const CURRENCY_LABEL: Record<string, string> = { PEN: "S/", USD: "US$" };

export function currencySymbol(currency: string): string {
  return CURRENCY_LABEL[currency] ?? currency;
}

export function currencyName(currency: string): string {
  return currency === "USD" ? "dólares" : "soles";
}

export function formatMoney(amount: string | number, currency: string): string {
  const value = Number(amount).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${currencySymbol(currency)} ${value}`;
}

/** Fecha sin hora (AAAA-MM-DD): se lee tal cual para que la zona horaria no la mueva de día. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", { dateStyle: "short", timeStyle: "short" });
}

export function maskAccount(number: string): string {
  return `****${number.slice(-4)}`;
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function isValidAmount(value: string): boolean {
  return /^\d+(\.\d{1,2})?$/.test(value) && Number(value) > 0;
}
