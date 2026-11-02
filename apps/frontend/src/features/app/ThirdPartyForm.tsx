import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { ApiError, transferThirdParty, type Account, type Operation } from "@/lib/api";
import { formatMoney, isValidAmount, maskAccount } from "@/lib/money";
import { OperationResult, SummaryList } from "./OperationResult";

const LUMA_CCI_PREFIX = "0110021";

/** Transferencia a otra cuenta por CCI: de Luma Bank o de otro banco. */
export function ThirdPartyForm({ accounts, onDone }: { accounts: Account[]; onDone: () => void }) {
  const active = accounts.filter((a) => a.status === "active");
  const [sourceNumber, setSourceNumber] = useState(active[0]?.number ?? "");
  const [cci, setCci] = useState("");
  const [holder, setHolder] = useState("");
  const [bank, setBank] = useState("");
  const [amount, setAmount] = useState("");
  const [concept, setConcept] = useState("");
  const [totp, setTotp] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Operation | null>(null);

  const source = active.find((a) => a.number === sourceNumber);
  if (!source) return <Alert tone="info">Necesitas una cuenta activa para transferir.</Alert>;

  if (result) {
    return (
      <OperationResult
        operation={result}
        onNew={() => {
          setResult(null);
          setCci("");
          setHolder("");
          setBank("");
          setAmount("");
          setConcept("");
          setTotp("");
          setNeedsTotp(false);
          setReviewing(false);
        }}
      />
    );
  }

  const cciOk = /^\d{20}$/.test(cci);
  const isExternal = cciOk && !cci.startsWith(LUMA_CCI_PREFIX);
  const amountOk = isValidAmount(amount);
  const enoughFunds = amountOk && Number(amount) <= Number(source.available_balance);
  const canReview = cciOk && enoughFunds && (!isExternal || Boolean(holder.trim() && bank.trim()));

  async function confirm() {
    if (!source) return;
    setLoading(true);
    setError(null);
    try {
      const operation = await transferThirdParty({
        source_number: source.number,
        destination_cci: cci,
        amount,
        concept: concept.trim(),
        holder: isExternal ? holder.trim() : "",
        bank: isExternal ? bank.trim() : "",
        totp,
      });
      onDone();
      setResult(operation);
    } catch (err) {
      if (err instanceof ApiError && (err.code === "totp_required" || err.code === "totp_invalid")) {
        setNeedsTotp(true);
        setTotp("");
        // Pedir el código es un paso normal del flujo, no un error.
        if (err.code === "totp_required") return;
      }
      setError(err instanceof ApiError ? err.message : "No se pudo completar la transferencia.");
    } finally {
      setLoading(false);
    }
  }

  if (reviewing) {
    const rows: [string, string][] = [
      ["Desde", maskAccount(source.number)],
      ["CCI de destino", cci],
    ];
    if (isExternal) {
      rows.push(["Titular", holder.trim()], ["Banco", bank.trim()]);
    }
    rows.push(["Monto", formatMoney(amount, source.currency)]);
    if (concept.trim()) rows.push(["Concepto", concept.trim()]);

    return (
      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-white">Confirma la transferencia</h2>
        <SummaryList rows={rows} />
        {needsTotp && (
          <TextField
            label="Código de tu app de autenticación"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="123456"
            value={totp}
            onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
            hint="Por el monto, necesitamos confirmar que eres tú."
          />
        )}
        {error && <Alert tone="error">{error}</Alert>}
        <div className="flex flex-wrap gap-3">
          <Button onClick={confirm} disabled={loading || (needsTotp && totp.length < 6)}>
            {loading ? "Procesando…" : "Confirmar transferencia"}
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              setReviewing(false);
              setError(null);
            }}
            disabled={loading}
          >
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
            {maskAccount(a.number)} · {formatMoney(a.available_balance, a.currency)}
          </option>
        ))}
      </SelectField>
      <TextField
        label="CCI de destino"
        inputMode="numeric"
        maxLength={20}
        placeholder="20 dígitos"
        value={cci}
        onChange={(e) => setCci(e.target.value.replace(/\D/g, ""))}
        error={cci && !cciOk ? `El CCI debe tener 20 dígitos (llevas ${cci.length}).` : null}
      />
      {isExternal && (
        <>
          <TextField label="Titular de la cuenta" maxLength={150} value={holder} onChange={(e) => setHolder(e.target.value)} />
          <TextField label="Banco de destino" maxLength={80} value={bank} onChange={(e) => setBank(e.target.value)} />
        </>
      )}
      <TextField
        label={`Monto en ${source.currency}`}
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
      <TextField label="Concepto (opcional)" maxLength={140} value={concept} onChange={(e) => setConcept(e.target.value)} />
      <Button type="submit" size="lg" disabled={!canReview}>
        Continuar
      </Button>
    </form>
  );
}
