import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ApiError, getAccounts, getMe, openAccount, type Account, type AccountsResponse, type Me } from "@/lib/api";
import { currencyName, formatDate, formatMoney, maskAccount } from "@/lib/money";

export function AppHome() {
  const [me, setMe] = useState<Me | null>(null);
  const [data, setData] = useState<AccountsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => getAccounts().then(setData), []);

  useEffect(() => {
    Promise.all([getMe().then(setMe), load()]).catch(() => {
      setError("No se pudo cargar tu información.");
    });
  }, [load]);

  return (
    <>
      {error && <Alert tone="error">{error}</Alert>}
      {!error && (!me || !data) && <p className="text-white/60">Cargando…</p>}
      {me && data && (
        <>
          <h1 className="text-2xl font-bold text-white">Hola, {me.full_name || me.email}</h1>
          <p className="text-sm text-white/60">{me.email}</p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {data.accounts.map((account) => (
              <AccountCard key={account.number} account={account} />
            ))}
          </div>
          {data.accounts.length === 0 && (
            <p className="mt-6 text-sm text-white/60">Aún no tienes cuentas abiertas.</p>
          )}

          <OpenAccountPanel data={data} onOpened={load} />
        </>
      )}
    </>
  );
}

function AccountCard({ account }: { account: Account }) {
  return (
    <Link
      to={`/app/cuentas/${account.number}`}
      className="block rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-cyan/40"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
        Ahorros en {currencyName(account.currency)}
      </p>
      <p className="mt-1 font-mono text-sm tracking-wider text-white/70">{maskAccount(account.number)}</p>

      <p className="mt-4 text-xs text-white/50">Saldo disponible</p>
      <p className="text-2xl font-bold text-white">
        {formatMoney(account.available_balance, account.currency)}
      </p>
      <p className="mt-1 text-xs text-white/50">
        Saldo contable: {formatMoney(account.balance, account.currency)}
      </p>

      {account.savings_rate && (
        <p className="mt-3 text-sm text-cyan-soft">
          TREA {account.savings_rate.trea}%{" "}
          <span className="text-xs text-white/50">
            vigente desde {formatDate(account.savings_rate.valid_from)}
          </span>
        </p>
      )}
      {account.status !== "active" && (
        <p className="mt-2 text-xs text-red-300">Cuenta {account.status_label}</p>
      )}
    </Link>
  );
}

function OpenAccountPanel({ data, onOpened }: { data: AccountsResponse; onOpened: () => Promise<void> }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opened, setOpened] = useState<Account | null>(null);

  const rate = data.savings_rates.find((r) => r.currency === selected);

  async function confirm() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const account = await openAccount(selected);
      await onOpened();
      setOpened(account);
      setSelected(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo abrir la cuenta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <h2 className="text-lg font-semibold text-white">Abrir una cuenta de ahorro</h2>
      <p className="mt-1 text-sm text-white/60">
        Tu dinero gana intereses cada día, sin comisiones de mantenimiento.
      </p>

      {opened && (
        <div className="mt-4">
          <Alert tone="success">
            Abrimos tu cuenta {maskAccount(opened.number)} con saldo inicial de{" "}
            {formatMoney(opened.balance, opened.currency)}
            {opened.savings_rate && <> y TREA de {opened.savings_rate.trea}%</>}.
          </Alert>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {!selected && (
        <div className="mt-4 flex flex-wrap gap-3">
          {data.savings_rates.map((r) => (
            <Button
              key={r.currency}
              variant="secondary"
              onClick={() => {
                setSelected(r.currency);
                setOpened(null);
                setError(null);
              }}
            >
              En {currencyName(r.currency)} · TREA {r.trea}%
            </Button>
          ))}
        </div>
      )}

      {selected && rate && (
        <div className="mt-4 rounded-xl border border-cyan/30 p-4">
          <p className="text-sm text-white/80">
            Vas a abrir una cuenta de ahorro en {currencyName(selected)} con saldo inicial de{" "}
            {formatMoney(0, selected)} y TREA de <strong className="text-cyan">{rate.trea}%</strong>,
            vigente desde {formatDate(rate.valid_from)}.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={confirm} disabled={loading}>
              {loading ? "Abriendo…" : "Confirmar apertura"}
            </Button>
            <Button variant="ghost" onClick={() => setSelected(null)} disabled={loading}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
