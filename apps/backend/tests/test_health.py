"""Smoke tests del scaffolding (Sprint 0)."""

import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint_ok():
    client = APIClient()
    resp = client.get(reverse("health"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "luma-bank-api"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["cache"] == "ok"


def test_dni_validation_mode_is_valid():
    assert settings.DNI_VALIDATION_MODE in {"production", "mock"}


def test_prod_settings_reject_mock_mode():
    """config.settings.prod debe abortar el arranque si DNI_VALIDATION_MODE=mock."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DNI_VALIDATION_MODE": "mock",
        "DJANGO_SECRET_KEY": "x" * 60,
        "DJANGO_ALLOWED_HOSTS": "luma.example.com",
        "DATABASE_URL": "postgres://luma:luma@localhost:5432/luma",
        "REDIS_URL": "redis://localhost:6379/0",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    assert result.returncode != 0
    assert "mock" in (result.stdout + result.stderr).lower()
