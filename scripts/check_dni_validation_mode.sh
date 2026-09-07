#!/usr/bin/env bash
#
# GUARDIA DE DESPLIEGUE - Luma Bank
#
# Falla (exit != 0) si "DNI_VALIDATION_MODE=mock" aparece en algun archivo
# versionado que aplique a un entorno de PRODUCCION.
#
# El modo "mock" no llama a LionAPI/RENIEC y devuelve datos simulados: solo
# puede usarse en desarrollo local y en tests automatizados. Este check es
# defensa en profundidad, ademas de config/settings/prod.py (que aborta el
# arranque si detecta 'mock').
#
# Uso:  bash scripts/check_dni_validation_mode.sh
# CI:   job obligatorio en .github/workflows/ci.yml
#
set -euo pipefail

# Rutas donde 'mock' SI esta permitido (desarrollo / tests / documentacion).
ALLOWLIST_REGEX='^(\.env\.example|docker-compose\.override\.yml|apps/backend/config/settings/dev\.py|apps/backend/pyproject\.toml|apps/backend/tests/.*|apps/backend/apps/.*/tests/.*|scripts/check_dni_validation_mode\.sh|README\.md|VERSIONS\.md|\.github/workflows/.*)$'

# DNI_VALIDATION_MODE seguido de = o : y luego (con comillas/espacios opcionales) mock
PATTERN='DNI_VALIDATION_MODE[[:space:]]*[:=][[:space:]]*["'"'"' ]*mock'

fail=0
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  if [[ "$file" =~ $ALLOWLIST_REGEX ]]; then
    continue
  fi
  if grep -nEi "$PATTERN" "$file" >/dev/null 2>&1; then
    echo "::error file=${file}::DNI_VALIDATION_MODE=mock en un archivo que aplica a produccion"
    grep -nEi "$PATTERN" "$file" | sed "s|^|  ${file}:|"
    fail=1
  fi
done < <(git ls-files)

if [[ "$fail" -ne 0 ]]; then
  echo ""
  echo "DESPLIEGUE BLOQUEADO: 'DNI_VALIDATION_MODE=mock' solo se permite en"
  echo "desarrollo local y tests. Corrige los archivos listados arriba."
  exit 1
fi

echo "OK: sin 'DNI_VALIDATION_MODE=mock' fuera de desarrollo/tests."
