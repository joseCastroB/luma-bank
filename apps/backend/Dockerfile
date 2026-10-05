# syntax=docker/dockerfile:1
# Luma Bank - Backend (Django + DRF)
# Base fijada por el equipo: Python 3.13 (ver /VERSIONS.md)

# ---------------------------------------------------------------------------
# Stage base: crea el virtualenv
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN python -m venv /opt/venv && pip install --upgrade pip

# ---------------------------------------------------------------------------
# Stage builder: instala SOLO dependencias de produccion
# ---------------------------------------------------------------------------
FROM base AS builder
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage dev: imagen de DESARROLLO (hot reload + dependencias de test)
# Se selecciona desde docker-compose.override.yml (build.target: dev)
# ---------------------------------------------------------------------------
FROM builder AS dev
ENV DJANGO_SETTINGS_MODULE=config.settings.dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# Stage runtime: imagen final de PRODUCCION.
# Va AL FINAL del archivo para ser el target por defecto: plataformas como
# Render construyen la ultima etapa y no permiten elegir otra.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod
RUN groupadd --system luma && useradd --system --gid luma --home /app luma
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY . .
# Archivos estaticos (admin) recopilados en el build. Se usan los settings de
# dev solo para este paso porque no exigen secretos; no toca la base de datos.
RUN mkdir -p /app/staticfiles /app/media \
    && DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py collectstatic --noinput \
    && chown -R luma:luma /app
USER luma
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
