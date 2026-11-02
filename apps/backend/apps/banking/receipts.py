"""Comprobante en PDF de una operación."""

from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import Transaction


def mask(number: str | None) -> str:
    return f"****{number[-4:]}" if number else "-"


def _rows(tx: Transaction) -> list[tuple[str, str]]:
    destination = (
        tx.destination_account.number if tx.destination_account else tx.external_destination_number
    )
    rows = [
        ("Código de operación", tx.operation_code),
        ("Fecha", f"{timezone.localtime(tx.completed_at or tx.created_at):%d/%m/%Y %H:%M}"),
        ("Tipo", tx.get_kind_display()),
        ("Estado", tx.get_status_display()),
        ("Cuenta de origen", mask(tx.source_account.number if tx.source_account else None)),
        ("Cuenta de destino", mask(destination)),
    ]
    if tx.external_destination_holder:
        rows.append(("Titular de destino", tx.external_destination_holder))
    if tx.external_destination_bank:
        rows.append(("Banco de destino", tx.external_destination_bank))
    rows.append(("Monto", f"{tx.currency} {tx.amount:,.2f}"))
    if tx.fee:
        rows.append(("Comisión", f"{tx.currency} {tx.fee:,.2f}"))
    if tx.exchange_rate:
        rows.append(("Tipo de cambio", f"{tx.exchange_rate:.4f}"))
        rows.append(("Monto abonado", f"{tx.destination_currency} {tx.destination_amount:,.2f}"))
    if tx.concept:
        rows.append(("Concepto", tx.concept))
    return rows


def render_receipt(tx: Transaction) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A5)
    pdf.setTitle(f"Comprobante {tx.operation_code}")
    width, height = A5

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(15 * mm, height - 20 * mm, "Luma Bank")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(15 * mm, height - 27 * mm, "Comprobante de operación")
    pdf.line(15 * mm, height - 31 * mm, width - 15 * mm, height - 31 * mm)

    y = height - 40 * mm
    for label, value in _rows(tx):
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(15 * mm, y, label)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - 15 * mm, y, value[:60])
        y -= 7 * mm

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
