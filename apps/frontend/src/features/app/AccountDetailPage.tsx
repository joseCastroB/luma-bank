import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, getAccount, getMovements, type Account, type Movement, type Paginated } from "@/lib/api";
import { capitalize, currencyName, formatDate, formatDateTime, formatMoney } from "@/lib/money";
import { ReceiptButton } from "./ReceiptButton";

interface Query {
  page: number;
  date_from: string;
  date_to: string;
}

export function AccountDetailPage() {
  const { number = "" } = useParams();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccount(number)
      .then(setAccount)
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError && err.status === 404
            ? "No encontramos esa cuenta."
            : "No se pudo cargar la cuenta.",
        );
      });
  }, [number]);

  return (
    <>
      <Link to="/app" className="text-sm text-white/50 hover:text-white">
        ← Volver a mis cuentas
      </Link>
      <div className="mt-4">{error && <Alert tone="error">{error}</Alert>}</div>
      {!error && !account && <p className="text-white/60">Cargando…</p>}
      {account && (
        <>
          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
              Ahorros en {currencyName(account.currency)}
            </p>
            <p className="mt-1 font-mono text-sm tracking-wider break-all text-white/70">{account.number}</p>
            <dl className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-white/50">Saldo disponible</dt>
                <dd className="text-2xl font-bold text-white">
                  {formatMoney(account.available_balance, account.currency)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-white/50">Saldo contable</dt>
                <dd className="text-lg font-semibold text-white">
                  {formatMoney(account.balance, account.currency)}
                </dd>
                <p className="mt-1 text-xs text-white/50">
                  Intereses por capitalizar: {formatMoney(account.accrued_interest, account.currency)}
                </p>
              </div>
              {account.savings_rate && (
                <div>
                  <dt className="text-xs text-white/50">TREA vigente</dt>
                  <dd className="text-lg font-semibold text-cyan">{account.savings_rate.trea}%</dd>
                  <p className="mt-1 text-xs text-white/50">
                    Desde {formatDate(account.savings_rate.valid_from)}
                  </p>
                </div>
              )}
            </dl>
          </section>
          <MovementHistory number={number} />
        </>
      )}
    </>
  );
}

function MovementHistory({ number }: { number: string }) {
  const [draft, setDraft] = useState({ date_from: "", date_to: "" });
  const [query, setQuery] = useState<Query>({ page: 1, date_from: "", date_to: "" });
  // El resultado guarda su consulta: si no coincide con la actual, sigue cargando.
  const [loaded, setLoaded] = useState<{ query: Query; data: Paginated<Movement> | null; error: string | null } | null>(null);

  useEffect(() => {
    let active = true;
    getMovements(number, query)
      .then((data) => {
        if (active) setLoaded({ query, data, error: null });
      })
      .catch((err: unknown) => {
        if (active) {
          const error = err instanceof ApiError ? err.message : "No se pudo cargar el historial.";
          setLoaded({ query, data: null, error });
        }
      });
    return () => {
      active = false;
    };
  }, [number, query]);

  const loading = loaded?.query !== query;
  const data = loaded?.data ?? null;
  const pageSize = 20;
  const totalPages = data ? Math.max(1, Math.ceil(data.count / pageSize)) : 1;

  function search(e: React.FormEvent) {
    e.preventDefault();
    setQuery({ page: 1, ...draft });
  }

  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-white">Historial de movimientos</h2>

      <form onSubmit={search} className="mt-3 flex flex-wrap items-end gap-3">
        <TextField
          label="Desde"
          type="date"
          value={draft.date_from}
          onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
        />
        <TextField
          label="Hasta"
          type="date"
          value={draft.date_to}
          onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
        />
        <Button type="submit" variant="secondary">
          Filtrar
        </Button>
        {(query.date_from || query.date_to) && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setDraft({ date_from: "", date_to: "" });
              setQuery({ page: 1, date_from: "", date_to: "" });
            }}
          >
            Quitar filtro
          </Button>
        )}
      </form>

      <div className="mt-4">
        {loaded?.error && <Alert tone="error">{loaded.error}</Alert>}
        {loading && !data && <p className="text-sm text-white/60">Cargando…</p>}
        {data?.results.length === 0 && (
          <p className="text-sm text-white/60">No hay movimientos en este periodo.</p>
        )}
        {data && data.results.length > 0 && (
          <ul className={`divide-y divide-white/10 rounded-2xl border border-white/10 ${loading ? "opacity-60" : ""}`}>
            {data.results.map((movement) => (
              <MovementRow key={`${movement.operation_code}-${movement.direction}`} movement={movement} />
            ))}
          </ul>
        )}
      </div>

      {data && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            disabled={!data.previous || loading}
            onClick={() => setQuery({ ...query, page: query.page - 1 })}
          >
            ← Anterior
          </Button>
          <span className="text-xs text-white/50">
            Página {query.page} de {totalPages}
          </span>
          <Button
            variant="ghost"
            disabled={!data.next || loading}
            onClick={() => setQuery({ ...query, page: query.page + 1 })}
          >
            Siguiente →
          </Button>
        </div>
      )}
    </section>
  );
}

function MovementRow({ movement }: { movement: Movement }) {
  const isDebit = movement.direction === "debit";
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 p-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-white">{capitalize(movement.concept || movement.kind_label)}</p>
        <p className="text-xs text-white/50">
          {formatDateTime(movement.created_at)}
          {movement.concept && <> · {movement.kind_label}</>}
          {movement.counterpart && <> · {movement.counterpart}</>}
        </p>
        {movement.exchange_rate && (
          <p className="text-xs text-white/50">Tipo de cambio: {movement.exchange_rate}</p>
        )}
        <p className="font-mono text-xs break-all text-white/40">{movement.operation_code}</p>
      </div>
      <div className="ml-auto text-right">
        <p className={`text-sm font-semibold ${isDebit ? "text-white" : "text-cyan"}`}>
          {isDebit ? "−" : "+"}
          {formatMoney(movement.amount, movement.currency)}
        </p>
        {movement.balance_after && (
          <p className="text-xs text-white/50">Saldo: {formatMoney(movement.balance_after, movement.currency)}</p>
        )}
        {movement.has_receipt && <ReceiptButton code={movement.operation_code} />}
      </div>
    </li>
  );
}
