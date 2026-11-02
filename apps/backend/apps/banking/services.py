"""
Servicios del dominio bancario: apertura de cuentas y movimiento de dinero.

Toda operación bloquea las cuentas (`select_for_update`, en orden de pk para
evitar interbloqueos) y escribe saldos y transacción en la misma transacción de
base de datos: o se aplica completa o no se aplica.
"""

from __future__ import annotations

import logging
import secrets
import string
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.services import auth

from . import exchange_rates
from .models import Account, ExchangeRate, SavingsRate, Transaction

logger = logging.getLogger("luma.banking")
User = get_user_model()

# Código de entidad + oficina (ficticios para el proyecto).
_BANK_CODE = "011"
_BRANCH_CODE = "0021"
LUMA_CCI_PREFIX = f"{_BANK_CODE}{_BRANCH_CODE}"

SUPPORTED_CURRENCIES = ("PEN", "USD")
CENT = Decimal("0.01")


class BankingError(Exception):
    def __init__(self, message: str, *, code: str = "", status: int = 400, **extra):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.extra = extra


def _luhn_check_digit(number: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def generate_account_number() -> str:
    """Número de 20 dígitos: entidad(3) + oficina(4) + serial(12) + control(1)."""
    for _ in range(10):
        serial = "".join(secrets.choice("0123456789") for _ in range(12))
        body = f"{_BANK_CODE}{_BRANCH_CODE}{serial}"
        number = body + _luhn_check_digit(body)
        if not Account.objects.filter(number=number).exists():
            return number
    raise RuntimeError("No se pudo generar un número de cuenta único.")


def open_account(user, *, currency: str = "PEN") -> Account:
    return Account.objects.create(
        user=user,
        number=generate_account_number(),
        currency=currency,
    )


def generate_operation_code() -> str:
    """20 caracteres: LB + fecha(6) + aleatorio(12)."""
    alphabet = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"LB{timezone.localdate():%y%m%d}{random_part}"


def current_savings_rate(currency: str) -> SavingsRate | None:
    return (
        SavingsRate.objects.filter(currency=currency, valid_from__lte=timezone.localdate())
        .order_by("-valid_from")
        .first()
    )


def available_balance(account: Account) -> Decimal:
    """Saldo contable menos lo comprometido en operaciones aún pendientes."""
    pending = account.outgoing_transactions.filter(status=Transaction.Status.PENDING)
    return account.balance - sum((t.amount + t.fee for t in pending), Decimal("0"))


def _require_verified(user) -> None:
    if not user.is_identity_verified:
        raise BankingError(
            "Tu identidad aún no está verificada. No puedes realizar esta operación.",
            code="identity_not_verified",
            status=403,
        )


def open_savings_account(user, *, currency: str) -> Account:
    _require_verified(user)
    if currency not in SUPPORTED_CURRENCIES:
        raise BankingError("Moneda no disponible.", code="invalid_currency")
    if current_savings_rate(currency) is None:
        raise BankingError(
            "Aún no hay una TREA vigente para esta moneda.", code="no_rate", status=503
        )

    with transaction.atomic():
        # Serializa las aperturas del cliente para que el límite no se pueda rebasar.
        User.objects.select_for_update().get(pk=user.pk)
        opened = Account.objects.filter(user=user, currency=currency).exclude(
            status=Account.Status.CLOSED
        )
        if opened.count() >= settings.MAX_ACCOUNTS_PER_CURRENCY:
            raise BankingError(
                f"Ya tienes el máximo de {settings.MAX_ACCOUNTS_PER_CURRENCY} cuentas "
                f"en {currency}.",
                code="too_many_accounts",
                status=409,
            )
        return open_account(user, currency=currency)


# --- Movimiento de dinero ---------------------------------------------------


def settle(
    *,
    kind: str,
    amount: Decimal,
    source: Account | None = None,
    destination: Account | None = None,
    credited: Decimal | None = None,
    fee: Decimal = Decimal("0"),
    concept: str = "",
    rate: Decimal | None = None,
    external: dict | None = None,
) -> Transaction:
    """Aplica saldos y registra la operación. Las cuentas ya deben estar bloqueadas."""
    for account in (source, destination):
        if account is not None and account.status != Account.Status.ACTIVE:
            raise BankingError(
                f"La cuenta terminada en {account.number[-4:]} no está activa.",
                code="account_inactive",
                status=409,
            )

    credited = amount if credited is None else credited
    if source is not None:
        if source.balance < amount + fee:
            raise BankingError(
                "Saldo insuficiente para realizar la operación.",
                code="insufficient_funds",
                status=409,
            )
        source.balance -= amount + fee
        source.save(update_fields=["balance"])
    if destination is not None:
        destination.balance += credited
        destination.save(update_fields=["balance"])

    is_conversion = rate is not None
    return Transaction.objects.create(
        operation_code=generate_operation_code(),
        kind=kind,
        source_account=source,
        destination_account=destination,
        amount=amount,
        fee=fee,
        currency=(source or destination).currency,
        concept=concept[:140],
        status=Transaction.Status.COMPLETED,
        exchange_rate=rate,
        destination_amount=credited if is_conversion else None,
        destination_currency=destination.currency if is_conversion else None,
        source_balance_after=source.balance if source else None,
        destination_balance_after=destination.balance if destination else None,
        completed_at=timezone.now(),
        **(external or {}),
    )


def _lock(*accounts: Account) -> list[Account]:
    """Devuelve las cuentas bloqueadas y recargadas, en el orden recibido."""
    pks = [a.pk for a in accounts]
    locked = {
        a.pk: a for a in Account.objects.select_for_update().filter(pk__in=pks).order_by("pk")
    }
    return [locked[pk] for pk in pks]


def _own_account(user, number: str) -> Account:
    account = Account.objects.filter(user=user, number=number).first()
    if account is None:
        raise BankingError("No encontramos esa cuenta.", code="account_not_found", status=404)
    return account


def quote(amount: Decimal, *, from_currency: str, to_currency: str, rate: ExchangeRate) -> tuple:
    """Monto a abonar y tipo aplicado: el cliente compra dólares a venta y los vende a compra."""
    if {from_currency, to_currency} != set(SUPPORTED_CURRENCIES):
        raise BankingError("Solo se convierte entre soles y dólares.", code="invalid_currency")
    if from_currency == "PEN":
        applied, credited = rate.sell, amount / rate.sell
    else:
        applied, credited = rate.buy, amount * rate.buy
    credited = credited.quantize(CENT, rounding=ROUND_HALF_UP)
    if credited <= 0:
        raise BankingError("El monto es demasiado pequeño para convertirlo.", code="amount_too_low")
    return credited, applied


def _current_rate() -> ExchangeRate:
    try:
        return exchange_rates.current_rate()
    except exchange_rates.ExchangeRateUnavailable as exc:
        raise BankingError(
            "El tipo de cambio oficial no está disponible. Inténtalo más tarde.",
            code="exchange_rate_unavailable",
            status=503,
        ) from exc


def transfer_between_own_accounts(
    user, *, source_number: str, destination_number: str, amount: Decimal, concept: str = ""
) -> Transaction:
    """Entre cuentas del mismo cliente. Si difieren en moneda, se aplica el tipo de cambio."""
    _require_verified(user)
    if source_number == destination_number:
        raise BankingError("Elige dos cuentas distintas.", code="same_account")
    source = _own_account(user, source_number)
    destination = _own_account(user, destination_number)

    # La consulta a SUNAT queda fuera de la transacción: no retiene los bloqueos.
    credited = applied = None
    is_conversion = source.currency != destination.currency
    if is_conversion:
        credited, applied = quote(
            amount,
            from_currency=source.currency,
            to_currency=destination.currency,
            rate=_current_rate(),
        )

    with transaction.atomic():
        source, destination = _lock(source, destination)
        return settle(
            kind=(
                Transaction.Kind.CURRENCY_EXCHANGE
                if is_conversion
                else Transaction.Kind.OWN_TRANSFER
            ),
            amount=amount,
            source=source,
            destination=destination,
            credited=credited,
            rate=applied,
            concept=concept,
        )


def _check_totp(user, code: str, *, amount: Decimal, currency: str) -> None:
    threshold = settings.TRANSFER_TOTP_THRESHOLD[currency]
    if amount <= threshold:
        return
    if auth.is_locked(user):
        raise BankingError(
            "Tu cuenta está bloqueada temporalmente por intentos fallidos.",
            code="locked",
            status=423,
        )
    if not code:
        raise BankingError(
            f"Por encima de {currency} {threshold} necesitamos tu código de verificación.",
            code="totp_required",
            status=403,
        )
    if not auth.verify_totp(user, code):
        locked = auth._register_failure(user, facial=False)
        raise BankingError(
            "Código de verificación incorrecto.",
            code="locked" if locked else "totp_invalid",
            status=423 if locked else 403,
        )
    auth.reset_failures(user)


def transfer_to_third_party(
    user,
    *,
    source_number: str,
    destination_cci: str,
    amount: Decimal,
    concept: str = "",
    holder: str = "",
    bank: str = "",
    totp: str = "",
) -> Transaction:
    """Hacia una cuenta de otro cliente de Luma Bank o de otro banco, por CCI."""
    _require_verified(user)
    source = _own_account(user, source_number)
    destination = Account.objects.filter(number=destination_cci).first()

    if destination is not None and destination.user_id == user.pk:
        raise BankingError(
            "Esa cuenta es tuya: usa la transferencia entre cuentas propias.", code="own_account"
        )
    if destination is None and destination_cci.startswith(LUMA_CCI_PREFIX):
        raise BankingError(
            "Ese CCI no corresponde a ninguna cuenta de Luma Bank.",
            code="account_not_found",
            status=404,
        )
    if destination is not None and destination.currency != source.currency:
        raise BankingError(
            "La cuenta destino está en otra moneda. Elige una cuenta origen en la misma moneda.",
            code="currency_mismatch",
        )
    if destination is None and not (holder.strip() and bank.strip()):
        raise BankingError(
            "Indica el titular y el banco de la cuenta destino.", code="external_data_required"
        )

    _check_totp(user, totp, amount=amount, currency=source.currency)

    with transaction.atomic():
        if destination is None:
            [source] = _lock(source)
            return settle(
                kind=Transaction.Kind.INTERBANK_TRANSFER,
                amount=amount,
                source=source,
                fee=settings.INTERBANK_FEE,
                concept=concept,
                external={
                    "external_destination_number": destination_cci,
                    "external_destination_holder": holder.strip()[:150],
                    "external_destination_bank": bank.strip()[:80],
                },
            )
        source, destination = _lock(source, destination)
        return settle(
            kind=Transaction.Kind.THIRD_PARTY_TRANSFER,
            amount=amount,
            source=source,
            destination=destination,
            concept=concept,
        )
