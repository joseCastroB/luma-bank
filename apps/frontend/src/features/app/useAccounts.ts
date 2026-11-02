import { useCallback, useEffect, useState } from "react";
import { getAccounts, type Account } from "@/lib/api";

export function useAccounts() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    getAccounts()
      .then((data) => setAccounts(data.accounts))
      .catch(() => setError("No se pudieron cargar tus cuentas."));
  }, []);

  useEffect(reload, [reload]);

  return { accounts, error, reload };
}
