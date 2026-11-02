/** Usabilidad según ISO/IEC 25010; cada bloque indica la subcaracterística que evalúa. */

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { cuentas } from "./datos";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const SIN_SESION = { cookies: [], origins: [] };

const PUBLICAS = [
  { nombre: "landing", ruta: "/", listo: "Tu dinero" },
  { nombre: "login", ruta: "/login", listo: "Banca por Internet" },
  { nombre: "registro", ruta: "/registro", listo: "Abrir cuenta" },
  { nombre: "página 404", ruta: "/no-existe", listo: "Esta página no existe" },
];

const PRIVADAS = [
  { nombre: "inicio", ruta: () => "/app", listo: /^Hola,/ },
  { nombre: "detalle de cuenta", ruta: () => `/app/cuentas/${cuentas().cuentaPen}`, listo: "Historial de movimientos" },
  { nombre: "transferir", ruta: () => "/app/transferir", listo: "Transferir" },
  { nombre: "convertir", ruta: () => "/app/convertir", listo: "Convertir moneda" },
  { nombre: "seguridad", ruta: () => "/app/seguridad", listo: "Tu rostro" },
];

async function revisarAccesibilidad(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  await test.info().attach("axe", {
    body: JSON.stringify(violations, null, 2),
    contentType: "application/json",
  });
  const resumen = violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} elemento(s)`);
  expect(resumen).toEqual([]);
}

async function revisarSinDesborde(page: Page) {
  const { ancho, visible } = await page.evaluate(() => ({
    ancho: document.documentElement.scrollWidth,
    visible: document.documentElement.clientWidth,
  }));
  expect(ancho).toBeLessThanOrEqual(visible);
}

test.describe("Accesibilidad: WCAG 2.2 AA con axe-core", () => {
  test.describe("páginas públicas", () => {
    test.use({ storageState: SIN_SESION });
    for (const { nombre, ruta, listo } of PUBLICAS) {
      test(`CP-U01 ${nombre} no tiene infracciones`, async ({ page }) => {
        await page.goto(ruta);
        await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
        await revisarAccesibilidad(page);
      });
    }
  });

  for (const { nombre, ruta, listo } of PRIVADAS) {
    test(`CP-U02 ${nombre} no tiene infracciones`, async ({ page }) => {
      await page.goto(ruta());
      await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
      await revisarAccesibilidad(page);
    });
  }

  test("CP-U03 el documento declara idioma y título", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "es");
    await expect(page).toHaveTitle(/Luma Bank/);
  });
});

test.describe("Operabilidad: se puede usar en pantallas pequeñas", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.describe("páginas públicas", () => {
    test.use({ storageState: SIN_SESION });
    for (const { nombre, ruta, listo } of PUBLICAS) {
      test(`CP-U04 ${nombre} no se desborda a 375 px`, async ({ page }) => {
        await page.goto(ruta);
        await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
        await revisarSinDesborde(page);
      });
    }
  });

  for (const { nombre, ruta, listo } of PRIVADAS) {
    test(`CP-U05 ${nombre} no se desborda a 375 px`, async ({ page }) => {
      await page.goto(ruta());
      await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
      await revisarSinDesborde(page);
    });
  }

  test("CP-U06 la navegación principal sigue visible en el móvil", async ({ page }) => {
    await page.goto("/app");
    const nav = page.getByRole("navigation", { name: "Principal" });
    for (const enlace of ["Inicio", "Transferir", "Convertir", "Seguridad"]) {
      await expect(nav.getByRole("link", { name: enlace })).toBeVisible();
    }
  });
});

test.describe("Operabilidad: se puede usar solo con el teclado", () => {
  test.describe("sin sesión", () => {
    test.use({ storageState: SIN_SESION });

    test("CP-U07 el login se completa con Tab y Enter", async ({ page }) => {
      await page.goto("/login");
      const campo = page.getByLabel("Correo o DNI");
      await campo.focus();
      await page.keyboard.type("cliente@lumabank.test");
      await page.keyboard.press("Tab");
      await expect(page.getByRole("button", { name: "Continuar" })).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(page.getByRole("button", { name: "Prefiero usar contraseña + código" })).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("heading", { name: "Acceso alterno" })).toBeVisible();
    });

    test("CP-U08 Enter en el formulario envía el DNI", async ({ page }) => {
      await page.goto("/registro");
      await page.getByLabel("Número de DNI").fill("70000001");
      await page.keyboard.press("Enter");
      await expect(page.getByText("¿Eres tú?")).toBeVisible();
    });
  });

  test("CP-U09 las pestañas de transferencia responden al teclado", async ({ page }) => {
    await page.goto("/app/transferir");
    const terceros = page.getByRole("tab", { name: "A terceros (CCI)" });
    await terceros.focus();
    await page.keyboard.press("Enter");
    await expect(terceros).toHaveAttribute("aria-selected", "true");
    await expect(page.getByLabel("CCI de destino")).toBeVisible();
  });
});

test.describe("Protección frente a errores del usuario", () => {
  test("CP-U10 volver desde la confirmación no mueve dinero y conserva lo escrito", async ({ page }) => {
    const { cuentaPen, cuentaPen2 } = cuentas();
    await page.goto(`/app/cuentas/${cuentaPen2}`);
    const saldo = await page.getByRole("definition").first().textContent();

    await page.goto("/app/transferir");
    await page.getByLabel("Cuenta de origen").selectOption(cuentaPen);
    await page.getByLabel("Cuenta de destino").selectOption(cuentaPen2);
    await page.getByLabel("Monto en soles").fill("77");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "Volver" }).click();
    await expect(page.getByLabel("Monto en soles")).toHaveValue("77");

    await page.goto(`/app/cuentas/${cuentaPen2}`);
    await expect(page.getByRole("definition").first()).toHaveText(saldo ?? "");
  });

  test("CP-U11 un monto mal escrito se explica junto al campo", async ({ page }) => {
    await page.goto("/app/transferir");
    const monto = page.getByLabel("Monto en soles");
    await monto.fill("12.345");
    await expect(page.getByText("Ingresa un monto válido, con hasta 2 decimales.")).toBeVisible();
    await expect(monto).toHaveAttribute("aria-invalid", "true");
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  test("CP-U12 el CCI ignora caracteres que no son dígitos", async ({ page }) => {
    await page.goto("/app/transferir");
    await page.getByRole("tab", { name: "A terceros (CCI)" }).click();
    const cci = page.getByLabel("CCI de destino");
    await cci.pressSequentially("12a-3");
    await expect(cci).toHaveValue("123");
  });

  test.describe("sin sesión", () => {
    test.use({ storageState: SIN_SESION });

    test("CP-U13 los errores se anuncian con role=alert", async ({ page }) => {
      await page.goto("/login");
      await page.getByLabel("Correo o DNI").fill("no-existe@lumabank.test");
      await page.getByRole("button", { name: "Prefiero usar contraseña + código" }).click();
      await page.getByLabel("Contraseña").fill("Una-Clave-Cualquiera");
      await page.getByLabel("Código de tu app de autenticación").fill("000000");
      await page.getByRole("button", { name: "Ingresar" }).click();
      await expect(page.getByRole("alert")).toContainText("No pudimos verificar tu identidad");
    });
  });
});

test.describe("Reconocibilidad y aprendizaje: el usuario sabe dónde está y qué hacer", () => {
  test("CP-U14 la navegación marca la sección actual", async ({ page }) => {
    await page.goto("/app/convertir");
    const nav = page.getByRole("navigation", { name: "Principal" });
    await expect(nav.getByRole("link", { name: "Convertir" })).toHaveAttribute("aria-current", "page");
    await expect(nav.getByRole("link", { name: "Inicio" })).not.toHaveAttribute("aria-current", "page");
  });

  test("CP-U15 cada campo del formulario tiene su etiqueta", async ({ page }) => {
    await page.goto("/app/transferir");
    await page.getByRole("tab", { name: "A terceros (CCI)" }).click();
    for (const etiqueta of ["Cuenta de origen", "CCI de destino", /Monto en/, "Concepto (opcional)"]) {
      await expect(page.getByLabel(etiqueta)).toBeVisible();
    }
  });

  test("CP-U16 las pistas explican el dato pedido antes de equivocarse", async ({ browser }) => {
    const contexto = await browser.newContext({ storageState: SIN_SESION });
    const page = await contexto.newPage();
    await page.goto("/registro");
    await expect(page.getByText("8 dígitos. Validaremos tu identidad con RENIEC.")).toBeVisible();
    await contexto.close();
  });

  test("CP-U17 sin cuentas suficientes se explica qué hacer", async ({ page }) => {
    await page.route("**/api/v1/banking/accounts/", async (route) => {
      const respuesta = await route.fetch();
      const cuerpo = (await respuesta.json()) as { accounts: unknown[] };
      await route.fulfill({ response: respuesta, json: { ...cuerpo, accounts: cuerpo.accounts.slice(0, 1) } });
    });
    await page.goto("/app/convertir");
    await expect(page.getByText(/Necesitas una cuenta en soles y otra en dólares/)).toBeVisible();
  });
});
