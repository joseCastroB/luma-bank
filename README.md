# Luma Bank

Plataforma de **banca web 100% digital** con autenticación por **reconocimiento
facial** (basada en *embeddings* cifrados, nunca fotos) y prueba de vivacidad.

Proyecto del **Curso Integrador II: Software (UTP)** — enfoque híbrido
**PMBOK + Scrum**, 17 semanas, Sprint 0 + 8 sprints de 2 semanas.

> **Estado:** Sprint 1 completado — landing (HU01), registro/apertura de cuenta
> con KYC (HU02) e inicio de sesión con reconocimiento facial (HU03).

---

## Funcionalidades (Sprint 1)

### HU01 — Landing (`/`)
Página pública con dos accesos: **Abrir cuenta** → `/registro`,
**Banca por Internet** → `/login`.

### HU02 — Registro y apertura de cuenta (`/registro`)
Asistente de 5 pasos:
1. **DNI** → `POST /api/v1/accounts/registro/validar-dni/` (trim + 8 dígitos,
   RENIEC vía LionAPI con modos `production`/`mock`, caché por DNI en Valkey).
2. **Confirmar identidad** ("¿eres tú?").
3. **Datos**: correo, fecha de nacimiento (rechaza < 18), contraseña (≥ 12).
4. **Prueba de vida**: cámara + parpadeo/giro de cabeza (MediaPipe) + descriptor
   facial de 128d (face-api) **en el navegador**. La foto no se envía.
5. `POST /api/v1/accounts/registro/` → cifra el descriptor (AES-256-GCM), lo sube
   a MinIO, crea el cliente y su cuenta, y devuelve el número + QR TOTP.

### HU03 — Login (`/login`)
1. Correo o DNI.
2. Rostro en vivo → `POST /api/v1/accounts/login/facial/` (compara contra el
   *embedding* almacenado). Éxito → JWT y `/app`.
   - 2 fallos faciales → se ofrece el método alterno.
   - 5 fallos consecutivos → cuenta bloqueada 30 min (HTTP 423).
   - Prueba de vida fallida → intento registrado como sospechoso.
3. Método alterno: correo + contraseña + código TOTP →
   `POST /api/v1/accounts/login/password/`.

Área privada `/app` (`GET /api/v1/accounts/me/`, requiere JWT): perfil + cuentas.

### Banca (`/app`, API en `/api/v1/banking/`, requiere JWT)

Los números de HU son los del backlog (`Historias_de_Usuario_LumaBankv2`).

| HU | Función | Endpoint |
|----|---------|----------|
| HU07 | Abrir cuenta de ahorro (PEN/USD) | `POST accounts/` |
| HU08 | Saldo disponible y contable, TREA con vigencia | `GET accounts/`, `GET accounts/<numero>/` |
| HU09 | Historial con rango de fechas y paginación | `GET accounts/<numero>/transactions/` |
| HU10 | Transferencia entre cuentas propias | `POST transfers/own/` |
| HU13 | Transferencia a terceros por CCI (TOTP sobre el umbral) | `POST transfers/third-party/` |
| HU13 | Comprobante en PDF | `GET transactions/<codigo>/receipt/` |
| HU14 | Conversión al tipo de cambio de SUNAT | `GET exchange/quote/`, `POST exchange/` |

- **HU11, inactividad:** el frontend avisa a los 4:30 min y cierra a los 5 min; el
  JWT dura 5 min y se renueva solo con actividad (refresh de 10 min).
- **Intereses:** `python manage.py devengar_intereses` devenga a diario y capitaliza
  a fin de mes. El servicio `scheduler` de Docker Compose lo corre cada hora; correrlo
  varias veces no duplica intereses. Fuera de Compose, prográmalo como tarea periódica.
- **TREA y tipo de cambio:** se publican en las tablas `tasa_ahorro` y `tipo_cambio`
  (desde el admin). El tipo de cambio se consulta solo a SUNAT y, si falla, se usa la
  última publicación de los últimos 5 días.
- **Saldo de prueba:** `python manage.py depositar <numero> <monto>` (solo con DEBUG).
- Las transferencias a otros bancos se simulan: se debitan al instante, sin conexión
  real con una cámara de compensación.

---

## Stack

| Capa            | Tecnología |
|-----------------|------------|
| Backend         | Django 5.2 + Django REST Framework (Python 3.13) |
| Frontend        | React 19 + Vite + TypeScript + Tailwind CSS 4 (Node 24) |
| Base de datos   | PostgreSQL 18 |
| Cache / sesiones| Valkey 8 |
| Objetos (S3)    | MinIO (autoalojado) |
| Contenedores    | Docker + Docker Compose |
| CI/CD           | GitHub Actions |

Versiones exactas y política de *pinning*: ver [`VERSIONS.md`](./VERSIONS.md).

---

## Arranque local (todo en Docker)

**Requisitos:** solo [Docker](https://docs.docker.com/get-docker/) y Docker
Compose v2. **No** necesitas instalar Python ni Node en tu máquina: todo corre
dentro de los contenedores.

```bash
git clone <URL-del-repo> luma-bank
cd luma-bank
cp .env.example .env
docker compose up --build
```

Listo. Docker Compose aplica automáticamente `docker-compose.override.yml`
(modo desarrollo: *hot reload*, código montado como volumen, puertos expuestos).

| Servicio                  | URL |
|---------------------------|-----|
| Frontend (Vite dev)       | http://localhost:5173 |
| API (Django)              | http://localhost:8000 |
| API — health check        | http://localhost:8000/api/health/ |
| Django admin              | http://localhost:8000/admin/ |
| MinIO — consola           | http://localhost:9001 |
| PostgreSQL                | `localhost:5432` (luma / luma) |
| Valkey                    | `localhost:6379` |

### Primeros comandos

```bash
# Migraciones (crea las tablas, incluido el modelo User personalizado)
docker compose run --rm backend python manage.py migrate

# Superusuario para el admin
docker compose run --rm backend python manage.py createsuperuser

# Tests del backend
docker compose run --rm backend pytest

# Linter
docker compose run --rm backend ruff check .
```

Con `make` instalado (Git Bash / WSL / Linux / macOS) hay atajos: `make help`.

---

## Solución de problemas

**`postgres` reinicia en bucle / "container ... is unhealthy"** — normalmente por
un volumen de datos creado con un layout viejo. Como todavía no hay datos reales,
recréalo:

```bash
docker compose down -v      # borra los volúmenes del proyecto (postgres, valkey, minio)
docker compose up --build
```

**El frontend no recarga cambios en Windows** — ya está `usePolling` activado en
`vite.config.ts`; si aun así falla, reinicia el contenedor `frontend`.

---

## Modo producción

La configuración **base** de `docker-compose.yml` está pensada para producción
(Gunicorn, `config.settings.prod`, Nginx sirviendo el build estático). Para
levantarla sin los *overrides* de desarrollo:

```bash
docker compose -f docker-compose.yml up --build
```

Requiere un `.env` con valores reales: `DJANGO_SECRET_KEY` nuevo,
`DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_ALLOWED_HOSTS`,
`DNI_VALIDATION_MODE=production` y `LIONAPI_KEY` válida.

---

## Estructura

```
luma-bank/
├── apps/
│   ├── backend/                 # Django + DRF
│   │   ├── config/
│   │   │   ├── settings/        # base.py, dev.py, prod.py
│   │   │   ├── urls.py
│   │   │   └── health.py
│   │   ├── apps/                # apps por dominio
│   │   │   ├── accounts/        # clientes, User personalizado, KYC (Sprint 1)
│   │   │   ├── banking/         # cuentas y movimientos (Sprint 2+)
│   │   │   └── cards/           # tarjetas (Sprint 3+)
│   │   ├── tests/
│   │   ├── requirements.txt / requirements-dev.txt
│   │   └── Dockerfile
│   └── frontend/                # React + Vite + Tailwind
│       ├── src/
│       │   ├── features/        # una carpeta por HU (Sprint 1)
│       │   └── lib/
│       ├── package.json
│       └── Dockerfile
├── docker-compose.yml           # base (producción)
├── docker-compose.override.yml  # desarrollo (hot reload)
├── .github/workflows/ci.yml
├── scripts/check_dni_validation_mode.sh
├── .env.example
└── VERSIONS.md
```

---

## Variables de entorno

Todas están documentadas en [`.env.example`](./.env.example). Las críticas:

| Variable | Descripción |
|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` (local) o `config.settings.prod` |
| `DNI_VALIDATION_MODE` | `production` (llama a LionAPI/RENIEC y cachea) o `mock` (datos simulados, **solo dev/tests**). Si **no** se define → se comporta como `production` (*fail-safe*). |
| `LIONAPI_KEY` | Clave del servicio LionAPI (validación de identidad vía RENIEC) |
| `DATABASE_URL` | Conexión a PostgreSQL |
| `REDIS_URL` | Conexión a Valkey (cache + sesiones) |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Almacenamiento de *embeddings* faciales cifrados |
| `FACE_MATCH_THRESHOLD` | Umbral de coincidencia facial (menor = más estricto) |
| `FRONTEND_URL` | Origen del frontend (CORS) |

### ⚠️ `DNI_VALIDATION_MODE` y producción

`mock` **no** debe llegar nunca a un entorno productivo. Hay tres barreras:

1. El *default* del código es `production` (nunca `mock`).
2. `config/settings/prod.py` **aborta el arranque** si detecta `mock`.
3. El job `guard-dni-mode` de CI **bloquea el pipeline** si encuentra
   `DNI_VALIDATION_MODE=mock` en cualquier archivo versionado que aplique a
   producción (`scripts/check_dni_validation_mode.sh`).

---

## Convenciones de trabajo

- **Ramas por historia:** `feature/HU01-landing`, `feature/HU02-registro`,
  `feature/HU03-login`.
- **Commits** pequeños y descriptivos.
- **Tests:** `pytest` + `pytest-django`. LionAPI **siempre** *mockeada* en tests
  automatizados (nunca llamadas reales — consumen créditos).
- **Seguridad:** OWASP ASVS nivel 2 en autenticación.
- **Secretos:** nunca se versionan. `.env` está en `.gitignore`.
- Al subir la versión de una dependencia, actualizar `VERSIONS.md` en el mismo
  commit.
