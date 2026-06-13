from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
import hmac
import hashlib

from .models import CustomerRequest, AIClassification, RequestEvent, InternalNote
from ai_providers.mock_provider import MockAIProvider

User = get_user_model()

class RequestTests(APITestCase):
    def setUp(self):
        # Create users
        self.agent_user = User.objects.create_user(
            username='agent_test',
            password='testpassword123',
            role='agent'
        )
        self.client.force_authenticate(user=self.agent_user)
        
        # URL targets
        self.request_list_url = reverse('request-list')
        self.webhook_url = reverse('inbound_webhook')
        self.telegram_webhook_url = reverse('telegram_webhook')
        
        # Setup base request
        self.request_payload = {
            'customer_name': 'Sarah Connor',
            'customer_email': 'sarah@resistance.org',
            'source_channel': 'website',
            'original_message': 'I have a question about billing checkout payment processes.',
        }

    def test_create_request_success_and_idempotency(self):
        # 1. First submission
        payload = {**self.request_payload, 'idempotency_key': 'key-1234'}
        response = self.client.post(self.request_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        req_id = response.data['id']
        
        # Check event logs
        self.assertTrue(RequestEvent.objects.filter(request_id=req_id, event_type='created').exists())
        self.assertTrue(RequestEvent.objects.filter(request_id=req_id, event_type='queued').exists())

        # 2. Resubmit same payload with same idempotency key
        response_dup = self.client.post(self.request_list_url, payload, format='json')
        self.assertEqual(response_dup.status_code, status.HTTP_200_OK)
        self.assertEqual(response_dup.data['data']['id'], req_id)
        self.assertIn("Duplicate request blocked", response_dup.data['message'])

    def test_request_filtering(self):
        # Seed a few records
        req_sales = CustomerRequest.objects.create(
            customer_name='Sales Customer',
            customer_email='sales@example.com',
            source_channel='email',
            original_message='Pricing details query',
            status='classified',
            category_snapshot='sales',
            priority_snapshot='medium'
        )
        req_support = CustomerRequest.objects.create(
            customer_name='Support Customer',
            customer_email='support@example.com',
            source_channel='whatsapp',
            original_message='Payment issues login',
            status='in_progress',
            category_snapshot='support',
            priority_snapshot='high'
        )
        
        # Test filter by category
        res = self.client.get(f"{self.request_list_url}?category=sales")
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['id'], req_sales.id)
        
        # Test filter by priority
        res = self.client.get(f"{self.request_list_url}?priority=high")
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['id'], req_support.id)

        # Test search
        res = self.client.get(f"{self.request_list_url}?search=sales@example.com")
        self.assertEqual(len(res.data['results']), 1)

    def test_request_stats(self):
        CustomerRequest.objects.create(status='classified', priority_snapshot='low')
        CustomerRequest.objects.create(status='classified', priority_snapshot='high')
        CustomerRequest.objects.create(status='in_progress', priority_snapshot='high')
        CustomerRequest.objects.create(status='resolved', priority_snapshot='medium')

        stats_url = reverse('request-stats')
        res = self.client.get(stats_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['classified'], 2)
        self.assertEqual(res.data['in_progress'], 1)
        self.assertEqual(res.data['resolved'], 1)
        self.assertEqual(res.data['high_priority'], 2)

    def test_request_details_timeline_and_notes(self):
        req = CustomerRequest.objects.create(
            customer_name='John Doe',
            customer_email='john@example.com',
            source_channel='api',
            original_message='A test request message content'
        )
        
        # Add a note
        note_url = reverse('request-add-note', args=[req.id])
        note_response = self.client.post(note_url, {'body': 'This is an internal agent comment'}, format='json')
        self.assertEqual(note_response.status_code, status.HTTP_200_OK)
        
        # Check database note and event log
        self.assertTrue(InternalNote.objects.filter(request=req, body='This is an internal agent comment').exists())
        self.assertTrue(RequestEvent.objects.filter(request=req, event_type='note_added').exists())

        # Check detail retrieval
        detail_url = reverse('request-detail', args=[req.id])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['notes']), 1)
        self.assertEqual(res.data['notes'][0]['body'], 'This is an internal agent comment')

    def test_status_updating(self):
        req = CustomerRequest.objects.create(
            customer_name='Jane Doe',
            customer_email='jane@example.com',
            source_channel='api',
            original_message='Message details',
            status='queued'
        )
        
        status_url = reverse('request-update-status', args=[req.id])
        response = self.client.patch(status_url, {'status': 'in_progress'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check database update and event
        req.refresh_from_db()
        self.assertEqual(req.status, 'in_progress')
        self.assertTrue(RequestEvent.objects.filter(request=req, event_type='status_changed', old_value='queued', new_value='in_progress').exists())

    def test_webhook_inbound_secret_and_hmac(self):
        # 1. Unauthenticated Webhook call
        payload = {
            'sender_name': 'Webhook User',
            'sender_email': 'webhook@example.com',
            'channel': 'whatsapp',
            'message': 'This is an inbound whatsapp message about pricing.',
        }
        res = self.client.post(self.webhook_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Authenticated webhook via secret token check
        headers = {
            'HTTP_X_COGNIFYR_SECRET': 'cognifyr-secret-token-123'
        }
        res = self.client.post(self.webhook_url, payload, format='json', **headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'queued')
        
        # Verify request created in DB
        self.assertTrue(CustomerRequest.objects.filter(customer_email='webhook@example.com').exists())

    def test_telegram_webhook_success(self):
        # 1. Payload format for Telegram bot webhook
        payload = {
            'message': {
                'message_id': 54321,
                'from': {
                    'id': 987654,
                    'first_name': 'Arthur',
                    'last_name': 'Dent',
                    'username': 'arthurdent'
                },
                'chat': {
                    'id': 112233,
                    'type': 'private'
                },
                'text': 'I have an urgent server connection problem'
            }
        }
        res = self.client.post(self.telegram_webhook_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'queued')

        # Check DB request
        req = CustomerRequest.objects.get(id=res.data['request_id'])
        self.assertEqual(req.source_channel, 'telegram')
        self.assertEqual(req.customer_name, 'Arthur Dent')
        self.assertEqual(req.customer_email, 'telegram_987654@telegram.user')
        self.assertEqual(req.original_message, 'I have an urgent server connection problem')
        self.assertEqual(req.idempotency_key, 'telegram-112233-54321')

        # Check event logs
        self.assertTrue(RequestEvent.objects.filter(request=req, event_type='created', actor='telegram_bot').exists())
        self.assertTrue(RequestEvent.objects.filter(request=req, event_type='queued', actor='system').exists())

    def test_telegram_webhook_acknowledgment(self):
        from unittest.mock import patch
        from django.test import override_settings
        
        payload = {
            'message': {
                'message_id': 12345,
                'from': {
                    'id': 67890,
                    'first_name': 'Zaphod',
                    'last_name': 'Beeblebrox',
                    'username': 'zaphod'
                },
                'chat': {
                    'id': 998877,
                    'type': 'private'
                },
                'text': 'Is this the end of the universe?'
            }
        }
        
        with patch('requests.post') as mock_post:
            with override_settings(TELEGRAM_BOT_TOKEN='fake-bot-token-123'):
                res = self.client.post(self.telegram_webhook_url, payload, format='json')
                self.assertEqual(res.status_code, status.HTTP_201_CREATED)
                
                # Assert requests.post was called to send acknowledgment
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], 'https://api.telegram.org/botfake-bot-token-123/sendMessage')
                self.assertEqual(kwargs['json']['chat_id'], 998877)
                self.assertEqual(kwargs['json']['reply_to_message_id'], 12345)
                self.assertEqual(kwargs['json']['parse_mode'], 'HTML')
                self.assertIn('Request #', kwargs['json']['text'])

    def test_telegram_webhook_duplicate(self):
        payload = {
            'message': {
                'message_id': 8888,
                'from': {'id': 9999, 'first_name': 'Ford'},
                'chat': {'id': 7777},
                'text': "Don't panic!"
            }
        }
        res1 = self.client.post(self.telegram_webhook_url, payload, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(self.telegram_webhook_url, payload, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn("Duplicate request blocked", res2.data['message'])

    def test_telegram_webhook_with_secret(self):
        from django.test import override_settings
        payload = {
            'message': {
                'message_id': 1111,
                'from': {'id': 2222, 'first_name': 'Trillian'},
                'chat': {'id': 3333},
                'text': 'Where is the heart of gold?'
            }
        }

        with override_settings(TELEGRAM_WEBHOOK_SECRET='super-secret-token'):
            # 1. Without/wrong secret header -> 401
            res = self.client.post(self.telegram_webhook_url, payload, format='json')
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

            # 2. With correct secret header
            headers = {'HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN': 'super-secret-token'}
            res_authorized = self.client.post(self.telegram_webhook_url, payload, format='json', **headers)
            self.assertEqual(res_authorized.status_code, status.HTTP_201_CREATED)



class AIProviderHeuristicsTests(APITestCase):
    def test_mock_heuristics_categorization(self):
        provider = MockAIProvider()
        
        # Test support trigger keyword
        res_support = provider.classify("Hello, I need help with billing checkout processes.")
        self.assertEqual(res_support.category, 'support')
        self.assertEqual(res_support.priority, 'high')

        # Test urgent trigger keyword
        res_urgent = provider.classify("URGENT: Server is down and portal is crashed!")
        self.assertEqual(res_urgent.category, 'urgent')
        self.assertEqual(res_urgent.priority, 'high')

        # Test sales trigger keyword
        res_sales = provider.classify("Hi, I want to request a pricing discount demo for enterprise package.")
        self.assertEqual(res_sales.category, 'sales')
        self.assertEqual(res_sales.priority, 'medium')

        # Test spam trigger keyword
        res_spam = provider.classify("Congratulations! Win free crypto casino money right now!")
        self.assertEqual(res_spam.category, 'spam')
        self.assertEqual(res_spam.priority, 'low')
