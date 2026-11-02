import { expect, test } from "@playwright/test";

test.describe("HU01 Landing y navegación pública", () => {
  test("CP-F01 la landing presenta la propuesta de valor", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Tu dinero");
    await expect(page.getByRole("link", { name: "Abrir cuenta" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Banca por Internet" }).first()).toBeVisible();
  });

  test("CP-F02 'Abrir cuenta' lleva al registro", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Abrir cuenta" }).first().click();
    await expect(page).toHaveURL(/\/registro$/);
    await expect(page.getByRole("heading", { name: "Abrir cuenta" })).toBeVisible();
  });

  test("CP-F03 'Banca por Internet' lleva al login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Banca por Internet" }).first().click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Banca por Internet" })).toBeVisible();
  });

  test("CP-F04 una ruta inexistente muestra la página 404", async ({ page }) => {
    await page.goto("/no-existe");
    await expect(page.getByText("Esta página no existe")).toBeVisible();
    await page.getByRole("link", { name: "Ir al inicio" }).click();
    await expect(page).toHaveURL(/\/$/);
  });

  for (const ruta of ["/app", "/app/transferir", "/app/convertir", "/app/seguridad"]) {
    test(`CP-F05 sin sesión, ${ruta} redirige al login`, async ({ page }) => {
      await page.goto(ruta);
      await expect(page).toHaveURL(/\/login$/);
    });
  }
});
