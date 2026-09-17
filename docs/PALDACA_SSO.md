# Playbook SSO federado (después del iframe)

No mezclar con el primer deploy del embed. Contrato:
`Portal-Paldaca/docs/PALDACA_SUITE/CONTRATO_SSO_FEDERADO.md`.
Referencia: `Nomina Paldaca/paldaca_sso/`.

Objetivo: un solo login (el del Portal). Cashflow crea o adopta una cuenta
espejo y abre su propia sesión (`cashflow_sessionid`). Orgs y roles locales
no se migran.

## S0 — Inventario (obligatorio, solo lectura)

Sin esto no se enciende el flag. Un espejo nuevo **no hereda**
`OrganizationAccess`: el usuario entra y ve el dashboard vacío.

1. Exportar Cashflow: `auth_user.id`, `username`, `email`, `is_superuser`,
   `profile.edit`, orgs vía `OrganizationAccess`.
2. Exportar Portal: `core_usuario.id`, `username`, `email`, módulos.
3. Clasificar: coincidencia clara / ambigua / solo-Cashflow / solo-Portal /
   superuser local (nunca adoptar).
4. Resolver ambiguos a mano. No hay match por “nombre parecido”.
5. Política de login local recomendada: permanente para solo-Cashflow
   (desvío vs Nómina, que lo deja en break-glass de superuser).

## S1 — Portal

El módulo `cashflow` ya existe por el embed. Comprobar:

1. `core_modulo.codigo=cashflow` activo.
2. `SATELLITE_ORIGINS` incluye `https://cashflow.cpaldaca.com`.
3. El piloto tiene el módulo (`modulos` en `GET /api/auth/me/`, no `permisos`).
4. No añadir `cashflow` a `PALDACA_DIRECTORIO_MODULOS` salvo que RRHH deba
   crear identidades desde aquí.

## S2 — Adaptar `paldaca_sso/`

No copiar `core/` del Portal. No usar el upsert de Nómina tal cual (importa
`Disciplina` / `Perfil` / `UsuarioModulo`).

1. Copiar la app desde Nómina.
2. Reescribir el upsert:
   - Unión por `portal_user_id` (`CuentaPortal`).
   - Adopción por username/email si `PALDACA_SSO_ADOPT_LOCAL_USERS=true`.
   - `set_unusable_password()` en espejos nuevos.
   - `is_superuser` **nunca** se espeja (el middleware de superadmin lo
     mandaría a `/superadmin/`).
   - **No escribir** `Profile.edit` ni `OrganizationAccess`.
   - Acceso: `identity.tiene_modulo("cashflow")` o `es_superadmin`.
3. Header backchannel: `X-Paldaca-Client: cashflow`.
4. Exenciones: `/accounts/`, `/superadmin/`, `/admin/`, `/media/`, `/static/`,
   `/bcv/`, `/proyectos/compartido/`, `/healthz/`.
5. Middleware: `Authentication` → embed → SSO → `SuperuserPanel`.
6. Settings solo por env (`merge=ours`):

```
PALDACA_SSO_ENABLED=false
PALDACA_PORTAL_URL=https://cpaldaca.com
PALDACA_PORTAL_API_URL=https://api.cpaldaca.com
PALDACA_SSO_PORTAL_COOKIE_NAME=paldaca_sessionid
SESSION_COOKIE_NAME=cashflow_sessionid
SESSION_COOKIE_DOMAIN=
```

`PALDACA_PORTAL_URL` (shell) ≠ `PALDACA_PORTAL_API_URL` (backchannel).
Checks de arranque: cookie ≠ `paldaca_sessionid`; domain vacío.

## S3 — Deploy oscuro

1. `PALDACA_SSO_ENABLED=false`. El iframe + doble sesión no cambia.
2. `migrate` → `paldaca_sso_cuenta_portal`.
3. Avisar: encender renombra la cookie y cierra `sessionid` (un login extra).
4. `python manage.py paldaca_sso_check --cookie <paldaca_sessionid real>`.
5. Local: `localhost` en ambos lados, nunca mezclar con `127.0.0.1`.

## S4 — Encender

1. Piloto: 2–3 usuarios con match claro y módulo asignado.
2. `PALDACA_SSO_ENABLED=true`. No tocar `VITE_EMBEDDED_MODULES`.
3. Login Portal → iframe sin segundo login → selector de org.
4. Adopción: `CuentaPortal` apunta al User local; las orgs siguen.
5. Portal sin match: User nuevo, cero orgs. Un admin local da el acceso.
6. Logout embebido: `session-expired` (ahora sí). Top-level: logout del Portal.
   Borrar solo cookies host-only de Cashflow.
7. Revalidar solo en petición real (300 s). 401/403 cierra sin gracia.
   5xx/timeout: gracia 30 min. Nunca redirect al Portal si está caído.

## S5 — Verificar

- `paldaca_sessionid` Domain=`.cpaldaca.com`; `cashflow_sessionid` host-only.
- Quitar el módulo al piloto → `forbidden` en el iframe, no el login del Portal.
- Superadmin del Portal entra como User normal (no `is_superuser`).
- `PALDACA_SSO_ENABLED=false` + restart: vuelve el doble login.

## S6 — No hacer

- No alinear `SECRET_KEY` con el Portal.
- No usar `SESSION_COOKIE_NAME=paldaca_sessionid`.
- No espejar `is_superuser` ni mapear orgs/roles desde el payload.
- No encender SSO el mismo día que el primer deploy del iframe.
