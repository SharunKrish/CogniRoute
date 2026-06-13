from celery import shared_task
from django.db import transaction
import logging

from .models import CustomerRequest, AIClassification, RequestEvent
from .views import broadcast_dashboard_update
from ai_providers.factory import get_ai_provider

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def classify_request(self, request_id):
    """
    Celery task to classify a customer request asynchronously.
    """
    try:
        customer_request = CustomerRequest.objects.get(id=request_id)
    except CustomerRequest.DoesNotExist:
        logger.error(f"CustomerRequest with ID {request_id} does not exist.")
        return

    # 1. Create a classification log in 'pending' status
    provider = get_ai_provider()
    provider_name = getattr(provider, 'api_key', '')
    provider_label = 'gemini' if provider_name else 'mock'
    
    with transaction.atomic():
        # Log event: classification started
        RequestEvent.objects.create(
            request=customer_request,
            event_type='classification_started',
            actor='system',
            metadata={'provider': provider_label}
        )
        
        # Create AIClassification record
        classification = AIClassification.objects.create(
            request=customer_request,
            provider=provider_label,
            status='pending',
            retry_count=self.request.retries
        )

    # Broadcast status change to 'classification_started'
    broadcast_dashboard_update(customer_request, 'classification_started')

    # 2. Query the AI Provider
    try:
        result = provider.classify(customer_request.original_message)
        
        # 3. Update database with successful classification
        with transaction.atomic():
            # Update request snapshots
            customer_request.status = 'classified'
            customer_request.category_snapshot = result.category
            customer_request.priority_snapshot = result.priority
            customer_request.save()
            
            # Update classification record
            classification.category = result.category
            classification.priority = result.priority
            classification.summary = result.summary
            classification.confidence = result.confidence
            classification.reason = result.reason
            classification.raw_output = result.raw_output
            classification.status = 'completed'
            classification.save()
            
            # Log event: classification completed
            RequestEvent.objects.create(
                request=customer_request,
                event_type='classified',
                actor='system',
                new_value='classified',
                metadata={
                    'category': result.category,
                    'priority': result.priority,
                    'confidence': result.confidence
                }
            )
            
        # Broadcast final classification to dashboard
        broadcast_dashboard_update(customer_request, 'classification_completed')
        
    except Exception as exc:
        logger.error(f"Error during classification of request {request_id}: {exc}")
        
        # Update classification as failed
        with transaction.atomic():
            classification.status = 'failed'
            classification.error_message = str(exc)
            classification.save()
            
            RequestEvent.objects.create(
                request=customer_request,
                event_type='classification_failed',
                actor='system',
                metadata={'error': str(exc), 'retry': self.request.retries}
            )
            
        # Broadcast failure to dashboard
        broadcast_dashboard_update(customer_request, 'classification_failed')
        
        # Retry logic
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for request {request_id}.")
            with transaction.atomic():
                customer_request.status = 'failed'
                customer_request.save()
