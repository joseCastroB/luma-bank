# VERSIONS.md — versiones fijadas de Luma Bank

Este archivo es la **fuente de verdad** de qué versiones corre el proyecto.
Cualquiera del equipo (o una sesión futura) debe poder leer solo este archivo
para saber el entorno completo, sin abrir cada Dockerfile.

> **Regla:** cuando actualices una versión (p. ej. un parche de seguridad de
> Django), actualiza también la tabla de abajo **en el mismo commit**, con la
> nueva fecha en la columna "Fijado el".

Última revisión completa: **2026-09-07**

---

## Runtimes e imágenes base (Docker)

| Tecnología        | Versión / tag                                  | Dónde                                   | Fijado el  | Notas |
|-------------------|------------------------------------------------|----------------------------------------|------------|-------|
| Python            | `3.13` (imagen `python:3.13-slim`)             | `apps/backend/Dockerfile`              | 2026-09-07 | Sigue el último parche de la serie 3.13 |
| Node.js           | `24` (imagen `node:24-alpine`)                 | `apps/frontend/Dockerfile`, override   | 2026-09-07 | Active LTS. Último parche de la serie 24 |
| PostgreSQL        | `18` (imagen `postgres:18`)                    | `docker-compose.yml`                   | 2026-09-07 | Último minor de PG 18 |
| Valkey            | `8` (imagen `valkey/valkey:8`)                 | `docker-compose.yml`                   | 2026-09-07 | Fork open source de Redis |
| MinIO (servidor)  | `RELEASE.2025-09-07T16-13-09Z`                 | `docker-compose.yml`                   | 2026-09-07 | Tag por fecha, **nunca** `latest`. Ver nota (1) |
| MinIO Client (mc) | `RELEASE.2025-08-13T08-35-41Z`                 | `docker-compose.yml` (`minio-init`)    | 2026-09-07 | Crea el bucket de embeddings |
| Nginx             | `1.30-alpine`                                  | `apps/frontend/Dockerfile`            | 2026-09-07 | Rama estable; sirve el build de producción |

**Política de pin de imágenes base:** `python:3.13-slim`, `node:24-alpine`,
`postgres:18` y `valkey/valkey:8` se fijan a la **serie** (major/minor); un
`docker compose build --pull` puede traer un parche nuevo de esa serie. Las
**dependencias de aplicación** (Python y npm, ver abajo) sí están fijadas al
parche exacto con `==`. MinIO y su cliente van fijados a un tag por fecha
exacto por pedido explícito del equipo.

(1) MinIO community dejó de publicar binarios/imágenes nuevas tras
`RELEASE.2025-09-07`. Si se necesita una versión más nueva, evaluar construir
desde fuente o migrar a un fork mantenido. Documentar el cambio aquí.

---

## Frameworks principales

| Tecnología            | Versión  | Dónde                                  | Fijado el  |
|-----------------------|----------|----------------------------------------|------------|
| Django                | 5.2.17   | `apps/backend/requirements.txt`        | 2026-09-07 |
| Django REST Framework | 3.18.0   | `apps/backend/requirements.txt`        | 2026-09-07 |
| React                 | 19.2.8   | `apps/frontend/package.json`           | 2026-09-07 |
| Vite                  | 8.2.2    | `apps/frontend/package.json`           | 2026-09-07 |
| Tailwind CSS          | 4.3.3    | `apps/frontend/package.json`           | 2026-09-07 |
| TypeScript            | 5.9.3    | `apps/frontend/package.json`           | 2026-09-07 |

> **Nota TypeScript:** existe TypeScript 7.x (port nativo). Nos quedamos en
> 5.9.3 hasta que `typescript-eslint` y `@vitejs/plugin-react` lo soporten de
> forma estable. Revisar en el siguiente sprint.

---

## Dependencias Python (backend) — `apps/backend/requirements.txt`

| Paquete                        | Versión   |
|--------------------------------|-----------|
| Django                         | 5.2.17    |
| djangorestframework            | 3.18.0    |
| django-cors-headers            | 4.9.0     |
| django-environ                 | 0.14.0    |
| psycopg[binary]                | 3.3.5     |
| redis                          | 8.1.0     |
| gunicorn                       | 26.2.0    |
| djangorestframework-simplejwt  | 5.5.1     |
| pyotp                          | 2.10.0    |
| boto3                          | 1.43.89   |
| django-storages                | 1.14.6    |
| cryptography                   | 50.0.1    |
| whitenoise                     | 6.12.0    |

### Solo dev/test — `apps/backend/requirements-dev.txt`

| Paquete        | Versión  |
|----------------|----------|
| pytest         | 9.1.1    |
| pytest-django  | 4.14.0   |
| pytest-cov     | 7.1.0    |
| ruff           | 0.16.6   |
| factory-boy    | 3.3.3    |
| responses      | 0.26.3   |

---

## Dependencias npm (frontend) — `apps/frontend/package.json`

Sin `^` ni `~`: versión exacta. El `package-lock.json` fija además todo el árbol.

| Paquete                        | Versión   | Tipo |
|--------------------------------|-----------|------|
| react                          | 19.2.8    | prod |
| react-dom                      | 19.2.8    | prod |
| vite                           | 8.2.2     | dev  |
| @vitejs/plugin-react           | 6.1.1     | dev  |
| tailwindcss                    | 4.3.3     | dev  |
| @tailwindcss/vite              | 4.3.3     | dev  |
| typescript                     | 5.9.3     | dev  |
| typescript-eslint              | 8.69.0    | dev  |
| eslint                         | 10.10.0   | dev  |
| @eslint/js                     | 10.0.1    | dev  |
| eslint-plugin-react-hooks      | 7.1.1     | dev  |
| eslint-plugin-react-refresh    | 0.5.6     | dev  |
| globals                        | 17.12.0   | dev  |
| @types/react                   | 19.2.18   | dev  |
| @types/react-dom               | 19.2.7    | dev  |
| @types/node                    | 26.4.1    | dev  |

---

## Historial de cambios de versión

| Fecha       | Cambio                                             | Commit |
|-------------|----------------------------------------------------|--------|
| 2026-09-07  | Fijado inicial de todo el stack (Sprint 0)          | —      |
