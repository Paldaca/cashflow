"""Contrato `paldaca-embed` v1. Sin SSO: el login local sigue siendo el acceso."""

from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.template import RequestContext, Template
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from paldaca_embed.embed import PaldacaEmbedMiddleware, _normalizar_frame_ancestors


def _ok_view(_request):
    return HttpResponse("ok")


def _middleware():
    return PaldacaEmbedMiddleware(_ok_view)


class NormalizarFrameAncestorsTests(SimpleTestCase):
    def test_repone_comillas_en_self_sin_comillas(self):
        assert (
            _normalizar_frame_ancestors("self https://cpaldaca.com https://www.cpaldaca.com")
            == "'self' https://cpaldaca.com https://www.cpaldaca.com"
        )

    def test_no_duplica_comillas_si_ya_vienen_puestas(self):
        assert (
            _normalizar_frame_ancestors("'self' https://cpaldaca.com")
            == "'self' https://cpaldaca.com"
        )

    def test_no_toca_origenes_normales(self):
        valor = "https://cpaldaca.com https://www.cpaldaca.com"
        assert _normalizar_frame_ancestors(valor) == valor

    def test_reconoce_otros_keywords_de_csp(self):
        assert _normalizar_frame_ancestors("none") == "'none'"


@override_settings(PALDACA_FRAME_ANCESTORS="self https://cpaldaca.test")
class EmbedHeadersTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mw = _middleware()

    def test_dentro_del_iframe_emite_csp_y_no_bloquea_el_framing(self):
        request = self.factory.get("/healthz/", HTTP_SEC_FETCH_DEST="iframe")
        response = self.mw(request)

        assert response.status_code == 200
        assert "frame-ancestors" in response.headers.get("Content-Security-Policy", "")
        assert response.headers.get("X-Frame-Options") is None

    def test_csp_se_emite_tambien_en_navegacion_top_level(self):
        request = self.factory.get("/healthz/", HTTP_SEC_FETCH_DEST="document")
        response = self.mw(request)

        assert "frame-ancestors" in response.headers.get("Content-Security-Policy", "")
        assert response.headers.get("X-Frame-Options") is None

    def test_cookie_de_respaldo_se_escribe_en_iframe(self):
        request = self.factory.get("/healthz/", HTTP_SEC_FETCH_DEST="iframe")
        response = self.mw(request)

        assert response.cookies["paldaca_embed"].value == "1"

    def test_una_navegacion_top_level_invalida_la_cookie_de_respaldo(self):
        request = self.factory.get("/healthz/", HTTP_SEC_FETCH_DEST="document")
        request.COOKIES["paldaca_embed"] = "1"
        response = self.mw(request)

        assert response.cookies["paldaca_embed"].value == ""


@override_settings(PALDACA_FRAME_ANCESTORS="")
class EmbedSinFrameAncestorsTests(SimpleTestCase):
    def test_sin_configurar_no_agrega_csp_ni_toca_xfo(self):
        request = RequestFactory().get("/healthz/", HTTP_SEC_FETCH_DEST="iframe")
        response = _middleware()(request)

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers


@override_settings(
    PALDACA_EMBED_REDIRECT_TO_SHELL=True,
    PALDACA_PORTAL_URL="https://cpaldaca.test",
    PALDACA_SHELL_PATH="/cashflow",
)
class EmbedRedirectToShellTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mw = _middleware()
        self.usuario = User.objects.create_user(username="editor", password="x")

    def _auth(self, request):
        request.user = self.usuario
        return request

    def test_acceso_directo_al_subdominio_redirige_al_shell(self):
        request = self._auth(self.factory.get("/", HTTP_SEC_FETCH_DEST="document"))
        response = self.mw(request)

        assert response.status_code == 302
        assert response.headers["Location"] == "https://cpaldaca.test/cashflow/"

    def test_healthz_nunca_se_redirige_al_shell(self):
        request = self._auth(self.factory.get("/healthz/", HTTP_SEC_FETCH_DEST="document"))
        response = self.mw(request)

        assert response.status_code == 200

    def test_el_redirect_al_shell_no_aplica_dentro_del_iframe(self):
        request = self._auth(self.factory.get("/", HTTP_SEC_FETCH_DEST="iframe"))
        response = self.mw(request)

        assert response.status_code != 302

    def test_valvula_de_escape_sirve_el_satelite_suelto(self):
        request = self._auth(
            self.factory.get("/?paldaca_standalone=1", HTTP_SEC_FETCH_DEST="document")
        )
        response = self.mw(request)

        assert response.status_code != 302

    def test_anonimo_no_se_redirige_al_shell(self):
        request = self.factory.get("/", HTTP_SEC_FETCH_DEST="document")
        request.user = AnonymousUser()
        response = self.mw(request)

        assert response.status_code != 302


@override_settings(
    PALDACA_EMBED_REDIRECT_TO_SHELL=False,
    PALDACA_PORTAL_URL="https://cpaldaca.test",
    PALDACA_SHELL_PATH="/cashflow",
)
class EmbedDirectLinkVivoTests(TestCase):
    def test_acceso_directo_no_redirige(self):
        usuario = User.objects.create_user(username="editor", password="x")
        request = RequestFactory().get("/", HTTP_SEC_FETCH_DEST="document")
        request.user = usuario
        response = _middleware()(request)

        assert response.status_code != 302


@override_settings(
    PALDACA_FRAME_ANCESTORS="self https://cpaldaca.test",
    PALDACA_PORTAL_URL="https://cpaldaca.test",
)
class EmbedChromeTests(TestCase):
    """Mismas condiciones que templates/base.html, sin cargar organizations.urls."""

    _SNIPPET = Template(
        "{% if paldaca_embedded %}EMBED{% endif %}"
        "{% if user.is_authenticated and not hide_sidebar and not paldaca_embedded %}SIDEBAR{% endif %}"
        "{% if not hide_navbar and not paldaca_embedded %}NAVBAR{% endif %}"
    )

    def setUp(self):
        self.factory = RequestFactory()
        self.usuario = User.objects.create_user(username="editor", password="x")

    def _html(self, *, dest: str) -> str:
        request = self.factory.get("/home/", HTTP_SEC_FETCH_DEST=dest)
        request.user = self.usuario
        request.session = {}
        _middleware()(request)
        return self._SNIPPET.render(
            RequestContext(
                request,
                {"hide_sidebar": False, "hide_navbar": False},
            )
        )

    def test_top_level_monta_sidebar_propio(self):
        html = self._html(dest="document")
        assert "SIDEBAR" in html
        assert "NAVBAR" in html
        assert "EMBED" not in html

    def test_iframe_no_monta_sidebar_ni_navbar(self):
        html = self._html(dest="iframe")
        assert "SIDEBAR" not in html
        assert "NAVBAR" not in html
        assert "EMBED" in html
