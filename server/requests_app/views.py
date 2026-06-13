from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import CustomerRequest, AIClassification, RequestEvent, InternalNote
from .serializers import (
    CustomerRequestCreateSerializer,
    CustomerRequestListSerializer,
    CustomerRequestDetailSerializer,
    InternalNoteSerializer,
)

def broadcast_dashboard_update(request_obj, event_type):
    """
    Utility to broadcast a request update to all websocket clients on 'dashboard_updates' group
    """
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                'dashboard_updates',
                {
                    'type': 'send_dashboard_update',
                    'data': {
                        'event': event_type,
                        'request': CustomerRequestListSerializer(request_obj).data
                    }
                }
            )
        except Exception as e:
            # Avoid crashing request loop if channels redis layer is not running
            print(f"WS Broadcast failed: {e}")


class CustomerRequestViewSet(viewsets.ModelViewSet):
    queryset = CustomerRequest.objects.all()
    permission_classes = (permissions.IsAuthenticated,)

    def get_permissions(self):
        if self.action in ['destroy', 'retry_classification']:
            from .permissions import IsAdminUserRole
            return [permissions.IsAuthenticated(), IsAdminUserRole()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerRequestCreateSerializer
        elif self.action == 'retrieve':
            return CustomerRequestDetailSerializer
        return CustomerRequestListSerializer

    def get_queryset(self):
        queryset = CustomerRequest.objects.all()
        
        # Filtering
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority_snapshot=priority_param)
            
        category_param = self.request.query_params.get('category')
        if category_param:
            queryset = queryset.filter(category_snapshot=category_param)
            
        # Search
        search_param = self.request.query_params.get('search')
        if search_param:
            queryset = queryset.filter(
                models.Q(customer_name__icontains=search_param) |
                models.Q(customer_email__icontains=search_param) |
                models.Q(original_message__icontains=search_param)
            )
            
        return queryset

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        Returns counts of requests by status and high priority for the dashboard stats counters.
        """
        return Response({
            'classified': CustomerRequest.objects.filter(status='classified').count(),
            'in_progress': CustomerRequest.objects.filter(status='in_progress').count(),
            'resolved': CustomerRequest.objects.filter(status='resolved').count(),
            'high_priority': CustomerRequest.objects.filter(priority_snapshot='high').count(),
        })

    def create(self, request, *args, **kwargs):
        # Prevent duplicate submissions with Idempotency Key
        idempotency_key = request.data.get('idempotency_key')
        if idempotency_key:
            existing = CustomerRequest.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                serializer = CustomerRequestDetailSerializer(existing)
                return Response(
                    {"message": "Duplicate request blocked by idempotency key.", "data": serializer.data},
                    status=status.HTTP_200_OK
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            customer_request = serializer.save()
            
            # Log creation event
            RequestEvent.objects.create(
                request=customer_request,
                event_type='created',
                actor=request.user.username,
                new_value='queued'
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='queued',
                actor='system',
                new_value='queued'
            )

        # Import celery tasks inline to avoid circular dependencies
        from .tasks import classify_request
        
        # Trigger async AI classification in background via Celery
        try:
            classify_request.delay(customer_request.id)
        except Exception as e:
            # Fallback if Celery/Redis is down in dev, we can note it but keep API working
            print(f"Celery task queueing failed: {e}")
            # Still log a failed/pending status so user can retry manually
            RequestEvent.objects.create(
                request=customer_request,
                event_type='classification_failed',
                actor='system',
                metadata={'error': 'Task queueing failed: Redis down?'}
            )

        # Broadcast WebSocket event
        broadcast_dashboard_update(customer_request, 'request_created')

        detail_serializer = CustomerRequestDetailSerializer(customer_request)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        customer_request = self.get_object()
        new_status = request.data.get('status')
        
        valid_statuses = [choice[0] for choice in CustomerRequest.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Choose from: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        old_status = customer_request.status
        if old_status == new_status:
            return Response(CustomerRequestDetailSerializer(customer_request).data)

        with transaction.atomic():
            customer_request.status = new_status
            customer_request.save()
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='status_changed',
                old_value=old_status,
                new_value=new_status,
                actor=request.user.username
            )

        broadcast_dashboard_update(customer_request, 'status_changed')
        
        return Response(CustomerRequestDetailSerializer(customer_request).data)

    @action(detail=True, methods=['post'], url_path='notes')
    def add_note(self, request, pk=None):
        customer_request = self.get_object()
        body = request.data.get('body')
        
        if not body:
            return Response({"error": "Note body is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        with transaction.atomic():
            note = InternalNote.objects.create(
                request=customer_request,
                author=request.user,
                body=body
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='note_added',
                actor=request.user.username,
                metadata={'note_id': note.id}
            )

        broadcast_dashboard_update(customer_request, 'note_added')
        
        return Response(CustomerRequestDetailSerializer(customer_request).data)

    @action(detail=True, methods=['post'], url_path='retry-classification')
    def retry_classification(self, request, pk=None):
        customer_request = self.get_object()
        
        with transaction.atomic():
            customer_request.status = 'queued'
            customer_request.save()
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='queued',
                actor=request.user.username,
                new_value='queued'
            )

        from .tasks import classify_request
        try:
            classify_request.delay(customer_request.id)
        except Exception as e:
            print(f"Celery task retry queueing failed: {e}")
            return Response({"error": "Redis broker unreachable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        broadcast_dashboard_update(customer_request, 'retry_triggered')
        
        return Response(CustomerRequestDetailSerializer(customer_request).data)

# Include Q imports to avoid NameError in queryset search
from django.db import models
from rest_framework.views import APIView
from django.conf import settings

class InboundWebhookView(APIView):
    """
    Public webhook endpoint that receives messages from simulated external sources
    such as WhatsApp, email, or website forms.
    Uses SHA256 HMAC header verification for security.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        # 1. Signature Verification
        received_signature = request.headers.get('X-Webhook-Signature')
        webhook_secret = getattr(settings, 'WEBHOOK_SECRET', 'cognifyr-secret-token-123')
        
        body_bytes = request.body
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        # Support a simpler fallback for easier manual testing (simple query/secret header check)
        secret_header = request.headers.get('X-Cognifyr-Secret')
        
        if received_signature != expected_signature and secret_header != webhook_secret:
            return Response(
                {"error": "Webhook signature verification failed."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Extract and Validate Input
        data = request.data
        customer_name = data.get('sender_name')
        customer_email = data.get('sender_email')
        source_channel = data.get('channel')
        original_message = data.get('message')
        idempotency_key = data.get('idempotency_key')

        if not original_message or not customer_name or not customer_email:
            return Response(
                {"error": "Missing mandatory fields: sender_name, sender_email, and message are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if source_channel not in ['website', 'whatsapp', 'email', 'telegram', 'api']:
            return Response(
                {"error": "Invalid channel. Choose from: website, whatsapp, email, telegram, api"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Prevent duplicate requests with Idempotency Key
        if idempotency_key:
            existing = CustomerRequest.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return Response(
                    {"message": "Duplicate request blocked by idempotency key.", "id": existing.id},
                    status=status.HTTP_200_OK
                )

        # 4. Create request and trigger worker
        with transaction.atomic():
            customer_request = CustomerRequest.objects.create(
                source_channel=source_channel,
                customer_name=customer_name,
                customer_email=customer_email,
                original_message=original_message,
                idempotency_key=idempotency_key,
                status='queued'
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='created',
                actor='webhook',
                new_value='queued'
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='queued',
                actor='system',
                new_value='queued'
            )

        from .tasks import classify_request
        try:
            classify_request.delay(customer_request.id)
        except Exception as e:
            print(f"Celery task queueing failed from webhook: {e}")

        # Broadcast WebSocket event
        broadcast_dashboard_update(customer_request, 'request_created')

        return Response({
            "message": "Webhook request enqueued successfully.",
            "request_id": customer_request.id,
            "status": "queued"
        }, status=status.HTTP_201_CREATED)

class TelegramWebhookView(APIView):
    """
    Public webhook endpoint that receives messages from a Telegram Bot.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        # Optional: Security validation if TELEGRAM_WEBHOOK_SECRET is set
        secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        expected_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        
        if expected_secret and secret_token != expected_secret:
            return Response(
                {"error": "Unauthorized webhook token."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data
        # Support both regular message and channel_post updates (Telegram channels send channel_post)
        message_data = data.get('message') or data.get('channel_post')
        if not message_data or 'text' not in message_data:
            return Response({"status": "ignored", "reason": "Not a text message"})

        from_user = message_data.get('from', {})
        user_id = from_user.get('id')
        username = from_user.get('username')
        first_name = from_user.get('first_name', '')
        last_name = from_user.get('last_name', '')
        message_text = message_data.get('text')
        message_id = message_data.get('message_id')
        chat_data = message_data.get('chat', {})
        chat_id = chat_data.get('id')

        # Format Customer details
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            if username:
                full_name = username
            elif chat_data.get('title'):
                full_name = chat_data.get('title')
            else:
                full_name = f"Telegram User {user_id}" if user_id else f"Telegram Chat {chat_id}"

        placeholder_email = f"telegram_{user_id or chat_id}@telegram.user"
        idempotency_key = f"telegram-{chat_id}-{message_id}"

        # Prevent duplicate requests
        existing = CustomerRequest.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response(
                {"message": "Duplicate request blocked by idempotency key.", "id": existing.id},
                status=status.HTTP_200_OK
            )

        # Create request and trigger classification
        with transaction.atomic():
            customer_request = CustomerRequest.objects.create(
                source_channel='telegram',
                customer_name=full_name,
                customer_email=placeholder_email,
                original_message=message_text,
                idempotency_key=idempotency_key,
                status='queued'
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='created',
                actor='telegram_bot',
                new_value='queued'
            )
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='queued',
                actor='system',
                new_value='queued'
            )

        from .tasks import classify_request
        try:
            classify_request.delay(customer_request.id)
        except Exception as e:
            print(f"Celery task queueing failed from Telegram webhook: {e}")

        # Send Telegram Bot Acknowledgment reply if token is set
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if bot_token and chat_id and message_id:
            import requests
            try:
                send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                reply_text = (
                    f"Hello {first_name or 'there'},\n\n"
                    f"Your request has been received and logged as <b>Request #{customer_request.id}</b>.\n\n"
                    f"Our AI routing engine is classifying and forwarding this to the appropriate queue shortly."
                )
                payload = {
                    "chat_id": chat_id,
                    "text": reply_text,
                    "reply_to_message_id": message_id,
                    "parse_mode": "HTML"
                }
                resp = requests.post(send_url, json=payload, timeout=5)
                if not resp.ok:
                    print(f"Telegram API response error: {resp.status_code} - {resp.text}")
                else:
                    print(f"Telegram reply sent successfully to chat_id {chat_id}")
            except Exception as e:
                print(f"Failed to send Telegram acknowledgment: {e}")
        else:
            print(f"Telegram reply skipped: bot_token is configured={bool(bot_token)}, chat_id={chat_id}, message_id={message_id}")

        # Broadcast WebSocket event
        broadcast_dashboard_update(customer_request, 'request_created')

        return Response({
            "message": "Telegram webhook request enqueued successfully.",
            "request_id": customer_request.id,
            "status": "queued"
        }, status=status.HTTP_201_CREATED)

import hmac
import hashlib

