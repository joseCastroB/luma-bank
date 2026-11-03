/** Datos de prueba creados por `manage.py preparar_e2e` (solo existe con DEBUG activo). */

import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";

export const ARCHIVO_SESION = "../../e2e-resultados/sesion.json";
export const ARCHIVO_CUENTAS = "../../e2e-resultados/cuentas.json";

export const CLIENTE = "e2e@lumabank.test";
export const CLIENTE_BLOQUEADO = "e2e.bloqueado@lumabank.test";
export const CLAVE = "E2e-Clave-Segura-2026";
const SECRETO_TOTP = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP";

/** CCI con formato válido que no pertenece a Luma Bank. */
export const CCI_OTRO_BANCO = "00200000000000000012";

export interface Cuentas {
  cuentaPen: string;
  cuentaPen2: string;
  cuentaUsd: string;
  cuentaDestino: string;
}

export function cuentas(): Cuentas {
  return JSON.parse(readFileSync(ARCHIVO_CUENTAS, "utf-8")) as Cuentas;
}

function base32(texto: string): Buffer {
  const alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const bits = [...texto].map((c) => alfabeto.indexOf(c).toString(2).padStart(5, "0")).join("");
  const bytes = bits.match(/.{8}/g) ?? [];
  return Buffer.from(bytes.map((b) => parseInt(b, 2)));
}

/** Código TOTP vigente (RFC 6238), el mismo que mostraría la app de autenticación. */
export function codigoTotp(secreto = SECRETO_TOTP): string {
  const contador = Buffer.alloc(8);
  contador.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 1000 / 30)));
  const hmac = createHmac("sha1", base32(secreto)).update(contador).digest();
  const inicio = hmac[hmac.length - 1] & 0xf;
  const valor = hmac.readUInt32BE(inicio) & 0x7fffffff;
  return String(valor % 1_000_000).padStart(6, "0");
}

/** Un código de 6 dígitos que no es el vigente ni el de los intervalos vecinos. */
export function codigoTotpIncorrecto(): string {
  return codigoTotp() === "000000" ? "111111" : "000000";
}
