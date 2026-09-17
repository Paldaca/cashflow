# Qué se hizo: iframe + doble sesión con el Portal

Corte implementado en la rama `integracion-cashflow` (Cashflow desde
`coolify-deploy`; Portal-Paldaca desde `dev`). **No hay SSO.** El Portal
abre Cashflow; Cashflow autentica y autoriza. Los datos no se migran.

Contrato de mensajes: `paldaca-embed` v1 (Portal
`frontend/src/components/module-frame/protocol.ts`).
Operación del embed: [`PALDACA_EMBED.md`](PALDACA_EMBED.md).
SSO futuro: [`PALDACA_SSO.md`](PALDACA_SSO.md).

## Decisión

| Superficie | Comportamiento |
|---|---|
| `cpaldaca.com/cashflow/...` | iframe same-site hacia `cashflow.cpaldaca.com` |
| `cashflow.cpaldaca.com` | igual que antes; **no** redirige al shell |
| Login | el de Cashflow, también dentro del iframe |
| Usuarios, orgs, txs, fotos, BCV | intactos |
| Cookie de sesión | sigue `sessionid` (no se renombra) |

El mosaico del Portal no es un candado: quien tenga URL y cuenta local entra.
El módulo `cashflow` solo se **crea**; no se asigna a todos. Superadmins del
Portal lo ven; el resto se habilita a mano (piloto).

## Cambios en este repo

- App `paldaca_embed/`: middleware CSP `frame-ancestors`, cookies
  `paldaca_embed` / `paldaca_standalone`, emisor `ready`/`loading`.
- `CashFlow/settings.py`: flags 100 % por env (`merge=ours`). Se quitó
  `XFrameOptionsMiddleware` (`DENY` dejaba el iframe en blanco).
- `templates/base.html`: sin sidebar/navbar si `paldaca_embedded`.
- `GET /healthz/` para pruebas y healthcheck.
- Redirect al shell (si algún día se enciende) usa `HttpResponseRedirect`
  absoluto, no `django.shortcuts.redirect` (evita cargar el URLconf).

## Cambios en Portal-Paldaca (misma rama)

- Migración `0016_seed_modulo_cashflow` y seed `core_modulo`.
- `SATELLITE_ORIGINS` / CSRF / CORS += `https://cashflow.cpaldaca.com`.
- Frontend: `VITE_SATELLITE_CASHFLOW_URL`, nav, Home, ruta `cashflow/*`.
- Local: `VITE_EMBEDDED_MODULES` incluye `cashflow`.
- Producción: **no** se añade al flag hasta desplegar este embed. El mosaico
  abre el subdominio (doble sesión en pestaña). Rollback del iframe = quitar
  el código y reconstruir el Portal.

## Cómo probar

```bash
# En cashflow (venv del proyecto)
python -m pytest paldaca_embed/tests/test_embed.py -q

# Servidor local (puerto que usa el Portal en .env.development)
python manage.py runserver 8005
```

```bash
# CSP y sin X-Frame-Options
curl -sSID - -H "Sec-Fetch-Dest: iframe" http://127.0.0.1:8005/healthz/

# Login usable dentro del iframe (doble sesión)
curl -sS -H "Sec-Fetch-Dest: iframe" \
  "http://127.0.0.1:8005/accounts/login/?paldaca_embed=1" | findstr paldaca-embed

# Link directo: anónimo va al login LOCAL, no al Portal
curl -sSID - -H "Sec-Fetch-Dest: document" http://127.0.0.1:8005/

# Válvula standalone
curl -sSID - -H "Sec-Fetch-Dest: document" \
  "http://127.0.0.1:8005/accounts/login/?paldaca_standalone=1"
```

En el Portal (local, Vite `:5173` + API `:8000`): `migrate` → asignar el
módulo a un piloto (o entrar como superadmin) → Control de Gastos → login
de Cashflow dentro del área de trabajo → selector de org. En otra pestaña,
`http://localhost:8005/` debe mostrar la UI propia.

## Resultado de las pruebas (2026-09-13)

### Automatizadas

`pytest paldaca_embed/tests/test_embed.py`: **17 passed**.

Cubren: normalización de `frame-ancestors` (comillas de `self`), CSP en
iframe y top-level, ausencia de `X-Frame-Options`, cookie de respaldo y su
borrado en `Sec-Fetch-Dest: document`, redirect al shell **apagado** por
default y encendido solo con el flag, exclusión de `/healthz/`,
`?paldaca_standalone=1`, y las condiciones de chrome de `base.html`
(sidebar/navbar solo si no está embebido).

Los tests del middleware no arrancan `organizations.urls` (Pillow/reportlab)
a propósito: usan `RequestFactory`.

### Manuales contra `runserver :8005`

| Comprobación | Resultado |
|---|---|
| `GET /healthz/` + `Sec-Fetch-Dest: iframe` | 200, CSP `frame-ancestors 'self' http://localhost:5173 http://127.0.0.1:5173`, **sin** `X-Frame-Options`, cookie `paldaca_embed=1` |
| `GET /accounts/login/?paldaca_embed=1` en iframe | 200, formulario «Iniciar sesión», script `paldaca-embed`, CSS del Portal |
| `GET /accounts/login/` top-level | 200, **0** menciones a `paldaca-embed` |
| `GET /` anónimo top-level | 302 → `/accounts/login/?next=/` (no al shell) |
| `?paldaca_standalone=1` | 200 + cookie `paldaca_standalone=1` |

No se levantó el SPA del Portal en este entorno (sin `node_modules` en
`frontend/`). El contrato del iframe en el shell queda para probar en local
completo o en el piloto de producción, después del `migrate` y del deploy
de este embed.

## Qué no se hizo (a propósito)

- SSO / `CuentaPortal` / adopción de usuarios.
- Renombrar `sessionid` → `cashflow_sessionid`.
- `PALDACA_EMBED_REDIRECT_TO_SHELL=true`.
- Encender `cashflow` en `VITE_EMBEDDED_MODULES` de producción.
- Asignar el módulo a todos los usuarios del Portal.
