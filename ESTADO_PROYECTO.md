# Estado del proyecto — HU02 / HU03 (registro y login facial)

> Documento de traspaso. Última actualización: 2026-10-05.
> Rama: `luis-vergara/feature` (sin upstream). `.atl/` sigue sin trackear.
> Para retomar: leer este archivo y la sección "Próximos pasos".

---

## 1. Qué se pidió

Ítem 5 de APF2: autenticación y autorización robustas. En la práctica se /
avanzó en dos frentes:

- **Alineación de contrato** entre frontend y backend para registro y login facial.
- **RNF-06**: degradación cuando RENIEC (API de terceros) no está disponible.

El documento de requisitos menciona "RENIEC mediante API de terceros", pero **no
nombra un proveedor concreto**. El proveedor real es **Software Lion / LionAPI**,
confirmado por el usuario.

---

## 2. Contrato con LionAPI

Endpoint base:

```
GET https://www.softwarelion.pe/api/lion-api/v1/consulta-dni/:dni
Header: x-api-key: <API_KEY>
```

Respuesta exitosa:

```json
{
  "success": true,
  "message": "exito",
  "result": {
    "dni": "...",
    "paterno": "...",
    "materno": "...",
    "nombres": "...",
    "sexo": "M",
    "codigo_verificacion": "..."
  }
}
```

### Trampas del proveedor (importante)

- **Devuelve HTTP 200 incluso cuando el DNI no existe** y también ante errores
  internos del proveedor. El status code NO alcanza: hay que leer `success` y
  `message`.
- Sin key o key inválida → **401**. Límite de consultas agotado → **429**.

Clasificación implementada en `identity.py`:

| Situación | Excepción |
|---|---|
| `success: false`, mensaje "no encontrado" | `IdentityNotFound` |
| `success: false`, otro mensaje | `IdentityServiceError` |
| HTTP 429 / quota | `LionApiQuotaExceeded` |

---

## 3. Seguridad: la API key

**La key se expuso en el chat de una sesión anterior.** Ya no está en ningún archivo
del repo (`.env` está en `.gitignore` y contiene un placeholder).

Pendiente antes de integrar en vivo: **rotar la key en Software Lion** y poner la
nueva en `.env`. Sin esto no se puede probar contra el proveedor real.

---

## 4. Vivacidad: qué cambió

El diseño anterior era inservible: el frontend mandaba `passed: true` y unos
`checks`, es decir, **el cliente se autodeclaraba vivo**. Eso no vale nada: cualquiera
podría mandar `passed: true`.

Ahora el reto lo emite el servidor:

- `POST /api/v1/accounts/liveness/challenge/` → `{challenge_id, plan, expires_in}`
- El `plan` lo sortea el servidor: `blink`, `head_turn_left`, `head_turn_right`.
- Se guarda en Valkey, **TTL 180 s**, y es de **un solo uso**.
- El cliente devuelve `{challenge_id, completed_actions}`.
- El backend compara contra el plan emitido y valida el ritmo humano
  (`LIVENESS_MIN_ACTION_MS`), así que no basta con inventarse la respuesta.

Códigos de error del servicio de vivacidad:

| Código | Significado |
|---|---|
| `challenge_expired` | No existe, venció o se consumió |
| `challenge_consumed` | Ya se usó (replay) |
| `challenge_mismatch` | Gestos distintos al plan emitido |
| `challenge_too_fast` | Se ejecutó más rápido de lo humano |

En login, un fallo de vivacidad se registra como `BAD_LIVENESS` con
`suspicious=True` y **no cuenta como fallo facial** (no gasta un intento del
usuario por un reto manipulado).

---

## 5. RNF-06: registro degradado

Cuando LionAPI devuelve 429 (sin créditos):

- `validar-dni` responde **202** y el frontend **no** lo trata como DNI inválido.
- El registro continúa en modo degradado; como no hay datos de RENIEC,
  **el usuario declara su nombre** (`full_name`).
- La cuenta queda con `is_identity_verified=False` y la respuesta incluye
  `identity_pending_review: true`.
- Un fallo técnico distinto (503) sigue siendo error duro.

Frontend: `StepDni` acepta el 202, `StepConfirmar` pide el nombre declarado,
`StepListo` avisa que la identidad quedó pendiente de revisión manual.

---

## 6. Lo que YA está implementado y verificado

### Backend

- Anti-replay de biometría con huella HMAC e índice único.
- Cifrado AES-256-GCM del descriptor facial, guardado en MinIO.
- TOTP (2FA).
- Lockout por intentos fallidos.
- Liveness de un solo uso, con el orden correcto:
  `consume_challenge` (línea 89) **antes** de `verify_face` (línea 108) en
  `views_auth.py`.
- Tests de contrato real de LionAPI: `test_identity_lionapi_contract.py`.

**Verificación:** `55 passed` en `apps/accounts/tests/`.

### Frontend

- `api.ts`: tipos `LivenessChallenge`, `LivenessResult`, y funciones
  `requestLivenessChallenge`, `loginFacial`, `registrar` con el contrato nuevo.
- `shared/liveness.ts`: ejecuta el plan que envía el servidor.
- `shared/FaceCapture.tsx`: recibe `plan`/`challengeId`, devuelve descriptor +
  `completed_actions`.
- `shared/useLivenessChallenge.ts`: pide y renueva retos.
- `StepRostro` y `LoginFacialStep` ya no mandan `passed: true`.
- Wizard con soporte de registro degradado.

**Verificación:** `npm run typecheck`, `npm run lint` y `npm run build` en verde.
El botón "simular prueba de vida" solo existe en `import.meta.env.DEV` y se
confirmó que **no aparece en el bundle de producción**.

---

## 7. Mejora continua (pendiente, acordado)

**El bloqueo de la cuenta degradada NO existe todavía.** Decisión acordada: no se
construye ahora, queda como mejora continua.

Situación real:

- `is_identity_verified` se escribe en `registration.py:133` y se lee solo en el
  admin (lista/filtro). **Nadie más lo consulta.**
- `apps/banking/` **no tiene vistas ni tests** (`tests/` solo contiene
  `__init__.py`). No existe punto de aplicación para un bloqueo.
- Consecuencia: una cuenta registrada en modo degradado abre y puede operar como
  si estuviera verificada.

Por eso el texto de la UI dice "te avisaremos cuando esté confirmado" y **no**
promete un congelamiento de saldo.

Cuando se implemente, requiere:
1. Módulo de transferencias con vistas.
2. Chequeo de `is_identity_verified` al autorizar una transferencia.
3. Tests que cubran el caso bloqueado y el permitido.

---

## 8. Otros pendientes

- **Roles y autorización de dominio** (pedido explícito del usuario, sin empezar).
- **Desbloqueo administrativo manual** de cuentas bloqueadas.
- **Patrón DAO/Repository** para las apps.
- **Corrección del análisis de negocio**: la afirmación de "no reversibilidad"
  de las transacciones es incorrecta.
- **API key rotada** para poder probar contra LionAPI real.

---

## 9. Errores a no repetir

En esta sesión se armó un script E2E propio contra el servidor real. **No aportó
nada** y conviene no repetirlo:

- **Redundante:** todos los casos ya estaban cubiertos como tests en
  `test_registro_api.py` y `test_login_api.py`, usando las fixtures
  `issue_live_challenge` y `fast_challenge` de `tests/conftest.py`.
- **Sus "hallazgos" eran falsos:** los 401 idénticos de dos casos parecían una
  falta de distinción entre fallo de vivacidad y de rostro, pero en realidad la
  cuenta nunca se creó (contraseña de menos de 12 caracteres), así que ambos
  casos cortaron en `resolve_user` (`views_auth.py:73`) antes de llegar a
  vivacidad.
- **Chocó con los throttles** (`registro: 5/min`, `login: 10/min`), que están
  puestos a propósito. **No hay que desactivarlos para que un test pase.**

Regla: para probar el backend se usa `pytest` con las fixtures existentes, no un
script HTTP a mano.

---

## 10. Cómo retomar

```bash
# Backend (contenedores ya no están levantados)
docker compose up -d
cd apps/backend && python -m pytest apps/accounts/tests/ -q

# Frontend
cd apps/frontend && npm run typecheck && npm run lint && npm run build
```

Orden sugerido para la próxima sesión: roles/autorización → módulo de
transferencias con el bloqueo de identidad → DAO/Repository.

---

## 11. Archivos tocados en este frente

**Backend**
- `apps/backend/apps/accounts/services/identity.py` — consulta y clasificación LionAPI
- `apps/backend/apps/accounts/services/liveness.py` — emisión/consumo del reto *(nuevo)*
- `apps/backend/apps/accounts/services/auth.py` — verificación facial, lockout
- `apps/backend/apps/accounts/services/crypto.py` — AES-256-GCM
- `apps/backend/apps/accounts/services/registration.py` — registro normal y degradado
- `apps/backend/apps/accounts/views.py` — `validar-dni` con respuesta 202
- `apps/backend/apps/accounts/views_auth.py` — login facial y orden de validación
- `apps/backend/apps/accounts/serializers.py` — `challenge_id`, `completed_actions`, `full_name`
- `apps/backend/apps/accounts/models.py` — `FaceEmbedding`, `LivenessAttestation`
- `apps/backend/apps/accounts/urls.py` — ruta del reto
- `apps/backend/apps/accounts/tests/conftest.py` — fixtures de reto *(nuevo)*
- `apps/backend/apps/accounts/tests/test_identity_lionapi_contract.py` *(nuevo)*
- `apps/backend/conftest.py` — fail-safe contra llamadas reales
- `apps/backend/config/settings/base.py` — settings de LionAPI, cache, throttles
- `.env.example` — contrato documentado sin secretos

**Frontend**
- `apps/frontend/src/lib/api.ts` — tipos y cliente HTTP
- `apps/frontend/src/features/auth/shared/liveness.ts` — detector por plan
- `apps/frontend/src/features/auth/shared/FaceCapture.tsx` — cámara y reto
- `apps/frontend/src/features/auth/shared/useLivenessChallenge.ts` *(nuevo)*
- `apps/frontend/src/features/auth/registro/RegistroWizard.tsx`
- `apps/frontend/src/features/auth/registro/steps/StepDni.tsx`
- `apps/frontend/src/features/auth/registro/steps/StepConfirmar.tsx`
- `apps/frontend/src/features/auth/registro/steps/StepRostro.tsx`
- `apps/frontend/src/features/auth/registro/steps/StepListo.tsx`
- `apps/frontend/src/features/auth/login/LoginFacialStep.tsx`
- `apps/frontend/src/components/ui/Alert.tsx` — nuevo tono `warning`