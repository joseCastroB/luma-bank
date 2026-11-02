import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { CCI_OTRO_BANCO, CLIENTE, codigoTotp, cuentas } from "./datos";

const EXITO = "Operación realizada con éxito.";

test.describe("HU08 Saldo y TREA", () => {
  test("CP-F17 el inicio muestra las cuentas con saldo y TREA", async ({ page }) => {
    await page.goto("/app");
    await expect(page.getByText(CLIENTE)).toBeVisible();
    const tarjeta = page.getByRole("link").filter({ hasText: cuentas().cuentaUsd.slice(-4) });
    await expect(tarjeta).toContainText("Ahorros en dólares");
    await expect(tarjeta).toContainText("Saldo disponible");
    await expect(tarjeta).toContainText("Saldo contable");
    await expect(tarjeta).toContainText(/US\$ 500\.00/);
    await expect(tarjeta).toContainText(/TREA \d/);
  });

  test("CP-F18 el detalle muestra el número completo y la TREA vigente", async ({ page }) => {
    const { cuentaUsd } = cuentas();
    await page.goto(`/app/cuentas/${cuentaUsd}`);
    await expect(page.getByText(cuentaUsd)).toBeVisible();
    await expect(page.getByText("TREA vigente")).toBeVisible();
    await expect(page.getByText(/Intereses por capitalizar/)).toBeVisible();
  });

  test("CP-F19 una cuenta ajena no se puede consultar", async ({ page }) => {
    await page.goto(`/app/cuentas/${cuentas().cuentaDestino}`);
    await expect(page.getByRole("alert")).toContainText("No encontramos esa cuenta.");
  });
});

test.describe("HU07 Abrir cuenta de ahorro", () => {
  test("CP-F20 pide confirmar y permite cancelar", async ({ page }) => {
    await page.goto("/app");
    await expect(page.getByRole("link", { name: /Ahorros en/ }).first()).toBeVisible();
    const cuentasAntes = await page.getByRole("link", { name: /Ahorros en/ }).count();
    await page.getByRole("button", { name: /En dólares/ }).click();
    await expect(page.getByText(/Vas a abrir una cuenta de ahorro en dólares/)).toBeVisible();
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByRole("link", { name: /Ahorros en/ })).toHaveCount(cuentasAntes);
  });

  test("CP-F21 abre la cuenta con saldo cero e informa la TREA", async ({ page }) => {
    await page.goto("/app");
    await expect(page.getByRole("link", { name: /Ahorros en/ }).first()).toBeVisible();
    const cuentasAntes = await page.getByRole("link", { name: /Ahorros en/ }).count();
    await page.getByRole("button", { name: /En soles/ }).click();
    await page.getByRole("button", { name: "Confirmar apertura" }).click();
    await expect(page.getByText(/Abrimos tu cuenta \*{4}\d{4} con saldo inicial de S\/ 0\.00/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Ahorros en/ })).toHaveCount(cuentasAntes + 1);
  });
});

test.describe("HU09 Historial de movimientos", () => {
  test("CP-F22 lista los movimientos y pagina de 20 en 20", async ({ page }) => {
    await page.goto(`/app/cuentas/${cuentas().cuentaPen}`);
    await expect(page.getByRole("heading", { name: "Historial de movimientos" })).toBeVisible();
    await expect(page.getByRole("listitem")).toHaveCount(20);
    await expect(page.getByText(/Página 1 de \d/)).toBeVisible();
    await expect(page.getByRole("button", { name: "← Anterior" })).toBeDisabled();

    await page.getByRole("button", { name: "Siguiente →" }).click();
    await expect(page.getByText(/Página 2 de \d/)).toBeVisible();
    await expect(page.getByRole("button", { name: "← Anterior" })).toBeEnabled();
  });

  test("CP-F23 filtra por fechas y permite quitar el filtro", async ({ page }) => {
    await page.goto(`/app/cuentas/${cuentas().cuentaPen}`);
    await expect(page.getByRole("listitem").first()).toBeVisible();

    await page.getByLabel("Desde").fill("2020-01-01");
    await page.getByLabel("Hasta").fill("2020-01-31");
    await page.getByRole("button", { name: "Filtrar" }).click();
    await expect(page.getByText("No hay movimientos en este periodo.")).toBeVisible();

    await page.getByRole("button", { name: "Quitar filtro" }).click();
    await expect(page.getByRole("listitem").first()).toBeVisible();
  });
});

test.describe("HU10 Transferencia entre cuentas propias", () => {
  test("CP-F24 transfiere, muestra el resultado y actualiza el historial", async ({ page }) => {
    const { cuentaPen, cuentaPen2 } = cuentas();
    await page.goto("/app/transferir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentaPen);
    await page.getByLabel("Cuenta de destino").selectOption(cuentaPen2);
    await page.getByLabel("Monto en soles").fill("150.50");
    await page.getByLabel("Concepto (opcional)").fill("Ahorro E2E");
    await page.getByRole("button", { name: "Continuar" }).click();

    await expect(page.getByRole("heading", { name: "Confirma la operación" })).toBeVisible();
    await expect(page.getByText("S/ 150.50")).toBeVisible();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();

    await expect(page.getByText(EXITO)).toBeVisible();
    await expect(page.getByText("Código de operación")).toBeVisible();

    await page.goto(`/app/cuentas/${cuentaPen2}`);
    await expect(page.getByRole("listitem").filter({ hasText: "Ahorro E2E" })).toContainText("+S/ 150.50");
  });

  test("CP-F25 no deja transferir más que el saldo disponible", async ({ page }) => {
    await page.goto("/app/transferir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentas().cuentaPen);
    await page.getByLabel("Monto en soles").fill("99999999");
    await expect(page.getByText("Saldo insuficiente en la cuenta de origen.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  test("CP-F26 descarga el comprobante en PDF", async ({ page }) => {
    const { cuentaPen, cuentaPen2 } = cuentas();
    await page.goto("/app/transferir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentaPen);
    await page.getByLabel("Cuenta de destino").selectOption(cuentaPen2);
    await page.getByLabel("Monto en soles").fill("10");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByText(EXITO)).toBeVisible();

    const descarga = page.waitForEvent("download");
    await page.getByRole("button", { name: "Descargar comprobante" }).click();
    const archivo = await descarga;
    expect(archivo.suggestedFilename()).toMatch(/\.pdf$/);
    expect(readFileSync(await archivo.path()).subarray(0, 4).toString()).toBe("%PDF");
  });
});

test.describe("HU13 Transferencia a terceros por CCI", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/app/transferir");
    await page.getByRole("tab", { name: "A terceros (CCI)" }).click();
    await page.getByLabel("Cuenta de origen").selectOption(cuentas().cuentaPen);
  });

  test("CP-F27 valida el largo del CCI", async ({ page }) => {
    await page.getByLabel("CCI de destino").fill("123");
    await expect(page.getByText("El CCI debe tener 20 dígitos (llevas 3).")).toBeVisible();
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  test("CP-F28 transfiere a otro cliente de Luma Bank", async ({ page }) => {
    await page.getByLabel("CCI de destino").fill(cuentas().cuentaDestino);
    await expect(page.getByLabel("Titular de la cuenta")).toBeHidden();
    await page.getByLabel(/Monto en PEN/).fill("25");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Confirmar transferencia" }).click();
    await expect(page.getByText(EXITO)).toBeVisible();
  });

  test("CP-F29 a otro banco exige titular y banco", async ({ page }) => {
    await page.getByLabel("CCI de destino").fill(CCI_OTRO_BANCO);
    await page.getByLabel(/Monto en PEN/).fill("30");
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();

    await page.getByLabel("Titular de la cuenta").fill("Persona de Prueba");
    await page.getByLabel("Banco de destino").fill("Banco de Prueba");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Confirmar transferencia" }).click();
    await expect(page.getByText(EXITO)).toBeVisible();
  });

  test("CP-F30 un CCI de Luma Bank inexistente se rechaza", async ({ page }) => {
    await page.getByLabel("CCI de destino").fill("01100210000000000000");
    await page.getByLabel(/Monto en PEN/).fill("10");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Confirmar transferencia" }).click();
    await expect(page.getByRole("alert")).toContainText("no corresponde a ninguna cuenta");
  });

  test("CP-F31 sobre el umbral pide el código TOTP y lo verifica", async ({ page }) => {
    await page.getByLabel("CCI de destino").fill(cuentas().cuentaDestino);
    await page.getByLabel(/Monto en PEN/).fill("1500");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Confirmar transferencia" }).click();

    const codigo = page.getByLabel("Código de tu app de autenticación");
    await expect(codigo).toBeVisible();
    await expect(page.getByRole("button", { name: "Confirmar transferencia" })).toBeDisabled();

    await codigo.fill(codigoTotp());
    await page.getByRole("button", { name: "Confirmar transferencia" }).click();
    await expect(page.getByText(EXITO)).toBeVisible();
  });
});

test.describe("HU14 Conversión de moneda", () => {
  test("CP-F32 cotiza, confirma y aplica el tipo de cambio", async ({ page }) => {
    const { cuentaPen, cuentaUsd } = cuentas();
    await page.goto("/app/convertir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentaPen);
    await page.getByLabel("Cuenta de destino").selectOption(cuentaUsd);
    await page.getByLabel("Monto en soles").fill("100");
    await expect(page.getByText(/Recibirás/)).toBeVisible();
    await page.getByRole("button", { name: "Continuar" }).click();

    await expect(page.getByText("Tipo de cambio", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(page.getByText(EXITO)).toBeVisible();
    await expect(page.getByText("Tipo de cambio aplicado")).toBeVisible();
    await expect(page.getByText("Monto abonado")).toBeVisible();
  });

  test("CP-F33 solo ofrece destinos en la otra moneda", async ({ page }) => {
    const { cuentaPen, cuentaPen2, cuentaUsd } = cuentas();
    await page.goto("/app/convertir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentaPen);
    const destino = page.getByLabel("Cuenta de destino");
    await expect(destino.locator(`option[value="${cuentaUsd}"]`)).toHaveCount(1);
    await expect(destino.locator(`option[value="${cuentaPen2}"]`)).toHaveCount(0);
  });
});

test.describe("HU06 Seguridad de la cuenta", () => {
  test("CP-F34 ofrece actualizar el rostro y permite cancelar", async ({ page }) => {
    await page.goto("/app/seguridad");
    await expect(page.getByRole("heading", { name: "Tu rostro" })).toBeVisible();
    await page.getByRole("button", { name: "Actualizar mi rostro" }).click();
    await expect(page.getByText("Parpadea y gira la cabeza")).toBeVisible();
    await page.getByRole("button", { name: "Cancelar" }).click();
    await expect(page.getByRole("button", { name: "Actualizar mi rostro" })).toBeVisible();
  });
});

test.describe("HU11 Cierre de sesión por inactividad", () => {
  // La sesión guardada ya lleva tiempo creada: la inactividad se cuenta desde que abre la página.
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("luma.lastActivity", String(Date.now())));
  });

  test("CP-F35 avisa antes de cerrar y 'Seguir conectado' mantiene la sesión", async ({ page }) => {
    await page.clock.install();
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();

    await page.clock.fastForward("04:40");
    const aviso = page.getByRole("alertdialog", { name: "¿Sigues ahí?" });
    await expect(aviso).toBeVisible();

    await page.getByRole("button", { name: "Seguir conectado" }).click();
    await expect(aviso).toBeHidden();
    await expect(page).toHaveURL(/\/app$/);
  });

  test("CP-F36 a los 5 minutos sin actividad cierra la sesión e informa el motivo", async ({ page }) => {
    await page.clock.install();
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();

    await page.clock.fastForward("05:01");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText("Cerramos tu sesión por inactividad.", { exact: false })).toBeVisible();
  });
});
