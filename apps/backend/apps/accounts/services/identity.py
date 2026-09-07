"""
Validación de identidad por DNI (RENIEC vía LionAPI).

Dos modos según settings.DNI_VALIDATION_MODE:
- "production": consulta LionAPI y cachea el resultado por DNI en Valkey.
- "mock": NO llama a LionAPI; devuelve datos simulados. Solo dev/tests.

Si la variable no está definida, base.py ya la fuerza a "production" (fail-safe).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("luma.identity")

DNI_RE = re.compile(r"^\d{8}$")
_CACHE_PREFIX = "identity:dni:"


class IdentityError(Exception):
    """Base para errores de validación de identidad."""


class InvalidDni(IdentityError):
    """El DNI no tiene exactamente 8 dígitos."""


class IdentityNotFound(IdentityError):
    """RENIEC no devolvió una persona para ese DNI."""


class IdentityServiceError(IdentityError):
    """LionAPI no está disponible o respondió con error."""


@dataclass(frozen=True)
class DniData:
    dni: str
    nombres: str
    apellido_paterno: str
    apellido_materno: str
    source: str  # "lionapi" | "mock" | "cache"

    @property
    def apellidos(self) -> str:
        return f"{self.apellido_paterno} {self.apellido_materno}".strip()

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()

    def to_cacheable(self) -> dict:
        return {
            "dni": self.dni,
            "nombres": self.nombres,
            "apellido_paterno": self.apellido_paterno,
            "apellido_materno": self.apellido_materno,
        }


def normalize_dni(raw: str) -> str:
    """Aplica strip() y valida 8 dígitos exactos.

    Bug real encontrado en producción: un espacio invisible al copiar/pegar el
    número rompía la validación. Por eso el strip() es OBLIGATORIO.
    """
    dni = (raw or "").strip()
    if not DNI_RE.match(dni):
        raise InvalidDni("El DNI debe tener exactamente 8 dígitos numéricos.")
    return dni


def validate_dni(raw: str) -> DniData:
    dni = normalize_dni(raw)
    mode = settings.DNI_VALIDATION_MODE

    cached = cache.get(_CACHE_PREFIX + dni)
    if cached:
        return DniData(**cached, source="cache")

    if mode == "mock":
        data = _mock_lookup(dni)
    else:
        data = _lionapi_lookup(dni)

    cache.set(
        _CACHE_PREFIX + dni,
        data.to_cacheable(),
        timeout=settings.LIONAPI_CACHE_TTL_SECONDS,
    )
    return data


# --- Implementaciones ---------------------------------------------------


def _lionapi_lookup(dni: str) -> DniData:
    if not settings.LIONAPI_KEY:
        raise IdentityServiceError("LIONAPI_KEY no está configurada.")

    url = f"{settings.LIONAPI_BASE_URL.rstrip('/')}/consulta-dni/{dni}"
    try:
        resp = requests.get(url, headers={"x-api-key": settings.LIONAPI_KEY}, timeout=10)
    except requests.RequestException as exc:
        logger.warning("LionAPI no responde: %s", exc)
        raise IdentityServiceError("El servicio de validación de identidad no responde.") from exc

    if resp.status_code == 404:
        raise IdentityNotFound("No se encontró una persona con ese DNI.")
    if resp.status_code >= 400:
        logger.warning("LionAPI %s: %s", resp.status_code, resp.text[:300])
        raise IdentityServiceError("El servicio de validación de identidad falló.")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise IdentityServiceError("Respuesta inválida del servicio de identidad.") from exc

    return _parse_lionapi(dni, payload)


def _parse_lionapi(dni: str, payload: dict) -> DniData:
    """Extrae nombres/apellidos con tolerancia a variantes de la respuesta."""
    data = payload.get("data") or payload.get("result") or payload

    def pick(*keys: str) -> str:
        for k in keys:
            v = data.get(k)
            if v:
                return str(v).strip()
        return ""

    nombres = pick("nombres", "names", "first_name", "nombre")
    ap_paterno = pick(
        "apellido_paterno", "apellidoPaterno", "ape_paterno", "paternal_surname", "paterno"
    )
    ap_materno = pick(
        "apellido_materno", "apellidoMaterno", "ape_materno", "maternal_surname", "materno"
    )

    if not nombres and not ap_paterno:
        raise IdentityNotFound("No se encontró una persona con ese DNI.")

    return DniData(
        dni=dni,
        nombres=nombres,
        apellido_paterno=ap_paterno,
        apellido_materno=ap_materno,
        source="lionapi",
    )


_MOCK_NOMBRES = ["Juan", "María", "Carlos", "Lucía", "José", "Ana", "Miguel", "Rosa"]
_MOCK_PATERNOS = ["Quispe", "Flores", "Huamán", "Rojas", "Vargas", "Chávez", "Ramos", "Torres"]
_MOCK_MATERNOS = ["Mamani", "Sánchez", "Castro", "Díaz", "Cruz", "Gutiérrez", "Ríos", "León"]


def _mock_lookup(dni: str) -> DniData:
    """Datos deterministas por DNI. Solo desarrollo/tests."""
    h = int(hashlib.sha256(dni.encode()).hexdigest(), 16)
    return DniData(
        dni=dni,
        nombres=_MOCK_NOMBRES[h % len(_MOCK_NOMBRES)],
        apellido_paterno=_MOCK_PATERNOS[(h // 7) % len(_MOCK_PATERNOS)],
        apellido_materno=_MOCK_MATERNOS[(h // 13) % len(_MOCK_MATERNOS)],
        source="mock",
    )
