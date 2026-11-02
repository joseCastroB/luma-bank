"""
Actualización del rostro de un cliente ya autenticado.

El vector nuevo se sube primero a MinIO y la referencia se cambia en una
transacción. El objeto anterior solo se borra cuando el cambio ya quedó guardado:
si algo falla, el cliente conserva su rostro vigente.
"""

from __future__ import annotations

from django.db import transaction

from ..models import FaceEmbedding
from . import audit, crypto, face_store, security_mail


def update_face(request, *, descriptor: list[float], algorithm: str) -> FaceEmbedding:
    user = request.user
    previous = FaceEmbedding.objects.filter(user=user).first()
    previous_location = (previous.bucket, previous.object_key) if previous else None

    bucket, object_key = face_store.put_embedding(user.pk, crypto.encrypt_embedding(descriptor))
    try:
        with transaction.atomic():
            embedding, _ = FaceEmbedding.objects.update_or_create(
                user=user,
                defaults={
                    "bucket": bucket,
                    "object_key": object_key,
                    "algorithm": algorithm[:128],
                    "dimensions": len(descriptor),
                },
            )
            audit.record(
                request,
                "biometrics.update",
                entity="embedding_facial",
                entity_id=str(embedding.pk),
                algorithm=embedding.algorithm,
            )
    except Exception:
        face_store.delete_embedding(bucket, object_key)
        raise

    if previous_location:
        face_store.delete_embedding(*previous_location)
    security_mail.notify_biometrics_updated(user)
    return embedding
