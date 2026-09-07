# Luma Bank

Plataforma de **banca web 100% digital** con autenticación por **reconocimiento
facial** (basada en *embeddings* cifrados, nunca fotos) y prueba de vivacidad.

Proyecto del **Curso Integrador II: Software (UTP)** — enfoque híbrido
**PMBOK + Scrum**, 17 semanas, Sprint 0 + 8 sprints de 2 semanas.

> **Estado:** Sprint 0 — *scaffolding*. La landing, el registro (KYC) y el login
> facial llegan en el Sprint 1.

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
