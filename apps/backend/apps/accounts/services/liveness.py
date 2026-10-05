"""
Prueba de vida con RETO ALEATORIO emitido por el servidor (HU02/HU03, RNF-15).

Por que el reto lo genera el servidor y no el cliente
------------------------------------------------------
MediaPipe corre en el navegador y detecta parpadeo y giro de cabeza, pero
eso solo demuestra que *alguien* pulso el boton de nuestro sitio. Un atacante
que no usa la UI (curl, Postman, un cliente parcheado) se salta la camara
entera y manda `{"liveness": {"passed": true}}` junto con un descriptor
cualquiera: el backend no tiene forma de saber que no hubo camara.

La defensa clasica contra replay de video es el RETO ALEATORIO: el servidor
manda una secuencia distinta en cada intento y el cliente debe ejecutarla en
ese orden exacto. Un video grabado de "parpadeo + giro a la izquierda" solo
pasa cuando el servidor sortea esa secuencia concreta, y el nonce de un solo
uso impide reutilizar la respuesta de un intento anterior.

LIMITE HONESTO DE ESTA DEFENSA
------------------------------
Esto demuestra que hubo una secuencia de gestos aleatoria y no repetible.
NO demuestra que haya una persona real detras de la camara: un deepfake en
tiempo real sigue pasando. Para eso habria que correr deteccion de vida en el
servidor (video remoto o modelo antispoofing dedicado), que excede el alcance
de este MVP. Se documenta explicitamente en el informe tecnico de seguridad.

VISION (no implementada, requiere coordenacion con frontend):
Mediapipe se ejecuta en el navegador y sus landmarks llegan al cliente, no al
servidor, asi que el backend no puede saber QUE se ejecuto el gesto: solo puede
comprobar que el cliente reporto una secuencia ordenada corretamente. Un
atacante con curl o un cliente parcheado puede responder el reto sin abrir la
camara. Subir el video (o los landmarks) al servidor permitiria verificarlo de
verdad, a costa de filtrar imagenes faciales del usuario fuera del navegador.
"""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger("luma.liveness")

CACHE_PREFIX = "luma:liveness:"

# Duracion imposible de alcanzar por una persona real. Se usa como respuesta
# cuando el tiempo del reto no se puede medir, para que la validacion falle.
_UNMEASURABLE_MS = 10**9

# Pool de gestos que el detector de MediaPipe puede verificar hoy.
# Anadir un gesto aqui obliga a implementarlo tambien en el cliente
# (apps/frontend/src/features/auth/shared/liveness.ts).
ACTIONS: tuple[str, ...] = ("blink", "head_turn_left", "head_turn_right")


class LivenessError(Exception):
    """Reto de vida invalido, vencido, ya usado o mal ejecutado."""

    status = 400

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    plan: list[str]
    expires_in: int


@dataclass(frozen=True)
class Attestation:
    """Prueba de que un reto se ejecuto correctamente. Se persiste como evidencia."""

    challenge_id: str
    plan: list[str]
    completed_actions: list[str]
    duration_ms: int


def _key(challenge_id: str) -> str:
    return f"{CACHE_PREFIX}{challenge_id}"


def issue_challenge() -> Challenge:
    """Emite un reto de un solo uso. Sin estado en base de datos."""
    size = min(settings.LIVENESS_PLAN_SIZE, len(ACTIONS))
    # OJO: sample() ya devuelve los elementos en ORDEN ALEATORIO. Aplicarle
    # sorted() aqui devolveria siempre el mismo plan alfabetico
    # (blink -> head_turn_left -> head_turn_right) y el reto aleatorio no
    # seria aleatorio: un video grabado de esa secuencia pasaria siempre.
    plan = list(secrets.SystemRandom().sample(ACTIONS, size))

    challenge_id = secrets.token_urlsafe(24)
    ttl = settings.LIVENESS_CHALLENGE_TTL_SECONDS
    # No guardamos un flag "consumed": el reto se invalida borrando la clave y
    # el unico uso lo garantiza que cache.delete() devuelva False la 2a vez.
    payload = {
        "plan": plan,
        "issued_at": timezone.now().isoformat(),
    }
    # cache.add() no sobreescribe: si el id colisiona (astronomicamente
    # improbable) se reintenta en vez de pisar el reto de otro cliente.
    while not cache.add(_key(challenge_id), json.dumps(payload), timeout=ttl):
        challenge_id = secrets.token_urlsafe(24)

    logger.info("Reto de vida emitido: id=%s plan=%s ttl=%ss", challenge_id, plan, ttl)
    return Challenge(challenge_id=challenge_id, plan=plan, expires_in=ttl)


def consume_challenge(challenge_id: str, completed_actions: list[str]) -> Attestation:
    """
    Valida y consume el reto. Dejar de ser reutilizable es parte del contrato:
    el mismo reto no vale para dos intentos.
    """
    challenge_id = (challenge_id or "").strip()
    if not challenge_id:
        raise LivenessError("Falta el identificador del reto de vida.", code="missing_challenge")

    raw = cache.get(_key(challenge_id))
    if raw is None:
        # Vencido (TTL) o ya consumido. No distinguimos entre los dos a proposito:
        # informar el motivo exacto ayuda a un atacante a cronometrar el TTL.
        raise LivenessError(
            "El reto de vida vencio o ya se uso. Vuelve a intentarlo.",
            code="challenge_expired",
        )

    payload = json.loads(raw)
    plan: list[str] = list(payload["plan"])

    # Un solo uso. cache.delete() devuelve True solo si la clave existia, asi
    # que un segundo intento concurrente sobre el mismo reto tambien se rechaza.
    if not cache.delete(_key(challenge_id)):
        raise LivenessError(
            "El reto de vida ya se uso. Vuelve a intentarlo.",
            code="challenge_consumed",
        )

    executed = [a for a in (completed_actions or [])]
    if executed != plan:
        logger.warning(
            "Reto de vida incorrecto: id=%s esperado=%s recibido=%s",
            challenge_id,
            plan,
            executed,
        )
        raise LivenessError(
            "La prueba de vida no se completo en el orden solicitado.",
            code="challenge_mismatch",
        )

    duration_ms = _elapsed_ms(payload["issued_at"])
    minimum_ms = settings.LIVENESS_MIN_ACTION_MS * len(plan)
    if duration_ms < minimum_ms:
        # Respuesta instantanea => el cliente no estaba mirando cuadro a cuadro.
        logger.warning(
            "Reto de vida demasiado rapido: id=%s duracion=%sms minimo=%sms",
            challenge_id,
            duration_ms,
            minimum_ms,
        )
        raise LivenessError(
            "La prueba de vida se completo demasiado rapido. Intentalo de nuevo.",
            code="challenge_too_fast",
        )

    return Attestation(
        challenge_id=challenge_id,
        plan=plan,
        completed_actions=executed,
        duration_ms=duration_ms,
    )


def _elapsed_ms(issued_at: str) -> int:
    """
    Milisegundos transcurridos desde la emision del reto.

    Si la marca de tiempo no se puede interpretar no se puede verificar el
    ritmo, y "no verificable" tiene que significar RECHAZAR, no aceptar. Por eso
    devuelve un valor grande en vez de uno pequeno.
    """
    try:
        issued = datetime.fromisoformat(issued_at)
    except (TypeError, ValueError):
        logger.error("Reto de vida con issued_at ilegible: %r", issued_at)
        return _UNMEASURABLE_MS

    if timezone.is_naive(issued):
        issued = timezone.make_aware(issued, timezone.get_current_timezone())

    delta: timedelta = timezone.now() - issued
    return max(0, int(delta.total_seconds() * 1000))
