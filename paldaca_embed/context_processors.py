"""Contexto de plantillas para el shell embebido."""

from django.conf import settings

from .embed import is_embedded


def paldaca_embed(request):
    portal_url = getattr(settings, "PALDACA_PORTAL_URL", "") or ""
    modulo_codigo = getattr(settings, "PALDACA_MODULO_CODIGO", "") or "cashflow"
    return {
        "paldaca_embedded": is_embedded(request),
        "paldaca_embed_css": f"{portal_url.rstrip('/')}/static/paldaca-embed.css",
        "paldaca_portal_url": portal_url,
        "paldaca_modulo_codigo": modulo_codigo,
        "paldaca_nav_portal_url": portal_url,
        "paldaca_nav_current_app": modulo_codigo,
    }
