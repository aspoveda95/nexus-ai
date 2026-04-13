"""ASGI config para api-core."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexus_api.settings")

application = get_asgi_application()
