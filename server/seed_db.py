import os
import django
import random
from datetime import datetime, timedelta

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cogniroute.settings')
django.setup()

from django.contrib.auth import get_user_model
from requests_app.models import CustomerRequest, AIClassification, RequestEvent, InternalNote

User = get_user_model()

def seed():
    print("Seeding database...")
    
    # 1. Create Users
    admin_user, created = User.objects.get_or_create(
        username='admin',
        email='admin@cognifyr.co',
        defaults={'role': 'admin'}
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("Admin user created (user: admin, pass: admin123)")
        
    agent_user, created = User.objects.get_or_create(
        username='agent',
        email='agent@cognifyr.co',
        defaults={'role': 'agent'}
    )
    if created:
        agent_user.set_password('agent123')
        agent_user.save()
        print("Agent user created (user: agent, pass: agent123)")

    # Avoid duplicate seeding if database is already populated
    if CustomerRequest.objects.count() > 0:
        print("Database already contains requests. Skipping request seeding.")
        return

    # 2. Mock Customer Messages
    mock_messages = [
        {
            "name": "Alice Johnson",
            "email": "alice@gmail.com",
            "channel": "email",
            "message": "Hi team, I would like to get a pricing quote for the Enterprise package. We are a team of 50 users and want to schedule a demo next week. Thanks!",
            "status": "classified",
            "category": "sales",
            "priority": "medium",
            "summary": "[SALES] Enterprise pricing query and demo request from Alice Johnson.",
            "reason": "Customer inquiry exhibits clear interest in purchasing and is asking about Enterprise plans and demo booking.",
            "note": "Assigned to sales representative. Scheduling demo for Tuesday."
        },
        {
            "name": "Bob Smith",
            "email": "bob@yahoo.com",
            "channel": "whatsapp",
            "message": "URGENT! Our login portal seems down. Whenever I enter my password, it crashes and shows a 500 server error. We can't access our paid dashboard. Please fix this immediately, we are losing money!",
            "status": "in_progress",
            "category": "urgent",
            "priority": "high",
            "summary": "[CRITICAL] Bob Smith cannot access the paid dashboard; login portal down.",
            "reason": "Request mentions service outage and blocker for paid tier users, representing high business risk.",
            "note": "Dev team notified. Investigating OAuth login token issues."
        },
        {
            "name": "Charlie Brown",
            "email": "charlie@outlook.com",
            "channel": "website",
            "message": "Hello, I made a duplicate payment by mistake. Can I please get a refund for the second transaction? I have attached the invoice details: #INV-9908. Thank you.",
            "status": "classified",
            "category": "support",
            "priority": "medium",
            "summary": "[SUPPORT] Request for billing refund on duplicate payment.",
            "reason": "Query is regarding billing, duplicate transaction, and request for refund. Safe to route to Support.",
            "note": "Refund processed via Stripe dashboard. Awaiting bank confirmation."
        },
        {
            "name": "David Miller",
            "email": "spammer99@lottery-winner.ru",
            "channel": "api",
            "message": "CONGRATULATIONS!!! You have won a free lottery ticket worth $10,000! Click here now to claim your cash prize and double your crypto wealth overnight! No credit card needed.",
            "status": "closed",
            "category": "spam",
            "priority": "low",
            "summary": "[SPAM] High risk lottery and crypto phishing message.",
            "reason": "Phishing markers, high density of uppercase congratulatory text, external link callouts, and lottery claims.",
            "note": "Auto-closed by system routing filters."
        },
        {
            "name": "Emma Watson",
            "email": "emma@gmail.com",
            "channel": "email",
            "message": "Hi, just wanted to check if you support integration with Slack? Our team currently uses Slack for everything and it would be great to sync notifications.",
            "status": "resolved",
            "category": "other",
            "priority": "low",
            "summary": "Product integration query regarding Slack.",
            "reason": "Inquiry is a general feature request rather than a support ticket or sales lead.",
            "note": "Replied to customer with documentation link on Webhook integrations."
        }
    ]

    for item in mock_messages:
        # Create request
        req = CustomerRequest.objects.create(
            source_channel=item["channel"],
            customer_name=item["name"],
            customer_email=item["email"],
            original_message=item["message"],
            status=item["status"],
            category_snapshot=item["category"],
            priority_snapshot=item["priority"]
        )

        # 1. Log request created
        RequestEvent.objects.create(
            request=req,
            event_type='created',
            actor='system',
            new_value='new',
            timestamp=datetime.now() - timedelta(minutes=60)
        )
        
        # 2. Log queued
        RequestEvent.objects.create(
            request=req,
            event_type='queued',
            actor='system',
            old_value='new',
            new_value='queued',
            timestamp=datetime.now() - timedelta(minutes=58)
        )

        # 3. Log classification started
        RequestEvent.objects.create(
            request=req,
            event_type='classification_started',
            actor='system',
            timestamp=datetime.now() - timedelta(minutes=57)
        )

        # 4. Create AIClassification
        AIClassification.objects.create(
            request=req,
            provider='mock',
            category=item["category"],
            priority=item["priority"],
            summary=item["summary"],
            confidence=round(random.uniform(0.82, 0.96), 2),
            reason=item["reason"],
            status='completed',
            raw_output={"seeding": True, "provider": "mock"},
            created_at=datetime.now() - timedelta(minutes=56)
        )

        # 5. Log classified
        RequestEvent.objects.create(
            request=req,
            event_type='classified',
            actor='system',
            new_value='classified',
            metadata={"category": item["category"], "priority": item["priority"]},
            timestamp=datetime.now() - timedelta(minutes=56)
        )

        # If it has progressed beyond 'classified'
        if item["status"] in ['in_progress', 'resolved', 'closed']:
            RequestEvent.objects.create(
                request=req,
                event_type='status_changed',
                old_value='classified',
                new_value=item["status"],
                actor='admin',
                timestamp=datetime.now() - timedelta(minutes=30)
            )

        # Add note
        InternalNote.objects.create(
            request=req,
            author=admin_user if random.choice([True, False]) else agent_user,
            body=item["note"],
            created_at=datetime.now() - timedelta(minutes=25)
        )
        
        RequestEvent.objects.create(
            request=req,
            event_type='note_added',
            actor='admin',
            timestamp=datetime.now() - timedelta(minutes=25)
        )

    print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed()
