import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import {
  ApiError,
  convertCurrency,
  getExchangeQuote,
  transferOwn,
  type Account,
  type ExchangeQuote,
  type Operation,
} from "@/lib/api";
import { currencyName, formatDate, formatMoney, isValidAmount, maskAccount } from "@/lib/money";
import { OperationResult, SummaryList } from "./OperationResult";

const QUOTE_DELAY_MS = 400;

function accountLabel(account: Account) {
  return `${maskAccount(account.number)} · ${formatMoney(account.available_balance, account.currency)}`;
}

/** Mueve dinero entre cuentas del cliente; si difieren en moneda, cotiza con el tipo de cambio. */
export function BetweenAccountsForm({
  accounts,
  mode,
  onDone,
}: {
  accounts: Account[];
  mode: "transfer" | "exchange";
  onDone: () => void;
}) {
  const active = accounts.filter((a) => a.status === "active");
  const [sourceNumber, setSourceNumber] = useState(active[0]?.number ?? "");
  const [destinationNumber, setDestinationNumber] = useState("");
  const [amount, setAmount] = useState("");
  const [concept, setConcept] = useState("");
  const [quote, setQuote] = useState<{ key: string; value: ExchangeQuote | null; error: string | null } | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Operation | null>(null);

  const source = active.find((a) => a.number === sourceNumber);
  const destinations = active.filter(
    (a) => a.number !== sourceNumber && (mode === "transfer" || a.currency !== source?.currency),
  );
  const destination = destinations.find((a) => a.number === destinationNumber) ?? destinations[0];

  const isConversion = Boolean(source && destination && source.currency !== destination.currency);
  const amountOk = isValidAmount(amount);
  const quoteKey = isConversion && amountOk ? `${amount}|${source?.currency}|${destination?.currency}` : "";
  const currentQuote = quote?.key === quoteKey ? quote : null;

  useEffect(() => {
    if (!quoteKey || !source || !destination) return;
    let active = true;
    const timer = window.setTimeout(() => {
      getExchangeQuote(amount, source.currency, destination.currency)
        .then((value) => {
          if (active) setQuote({ key: quoteKey, value, error: null });
        })
        .catch((err: unknown) => {
          if (active) {
            const message = err instanceof ApiError ? err.message : "No se pudo obtener el tipo de cambio.";
            setQuote({ key: quoteKey, value: null, error: message });
          }
        });
    }, QUOTE_DELAY_MS);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
    // quoteKey ya resume monto y monedas.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quoteKey]);

  if (result) {
    return (
      <OperationResult
        operation={result}
        onNew={() => {
          setResult(null);
          setAmount("");
          setConcept("");
          setReviewing(false);
        }}
      />
    );
  }

  if (active.length < 2 || !source || !destination) {
    return (
      <Alert tone="info">
        {mode === "exchange"
          ? "Necesitas una cuenta en soles y otra en dólares para convertir. Ábrelas desde Inicio."
          : "Necesitas al menos dos cuentas para transferir entre ellas. Abre otra desde Inicio."}
      </Alert>
    );
  }

  const enoughFunds = amountOk && Number(amount) <= Number(source.available_balance);
  const canReview = enoughFunds && (!isConversion || Boolean(currentQuote?.value));

  async function confirm() {
    if (!source || !destination) return;
    setLoading(true);
    setError(null);
    try {
      const payload = {
        source_number: source.number,
        destination_number: destination.number,
        amount,
        concept: concept.trim(),
      };
      const operation = await (mode === "exchange" ? convertCurrency(payload) : transferOwn(payload));
      onDone();
      setResult(operation);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la operación.");
    } finally {
      setLoading(false);
    }
  }

  if (reviewing) {
    const rows: [string, string][] = [
      ["Desde", `${maskAccount(source.number)} (${currencyName(source.currency)})`],
      ["Hacia", `${maskAccount(destination.number)} (${currencyName(destination.currency)})`],
      ["Monto a debitar", formatMoney(amount, source.currency)],
    ];
    if (currentQuote?.value) {
      rows.push(["Tipo de cambio", currentQuote.value.applied_rate]);
      rows.push(["Monto a abonar", formatMoney(currentQuote.value.credited, destination.currency)]);
    }
    if (concept.trim()) rows.push(["Concepto", concept.trim()]);
    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-white">Confirma la operación</h2>
        <SummaryList rows={rows} />
        {error && <Alert tone="error">{error}</Alert>}
        <div className="flex flex-wrap gap-3">
          <Button onClick={confirm} disabled={loading}>
            {loading ? "Procesando…" : "Confirmar"}
          </Button>
          <Button variant="ghost" onClick={() => setReviewing(false)} disabled={loading}>
            Volver
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (canReview) {
          setError(null);
          setReviewing(true);
        }
      }}
    >
      <SelectField label="Cuenta de origen" value={source.number} onChange={(e) => setSourceNumber(e.target.value)}>
        {active.map((a) => (
          <option key={a.number} value={a.number}>
            {accountLabel(a)}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Cuenta de destino"
        value={destination.number}
        onChange={(e) => setDestinationNumber(e.target.value)}
      >
        {destinations.map((a) => (
          <option key={a.number} value={a.number}>
            {accountLabel(a)}
          </option>
        ))}
      </SelectField>
      <TextField
        label={`Monto en ${currencyName(source.currency)}`}
        inputMode="decimal"
        placeholder="0.00"
        value={amount}
        onChange={(e) => setAmount(e.target.value.trim())}
        error={
          amount && !amountOk
            ? "Ingresa un monto válido, con hasta 2 decimales."
            : amountOk && !enoughFunds
              ? "Saldo insuficiente en la cuenta de origen."
              : null
        }
      />
      {mode === "transfer" && (
        <TextField
          label="Concepto (opcional)"
          maxLength={140}
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
        />
      )}
      {currentQuote?.error && <Alert tone="error">{currentQuote.error}</Alert>}
      {currentQuote?.value && (
        <Alert tone="info">
          Recibirás <strong>{formatMoney(currentQuote.value.credited, destination.currency)}</strong> al tipo de
          cambio {currentQuote.value.applied_rate} ({currentQuote.value.source},{" "}
          {formatDate(currentQuote.value.date)}).
        </Alert>
      )}
      <Button type="submit" size="lg" disabled={!canReview}>
        Continuar
      </Button>
    </form>
  );
}
