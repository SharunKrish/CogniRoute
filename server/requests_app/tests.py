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
