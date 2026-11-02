import { expect, test as setup } from "@playwright/test";
import { ARCHIVO_SESION, CLAVE, CLIENTE, codigoTotp } from "./datos";

// El login tiene un límite de 10 intentos por minuto: las pruebas reutilizan esta sesión.
setup("iniciar sesión con contraseña y código", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Correo o DNI").fill(CLIENTE);
  await page.getByRole("button", { name: "Prefiero usar contraseña + código" }).click();
  await page.getByLabel("Contraseña").fill(CLAVE);
  await page.getByLabel("Código de tu app de autenticación").fill(codigoTotp());
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();
  await page.context().storageState({ path: ARCHIVO_SESION });
});
