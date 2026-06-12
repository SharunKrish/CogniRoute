from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerRequestViewSet, InboundWebhookView

router = DefaultRouter()
router.register(r'requests', CustomerRequestViewSet, basename='request')

urlpatterns = [
    path('webhooks/inbound/', InboundWebhookView.as_view(), name='inbound_webhook'),
    path('', include(router.urls)),
]
