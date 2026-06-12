from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('agent', 'Agent'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='agent')

    def is_admin(self):
        return self.role == 'admin'

    def is_agent(self):
        return self.role == 'agent'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
