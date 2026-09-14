"""
Soporte para renderizar Cashflow DENTRO del shell del Portal
(`cpaldaca.com/cashflow`), o suelto en cashflow.cpaldaca.com.

Copiado (casi verbatim) de `Nomina Paldaca/paldaca_sso/embed.py`, a su vez
tomado de ActivosPALDACA. Vive en esta app removible — no hay `core/` ni SSO
en este corte. El login propio de Cashflow se completa dentro del iframe
(doble sesión). `PALDACA_EMBED_REDIRECT_TO_SHELL` debe quedar en false para
que el subdominio siga siendo accesible en pestaña nueva.

Contrato: `paldaca-embed` v1 en Portal-Paldaca
`frontend/src/components/module-frame/protocol.ts`.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import escape

EMBED_REQUEST_ATTR = "paldaca_embedded"

EMBED_COOKIE = "paldaca_embed"
EMBED_QUERY_PARAM = "paldaca_embed"

STANDALONE_COOKIE = "paldaca_standalone"
STANDALONE_QUERY_PARAM = "paldaca_standalone"

DEFAULT_EXCLUDED_PREFIXES = (
    "/admin/",
    "/static/",
    "/media/",
    "/accounts/",
    "/superadmin/",
    "/bcv/",
    "/proyectos/compartido/",
    "/healthz/",
)

_CSP_KEYWORDS = {
    "self",
    "none",
    "unsafe-inline",
    "unsafe-eval",
    "unsafe-hashes",
    "strict-dynamic",
    "report-sample",
}


def _normalizar_frame_ancestors(valor: str) -> str:
    """Envuelve en comillas simples los keywords de CSP sueltos (`self` ->
    `'self'`), sin tocar orígenes normales (`https://cpaldaca.com`)."""
    tokens = []
    for token in valor.split():
        desnudo = token.strip("'").lower()
        if desnudo in _CSP_KEYWORDS and not (token.startswith("'") and token.endswith("'")):
            tokens.append(f"'{desnudo}'")
        else:
            tokens.append(token)
    return " ".join(tokens)


def is_embedded(request) -> bool:
    """¿Esta petición se está sirviendo dentro del iframe del Portal?"""
    return bool(getattr(request, EMBED_REQUEST_ATTR, False))


def _modulo_codigo() -> str:
    return getattr(settings, "PALDACA_MODULO_CODIGO", "")


def _portal_origin() -> str:
    """Origen exacto del shell, para `postMessage(..., targetOrigin)`."""
    raw = (getattr(settings, "PALDACA_PORTAL_URL", "") or "").strip()
    parts = urlsplit(raw)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return raw.rstrip("/")


def embed_signal_response(request, message_type: str, status: int = 200):
    """
    Documento mínimo cuyo único fin es avisar al shell por `postMessage`.

    En este corte (doble sesión) NO se usa para logout de Cashflow: emitir
    `session-expired` echaría del Portal. Queda listo para el playbook SSO.
    """
    origin = escape(_portal_origin())
    app = escape(_modulo_codigo())
    kind = escape(message_type)
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Paldaca</title></head>
<body>
<script>
  try {{
    window.parent.postMessage(
      {{ v: 1, source: "paldaca-embed", type: "{kind}", app: "{app}" }},
      "{origin}"
    );
  }} catch (e) {{ /* sin padre alcanzable: no hay nada que avisar */ }}
</script>
</body></html>"""
    return HttpResponse(html, status=status)


class PaldacaEmbedMiddleware:
    """
    Hace embebible este satélite y mantiene coherente la experiencia de shell.

    POSICIÓN EN `MIDDLEWARE`: DESPUÉS de `AuthenticationMiddleware` (el
    redirect al shell, si se activara, necesita `request.user`) y ANTES de
    `SuperuserPanelMiddleware`. Su fase de respuesta corre al final, así que
    tiene la última palabra sobre las cabeceras de framing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        standalone = self._resolve_standalone(request)
        embedded = self._resolve_embedded(request, standalone)
        setattr(request, EMBED_REQUEST_ATTR, embedded)

        redirect_response = self._maybe_redirect_to_shell(
            request, embedded=embedded, standalone=standalone
        )
        if redirect_response is not None:
            return self._apply_cookies(request, redirect_response, embedded, standalone)

        response = self.get_response(request)
        self._apply_frame_headers(response)
        return self._apply_cookies(request, response, embedded, standalone)

    def _resolve_standalone(self, request) -> bool:
        raw = request.GET.get(STANDALONE_QUERY_PARAM)
        if raw is not None:
            return raw not in ("0", "false", "no", "")
        return request.COOKIES.get(STANDALONE_COOKIE) == "1"

    def _resolve_embedded(self, request, standalone: bool) -> bool:
        if standalone:
            return False

        dest = request.headers.get("Sec-Fetch-Dest", "").lower()
        if dest == "iframe":
            return True
        if dest == "document":
            return False

        if request.GET.get(EMBED_QUERY_PARAM) == "1":
            return True
        return request.COOKIES.get(EMBED_COOKIE) == "1"

    def _maybe_redirect_to_shell(self, request, *, embedded: bool, standalone: bool):
        if embedded or standalone:
            return None
        if not getattr(settings, "PALDACA_EMBED_REDIRECT_TO_SHELL", False):
            return None
        if request.method != "GET":
            return None
        if request.headers.get("Sec-Fetch-Dest", "").lower() != "document":
            return None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        excluded = getattr(
            settings, "PALDACA_EMBED_EXCLUDED_PREFIXES", DEFAULT_EXCLUDED_PREFIXES
        )
        if any(request.path.startswith(prefix) for prefix in excluded):
            return None

        portal = _portal_origin()
        shell_path = (getattr(settings, "PALDACA_SHELL_PATH", "") or "").rstrip("/")
        if not portal or not shell_path:
            return None

        return HttpResponseRedirect(f"{portal}{shell_path}{request.get_full_path()}")

    def _apply_frame_headers(self, response) -> None:
        ancestors = getattr(settings, "PALDACA_FRAME_ANCESTORS", "").strip()
        if not ancestors:
            return

        if response.has_header("X-Frame-Options"):
            del response["X-Frame-Options"]

        if not response.has_header("Content-Security-Policy"):
            response["Content-Security-Policy"] = (
                f"frame-ancestors {_normalizar_frame_ancestors(ancestors)}"
            )

    def _apply_cookies(self, request, response, embedded: bool, standalone: bool):
        secure = bool(getattr(settings, "SESSION_COOKIE_SECURE", False))

        if standalone:
            if request.COOKIES.get(STANDALONE_COOKIE) != "1":
                response.set_cookie(
                    STANDALONE_COOKIE,
                    "1",
                    path="/",
                    samesite="Lax",
                    secure=secure,
                    httponly=True,
                )
        elif request.GET.get(STANDALONE_QUERY_PARAM) is not None:
            response.delete_cookie(STANDALONE_COOKIE, path="/")

        if embedded:
            if request.COOKIES.get(EMBED_COOKIE) != "1":
                response.set_cookie(
                    EMBED_COOKIE,
                    "1",
                    path="/",
                    samesite="Lax",
                    secure=secure,
                    httponly=True,
                )
        elif request.headers.get("Sec-Fetch-Dest", "").lower() == "document":
            if request.COOKIES.get(EMBED_COOKIE) is not None:
                response.delete_cookie(EMBED_COOKIE, path="/")

        return response
