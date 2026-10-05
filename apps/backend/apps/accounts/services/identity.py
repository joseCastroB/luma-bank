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


class LionApiQuotaExceeded(IdentityServiceError):
    """
    Se agotaron los créditos/consultas de LionAPI (HTTP 429).

    Va separada de IdentityServiceError porque RNF-06 pide degradación con
    gracia: el agotamiento de créditos es un estado CONOCIDO y esperable, no
    una caída del servicio. Permite distinguir "no hay consultas" de "la API
    está caída" y aplicar una respuesta degradada en vez de un error genérico.
    """


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
    """
    Consulta real a LionAPI (Software Lion).

    Contrato verificado contra la API en produccion:

        GET {LIONAPI_BASE_URL}/consulta-dni/{dni}
        Header: x-api-key: <LIONAPI_KEY>

    La API responde SIEMPRE con HTTP 200 y envuelve el resultado, así que el
    status HTTP NO alcanza para saber si fue un acierto:

        exito      -> {"success": true, "message": "exito", "result": {...}}
        no existe  -> {"success": false, "message": "DNI no encontrado", "result": null}
        sin key    -> HTTP 401, {"success": false, "message": "Falta la API Key ..."}
        fallo      -> {"success": false, "message": "<texto>", "result": null}
    """
    if not settings.LIONAPI_KEY:
        raise IdentityServiceError("LIONAPI_KEY no está configurada.")

    url = f"{settings.LIONAPI_BASE_URL.rstrip('/')}/consulta-dni/{dni}"
    try:
        resp = requests.get(
            url,
            headers={"x-api-key": settings.LIONAPI_KEY, "Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning("LionAPI no responde: %s", exc)
        raise IdentityServiceError("El servicio de validación de identidad no responde.") from exc

    if resp.status_code == 401:
        # Credencial invalida o ausente. Es un problema de despliegue, no del DNI.
        logger.error("LionAPI 401: API Key invalida o ausente.")
        raise IdentityServiceError("El servicio de validación de identidad no está disponible.")
    if resp.status_code == 429:
        # RNF-06: agotamiento de creditos. Se distingue del fallo generico para
        # poder aplicar la degradacion con gracia correspondiente.
        logger.warning("LionAPI 429: creditos agotados.")
        raise LionApiQuotaExceeded("Se agotaron las consultas disponibles al servicio.")
    if resp.status_code >= 400:
        logger.warning("LionAPI %s: %s", resp.status_code, resp.text[:300])
        raise IdentityServiceError("El servicio de validación de identidad falló.")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise IdentityServiceError("Respuesta inválida del servicio de identidad.") from exc

    return _parse_lionapi(dni, payload)


def _parse_lionapi(dni: str, payload: dict) -> DniData:
    """
    Interpreta el sobre de LionAPI.

    El campo `success` es el que manda: la API devuelve HTTP 200 incluso cuando
    el DNI no existe o cuando el服务端 falla, así que leer solo el status HTTP
    haría que un "DNI no encontrado" pasara por un acierto.
    """
    success = payload.get("success")
    message = str(payload.get("message") or "").strip()
    data = payload.get("result") or payload.get("data") or {}

    if success is False or (success is None and message and not data):
        # Distinguir "no existe esa persona" de "el servicio falló": es la
        # diferencia entre un 400 honesto al usuario y un 502 con reintento.
        if _is_not_found(message):
            raise IdentityNotFound("No se encontró una persona con ese DNI.")
        raise IdentityServiceError("El servicio de validación de identidad falló.")

    def pick(*keys: str) -> str:
        for k in keys:
            v = data.get(k)
            if v:
                return str(v).strip()
        return ""

    # Claves confirmadas contra la API real: nombres, paterno, materno.
    nombres = pick("nombres", "names", "first_name", "nombre")
    ap_paterno = pick("paterno", "apellido_paterno", "apellidoPaterno", "ape_paterno")
    ap_materno = pick("materno", "apellido_materno", "apellidoMaterno", "ape_materno")

    if not nombres and not ap_paterno:
        raise IdentityNotFound("No se encontró una persona con ese DNI.")

    return DniData(
        dni=str(data.get("dni") or dni).strip(),
        nombres=nombres,
        apellido_paterno=ap_paterno,
        apellido_materno=ap_materno,
        source="lionapi",
    )


def _is_not_found(message: str) -> bool:
    """Distingue 'ese DNI no existe' de 'la API falló'."""
    m = message.lower()
    return "no encontrado" in m or "no existe" in m or "no fue encontrado" in m


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
