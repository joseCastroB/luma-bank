"""Fixtures compartidas por los tests de accounts (HU02/HU03).

La pieza central es `live_challenge`. Los tests de registro y de login facial
NO pueden inventarse un payload de vivacidad a mano: el servidor exige que el
`challenge_id` exista realmente en la cache, que `completed_actions` coincida
exactamente con el plan emitido y que el reto no se haya consumido antes. Por eso
el helper pide un reto de verdad al servicio y lo resuelve.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.services import liveness


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def issue_live_challenge():
    """
    Devuelve una fabrica de payloads de vivacidad válidos.

    Cada llamada emite un reto NUEVO y devuelve el `liveness` correspondiente
    con las acciones ya completadas. Se usa para el caso feliz.

    Para el caso "el cliente miente" se pasan `completed_actions` alterados a
    proposito, manteniendo el `challenge_id` real: eso es exactamente lo que
    haria un atacante.
    """

    def _make(completed_actions=None):
        challenge = liveness.issue_challenge()
        return {
            "challenge_id": challenge.challenge_id,
            "completed_actions": (
                list(challenge.plan) if completed_actions is None else list(completed_actions)
            ),
        }

    return _make


@pytest.fixture
def fast_challenge(issue_live_challenge, settings):
    """
    Igual que `issue_live_challenge` pero con el piso de duracion en 0 ms.

    `consume_challenge` exige que el tiempo transcurrido sea al menos
    LIVENESS_MIN_ACTION_MS por accion. En un test que corre en milisegundos eso
    siempre fallaria por velocidad y enmascararía el motivo real del rechazo,
    asi que para los tests que no evalúan el ritmo se baja ese piso.
    """
    settings.LIVENESS_MIN_ACTION_MS = 0
    return issue_live_challenge


@pytest.fixture
def make_attestation(settings):
    """
    Atestación válida para quien arma datos en el servicio sin pasar por la API
    (por ejemplo el fixture `customer` de los tests de login, que llama a
    `registration.register_customer` directamente).
    """
    settings.LIVENESS_MIN_ACTION_MS = 0

    def _make():
        return liveness.consume_challenge(
            *(lambda c: (c.challenge_id, list(c.plan)))(liveness.issue_challenge())
        )

    return _make
