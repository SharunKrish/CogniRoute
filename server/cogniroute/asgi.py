import os
from django.core.asgi import get_asgi_application

# Set settings module before importing channels applications
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cogniroute.settings')

# Get HTTP ASGI application first
django_http_asgi = get_asgi_application()

# Now import channels and project-specific routings
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from requests_app.middleware import JWTAuthMiddleware
import requests_app.routing

application = ProtocolTypeRouter({
    "http": django_http_asgi,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(
                requests_app.routing.websocket_urlpatterns
            )
        )
    ),
})
