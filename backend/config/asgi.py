"""
ASGI config for config project.

Supports both HTTP (Django WSGI via ASGI wrapper) and WebSocket (Channels).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = ProtocolTypeRouter(
    {
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(
            URLRouter(
                # WebSocket routes will be added per module later
                []
            )
        ),
    }
)
