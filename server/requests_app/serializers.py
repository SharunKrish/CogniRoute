from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomerRequest, AIClassification, RequestEvent, InternalNote

User = get_user_model()

class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'role')


class AIClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIClassification
        fields = ('id', 'provider', 'category', 'priority', 'summary', 'confidence', 'reason', 'raw_output', 'status', 'error_message', 'retry_count', 'created_at')


class RequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ('id', 'event_type', 'old_value', 'new_value', 'actor', 'metadata', 'timestamp')


class InternalNoteSerializer(serializers.ModelSerializer):
    author = UserShortSerializer(read_only=True)

    class Meta:
        model = InternalNote
        fields = ('id', 'author', 'body', 'created_at')


class CustomerRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRequest
        fields = ('id', 'source_channel', 'customer_name', 'customer_email', 'original_message', 'idempotency_key')
        extra_kwargs = {
            'original_message': {'required': True},
            'customer_name': {'required': True},
            'customer_email': {'required': True},
        }

    def validate_customer_email(self, value):
        if not value:
            raise serializers.ValidationError("Customer email is required.")
        return value


class CustomerRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRequest
        fields = ('id', 'source_channel', 'customer_name', 'customer_email', 'status', 'category_snapshot', 'priority_snapshot', 'created_at', 'updated_at')


class CustomerRequestDetailSerializer(serializers.ModelSerializer):
    classifications = AIClassificationSerializer(many=True, read_only=True)
    notes = InternalNoteSerializer(many=True, read_only=True)
    events = RequestEventSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerRequest
        fields = (
            'id', 'source_channel', 'customer_name', 'customer_email', 
            'original_message', 'status', 'category_snapshot', 'priority_snapshot', 
            'idempotency_key', 'created_at', 'updated_at', 
            'classifications', 'notes', 'events'
        )
