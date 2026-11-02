import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import type { Operation } from "@/lib/api";
import { capitalize, formatDateTime, formatMoney } from "@/lib/money";
import { ReceiptButton } from "./ReceiptButton";

export function OperationResult({ operation, onNew }: { operation: Operation; onNew: () => void }) {
  const rows: [string, string][] = [
    ["Tipo", capitalize(operation.kind_label)],
    ["Código de operación", operation.operation_code],
    ["Fecha", formatDateTime(operation.completed_at)],
    ["Monto", formatMoney(operation.amount, operation.currency)],
  ];
  if (Number(operation.fee) > 0) rows.push(["Comisión", formatMoney(operation.fee, operation.currency)]);
  if (operation.exchange_rate) rows.push(["Tipo de cambio aplicado", operation.exchange_rate]);
  if (operation.destination_amount && operation.destination_currency) {
    rows.push(["Monto abonado", formatMoney(operation.destination_amount, operation.destination_currency)]);
  }
  rows.push(["Saldo de tu cuenta de origen", formatMoney(operation.source_balance_after, operation.currency)]);
  if (operation.destination_balance_after) {
    const destinationCurrency = operation.destination_currency ?? operation.currency;
    if (operation.kind !== "third_party_transfer") {
      rows.push([
        "Saldo de tu cuenta de destino",
        formatMoney(operation.destination_balance_after, destinationCurrency),
      ]);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Alert tone="success">Operación realizada con éxito.</Alert>
      <SummaryList rows={rows} />
      <div className="flex flex-wrap gap-3">
        <ReceiptButton code={operation.operation_code} variant="button" />
        <Button variant="ghost" onClick={onNew}>
          Hacer otra operación
        </Button>
      </div>
    </div>
  );
}

export function SummaryList({ rows }: { rows: [string, string][] }) {
  return (
    <dl className="divide-y divide-white/10 rounded-xl border border-white/10 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex flex-wrap justify-between gap-x-4 gap-y-1 p-3">
          <dt className="text-white/60">{label}</dt>
          <dd className="font-medium break-all text-white">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
