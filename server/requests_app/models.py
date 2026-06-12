from django.db import models
from django.conf import settings

class CustomerRequest(models.Model):
    CHANNEL_CHOICES = (
        ('website', 'Website'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('telegram', 'Telegram'),
        ('api', 'API'),
    )
    
    STATUS_CHOICES = (
        ('new', 'New'),
        ('queued', 'Queued'),
        ('classified', 'Classified'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    source_channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='api')
    customer_name = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)
    original_message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    
    # Snapshots of the latest classification for fast search/filtering
    category_snapshot = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    priority_snapshot = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    
    idempotency_key = models.CharField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request {self.id} - {self.customer_name or 'Unknown'} ({self.status})"


class AIClassification(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    request = models.ForeignKey(CustomerRequest, on_delete=models.CASCADE, related_name='classifications')
    provider = models.CharField(max_length=50)  # e.g., 'mock', 'gemini', 'openai'
    category = models.CharField(max_length=50, blank=True, null=True)
    priority = models.CharField(max_length=20, blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    raw_output = models.JSONField(blank=True, null=True)  # Store original API payload for debugging
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Classification for Request {self.request_id} - {self.status} ({self.provider})"


class RequestEvent(models.Model):
    EVENT_CHOICES = (
        ('created', 'Request Created'),
        ('queued', 'Enqueued for Classification'),
        ('classification_started', 'AI Classification Started'),
        ('classified', 'AI Classification Completed'),
        ('classification_failed', 'AI Classification Failed'),
        ('status_changed', 'Status Updated'),
        ('note_added', 'Internal Note Added'),
    )
    
    request = models.ForeignKey(CustomerRequest, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES, db_index=True)
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)
    actor = models.CharField(max_length=255, default='system')  # 'system' or 'username'
    metadata = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Event {self.event_type} on Request {self.request_id} at {self.timestamp}"


class InternalNote(models.Model):
    request = models.ForeignKey(CustomerRequest, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Note by {self.author.username} on Request {self.request_id}"
