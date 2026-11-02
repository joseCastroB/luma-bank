import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { ARCHIVO_CUENTAS } from "./datos";

const COMANDO =
  process.env.E2E_SEED_COMMAND ?? "docker compose exec -T backend python manage.py preparar_e2e";

/** Reinicia los clientes de prueba antes de cada corrida; los números de cuenta cambian. */
export default function globalSetup() {
  const salida = execSync(COMANDO, { encoding: "utf-8" });
  const json = salida.trim().split("\n").at(-1) ?? "";
  mkdirSync(dirname(ARCHIVO_CUENTAS), { recursive: true });
  writeFileSync(ARCHIVO_CUENTAS, json);
}
