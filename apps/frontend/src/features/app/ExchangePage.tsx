import { Alert } from "@/components/ui/Alert";
import { BetweenAccountsForm } from "./BetweenAccountsForm";
import { useAccounts } from "./useAccounts";

export function ExchangePage() {
  const { accounts, error, reload } = useAccounts();

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-bold text-white">Convertir moneda</h1>
      <p className="mt-1 text-sm text-white/60">
        Mueve dinero entre tus cuentas en soles y dólares al tipo de cambio oficial de SUNAT.
      </p>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        {error && <Alert tone="error">{error}</Alert>}
        {!error && !accounts && <p className="text-sm text-white/60">Cargando…</p>}
        {accounts && <BetweenAccountsForm accounts={accounts} mode="exchange" onDone={reload} />}
      </div>
    </div>
  );
}
