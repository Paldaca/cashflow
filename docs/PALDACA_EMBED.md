# Embed en el Portal (iframe + doble sesión)

Cashflow se puede abrir en `cpaldaca.com/cashflow/...` (iframe same-site) y
sigue vivo en `https://cashflow.cpaldaca.com`. El login, las orgs y los datos
siguen siendo de esta app. El Portal solo decide quién ve el mosaico.

## Qué hay en el código

- App `paldaca_embed/`: middleware CSP `frame-ancestors`, cookie `paldaca_embed`,
  protocolo `paldaca-embed` v1 (`ready` / `loading` / `navigate`).
- `PALDACA_EMBED_REDIRECT_TO_SHELL` default `false`: el subdominio no se manda
  al shell.
- No hay SSO. Logout de Cashflow **no** emite `session-expired` (echaría del
  Portal). El playbook SSO está en [`PALDACA_SSO.md`](PALDACA_SSO.md).

## Variables

Todas por entorno (`CashFlow/settings.py` es `merge=ours`):

- `PALDACA_MODULO_CODIGO` (default `cashflow`)
- `PALDACA_PORTAL_URL` (shell: `http://localhost:5173` en dev, `https://cpaldaca.com` en prod)
- `PALDACA_SHELL_PATH` (default `/cashflow`)
- `PALDACA_FRAME_ANCESTORS`
- `PALDACA_EMBED_REDIRECT_TO_SHELL` (`false`)
- `CSRF_TRUSTED_ORIGINS` debe incluir `https://cpaldaca.com` en producción

## Piloto

La migración del Portal solo **crea** `core_modulo.codigo=cashflow`. No asigna
el módulo a todos los usuarios. Los superadmins del Portal lo ven; al resto
hay que dárselo a mano en Configuración → Usuarios. Quien no esté en el Portal
sigue entrando por `cashflow.cpaldaca.com`.

## Rollback del iframe

En el Portal: quitar `cashflow` de `VITE_EMBEDDED_MODULES` y reconstruir.
Esta app no se revierte.

## Válvula

`?paldaca_standalone=1` sirve Cashflow suelto aunque el referrer sea el shell.
