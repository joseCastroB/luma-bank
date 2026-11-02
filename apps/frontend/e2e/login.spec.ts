import { expect, test, type Page } from "@playwright/test";
import { CLAVE, CLIENTE, CLIENTE_BLOQUEADO, codigoTotp, codigoTotpIncorrecto } from "./datos";

async function intentarLogin(page: Page, correo: string, clave: string, codigo: string) {
  await page.goto("/login");
  await page.getByLabel("Correo o DNI").fill(correo);
  await page.getByRole("button", { name: "Prefiero usar contraseña + código" }).click();
  await page.getByLabel("Contraseña").fill(clave);
  await page.getByLabel("Código de tu app de autenticación").fill(codigo);
  await page.getByRole("button", { name: "Ingresar" }).click();
}

test.describe("HU03 y HU04 Inicio de sesión y segundo factor", () => {
  test("CP-F12 sin identificador no se puede continuar", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Prefiero usar contraseña + código" })).toBeDisabled();
  });

  test("CP-F13 una contraseña incorrecta no da acceso ni revela el motivo", async ({ page }) => {
    await intentarLogin(page, CLIENTE, "Clave-Incorrecta-1", codigoTotp());
    await expect(page.getByRole("alert")).toContainText("No pudimos verificar tu identidad");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("CP-F14 un código TOTP incorrecto no da acceso", async ({ page }) => {
    await intentarLogin(page, CLIENTE, CLAVE, codigoTotpIncorrecto());
    await expect(page.getByRole("alert")).toContainText("Código de verificación incorrecto");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("CP-F15 contraseña y código correctos dan acceso, y se puede cerrar sesión", async ({ page }) => {
    await intentarLogin(page, CLIENTE, CLAVE, codigoTotp());
    await expect(page).toHaveURL(/\/app$/);
    await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();

    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/app");
    await expect(page).toHaveURL(/\/login$/);
  });
});

test.describe("HU05 Bloqueo de cuenta", () => {
  test("CP-F16 una cuenta bloqueada no entra aunque los datos sean correctos", async ({ page }) => {
    await intentarLogin(page, CLIENTE_BLOQUEADO, CLAVE, codigoTotp());
    await expect(page.getByRole("alert")).toContainText("Cuenta bloqueada temporalmente");
    await expect(page).toHaveURL(/\/login$/);
  });
});
