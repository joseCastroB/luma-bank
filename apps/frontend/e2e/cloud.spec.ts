/**
 * Validación del sistema desplegado. Solo lee: no valida DNI (consume créditos de LionAPI),
 * no registra clientes, no intenta ingresar sin cuenta y no mueve dinero.
 * Los casos con sesión piden una cuenta de prueba en variables de entorno; sin ellas, se omiten.
 */

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { API_CLOUD, FRONT_CLOUD } from "../playwright.cloud.config";
import { codigoTotp } from "./datos";

const ORIGEN_AJENO = "https://sitio-malicioso.example";
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const PUBLICAS = [
  { nombre: "landing", ruta: "/", listo: "Tu dinero" },
  { nombre: "login", ruta: "/login", listo: "Banca por Internet" },
  { nombre: "registro", ruta: "/registro", listo: "Abrir cuenta" },
  { nombre: "página 404", ruta: "/no-existe", listo: "Esta página no existe" },
];

test.describe("Disponibilidad y transporte seguro", () => {
  test("CP-C01 el sitio responde y HTTP redirige a HTTPS", async ({ request }) => {
    expect((await request.get(FRONT_CLOUD)).status()).toBe(200);
    if (FRONT_CLOUD.startsWith("https://")) {
      const http = await request.get(FRONT_CLOUD.replace("https://", "http://"), { maxRedirects: 0 });
      expect(http.status()).toBe(301);
      expect(http.headers()["location"]).toMatch(/^https:\/\//);
    }
  });

  test("CP-C02 el estado del servicio informa base y caché correctas", async ({ request }) => {
    const respuesta = await request.get(`${API_CLOUD}/api/health/`);
    expect(respuesta.status()).toBe(200);
    expect(await respuesta.json()).toMatchObject({
      status: "ok",
      debug: false,
      dni_validation_mode: "production",
      checks: { database: "ok", cache: "ok" },
    });
  });

  test("CP-C03 la API envía cabeceras de seguridad", async ({ request }) => {
    const cabeceras = (await request.get(`${API_CLOUD}/api/health/`)).headers();
    expect(cabeceras["strict-transport-security"]).toContain("max-age=");
    expect(cabeceras["x-content-type-options"]).toBe("nosniff");
    expect(cabeceras["x-frame-options"]).toBe("DENY");
  });

  test("CP-C04 el frontend envía HSTS y nosniff", async ({ request }) => {
    const cabeceras = (await request.get(FRONT_CLOUD)).headers();
    expect(cabeceras["strict-transport-security"]).toContain("max-age=");
    expect(cabeceras["x-content-type-options"]).toBe("nosniff");
  });
});

test.describe("Control de acceso a la API", () => {
  for (const ruta of ["/api/v1/accounts/me/", "/api/v1/banking/accounts/", "/api/v1/banking/exchange/quote/"]) {
    test(`CP-C05 ${ruta} rechaza una petición sin sesión`, async ({ request }) => {
      expect((await request.get(`${API_CLOUD}${ruta}`)).status()).toBe(401);
    });
  }

  test("CP-C06 la API rechaza un token inválido", async ({ request }) => {
    const respuesta = await request.get(`${API_CLOUD}/api/v1/banking/accounts/`, {
      headers: { Authorization: "Bearer abc.def.ghi" },
    });
    expect(respuesta.status()).toBe(401);
  });

  async function origenPermitido(request: import("@playwright/test").APIRequestContext, origen: string) {
    const respuesta = await request.fetch(`${API_CLOUD}/api/v1/accounts/login/password/`, {
      method: "OPTIONS",
      headers: {
        Origin: origen,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
      },
    });
    return respuesta.headers()["access-control-allow-origin"];
  }

  test("CP-C07 CORS autoriza al frontend", async ({ request }) => {
    expect(await origenPermitido(request, FRONT_CLOUD)).toBe(FRONT_CLOUD);
  });

  test("CP-C08 CORS no autoriza a un sitio ajeno", async ({ request }) => {
    expect(await origenPermitido(request, ORIGEN_AJENO)).toBeUndefined();
  });
});

test.describe("Frontend desplegado", () => {
  test("CP-C09 el navegador se comunica con la API", async ({ page }) => {
    await page.goto("/estado");
    const estado = page.getByRole("definition").first();
    await expect(estado).toHaveText("ok");
    await expect(page.getByText("production")).toBeVisible();
  });

  test("CP-C10 la landing lleva al registro y al login", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Abrir cuenta" }).first().click();
    await expect(page).toHaveURL(/\/registro$/);
    await page.goto("/");
    await page.getByRole("link", { name: "Banca por Internet" }).first().click();
    await expect(page).toHaveURL(/\/login$/);
  });

  for (const ruta of ["/app", "/app/transferir", "/app/convertir", "/app/seguridad"]) {
    test(`CP-C11 sin sesión, ${ruta} redirige al login`, async ({ page }) => {
      await page.goto(ruta);
      await expect(page).toHaveURL(/\/login$/);
    });
  }

  test("CP-C12 un DNI mal escrito se rechaza sin consultar la API", async ({ page }) => {
    const consultas: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("validar-dni")) consultas.push(r.url());
    });
    await page.goto("/registro");
    await page.getByLabel("Número de DNI").fill("1234");
    await expect(page.getByText("Deben ser exactamente 8 dígitos.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
    expect(consultas).toEqual([]);
  });

  test("CP-C13 el login alterno se abre solo con el teclado", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Correo o DNI").focus();
    await page.keyboard.type("cliente@lumabank.test");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Acceso alterno" })).toBeVisible();
  });
});

test.describe("Usabilidad en Cloud", () => {
  for (const { nombre, ruta, listo } of PUBLICAS) {
    test(`CP-C14 ${nombre} no tiene infracciones de accesibilidad`, async ({ page }) => {
      await page.goto(ruta);
      await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
      const { violations } = await new AxeBuilder({ page }).withTags(WCAG).analyze();
      await test.info().attach("axe", {
        body: JSON.stringify(violations, null, 2),
        contentType: "application/json",
      });
      expect(violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
    });
  }

  test.describe("pantalla pequeña", () => {
    test.use({ viewport: { width: 375, height: 812 } });
    for (const { nombre, ruta, listo } of PUBLICAS) {
      test(`CP-C15 ${nombre} no se desborda a 375 px`, async ({ page }) => {
        await page.goto(ruta);
        await expect(page.getByRole("heading", { name: listo }).first()).toBeVisible();
        const { ancho, visible } = await page.evaluate(() => ({
          ancho: document.documentElement.scrollWidth,
          visible: document.documentElement.clientWidth,
        }));
        expect(ancho).toBeLessThanOrEqual(visible);
      });
    }
  });
});

const USUARIO = process.env.E2E_CLOUD_USUARIO;
const CLAVE = process.env.E2E_CLOUD_CLAVE;
const TOTP = process.env.E2E_CLOUD_TOTP;

test.describe("Con cuenta de prueba (solo lectura)", () => {
  test.describe.configure({ mode: "serial" });
  test.skip(!USUARIO || !CLAVE || !TOTP, "Define E2E_CLOUD_USUARIO, E2E_CLOUD_CLAVE y E2E_CLOUD_TOTP");

  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  test("CP-C20 ingresa con contraseña y código", async () => {
    await page.goto("/login");
    await page.getByLabel("Correo o DNI").fill(USUARIO ?? "");
    await page.getByRole("button", { name: "Prefiero usar contraseña + código" }).click();
    await page.getByLabel("Contraseña").fill(CLAVE ?? "");
    await page.getByLabel("Código de tu app de autenticación").fill(codigoTotp(TOTP));
    await page.getByRole("button", { name: "Ingresar" }).click();
    await expect(page.getByRole("heading", { name: /^Hola,/ })).toBeVisible();
    await test.info().attach("inicio", { body: await page.screenshot(), contentType: "image/png" });
  });

  test("CP-C21 muestra las cuentas, las tasas y el historial", async () => {
    await expect(page.getByRole("heading", { name: "Abrir una cuenta de ahorro" })).toBeVisible();
    const cuenta = page.getByRole("link", { name: /Ahorros en/ }).first();
    await expect(cuenta).toBeVisible();
    await cuenta.click();
    await expect(page.getByRole("heading", { name: "Historial de movimientos" })).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("CP-C22 abre las pantallas de operación sin ejecutar ninguna", async () => {
    await page.getByRole("link", { name: "Transferir" }).click();
    await expect(page.getByRole("heading", { name: "Transferir" })).toBeVisible();
    await page.getByRole("link", { name: "Convertir" }).click();
    await expect(page.getByRole("heading", { name: "Convertir moneda" })).toBeVisible();
    await page.getByRole("link", { name: "Seguridad" }).click();
    await expect(page.getByRole("heading", { name: "Tu rostro" })).toBeVisible();
  });

  test("CP-C23 cierra la sesión", async () => {
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/app");
    await expect(page).toHaveURL(/\/login$/);
  });
});
