import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { BetweenAccountsForm } from "./BetweenAccountsForm";
import { ThirdPartyForm } from "./ThirdPartyForm";
import { useAccounts } from "./useAccounts";

const TABS = [
  { id: "own", label: "Entre mis cuentas" },
  { id: "third", label: "A terceros (CCI)" },
] as const;

export function TransferPage() {
  const { accounts, error, reload } = useAccounts();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("own");

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-bold text-white">Transferir</h1>

      <div className="mt-4 flex gap-2" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={
              "rounded-full px-4 py-2 text-sm font-medium transition " +
              (tab === t.id ? "bg-cyan text-ink" : "text-white/60 hover:text-white")
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        {error && <Alert tone="error">{error}</Alert>}
        {!error && !accounts && <p className="text-sm text-white/60">Cargando…</p>}
        {accounts && tab === "own" && <BetweenAccountsForm accounts={accounts} mode="transfer" onDone={reload} />}
        {accounts && tab === "third" && <ThirdPartyForm accounts={accounts} onDone={reload} />}
      </div>
    </div>
  );
}
