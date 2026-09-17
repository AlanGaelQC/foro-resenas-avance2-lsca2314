#!/usr/bin/env bash
# Instala las herramientas del pipeline en .herramientas/ (dentro del proyecto,
# fuera de git). No toca el Python del sistema: en Amazon Linux 2023 instalar
# con pip --user puede dejar inservible el AWS CLI.
#
# Uso:  bash pipeline/preparar_herramientas.sh

set -uo pipefail

RAIZ_PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR_HERRAMIENTAS="$RAIZ_PROYECTO/.herramientas"
VENV="$DIR_HERRAMIENTAS/venv"
BIN="$DIR_HERRAMIENTAS/bin"

VERSION_GITLEAKS="${VERSION_GITLEAKS:-8.21.2}"

mkdir -p "$BIN"

echo "============================================================"
echo " Preparando herramientas del pipeline"
echo "============================================================"

# --- Python del pipeline ------------------------------------------------------
# checkov, semgrep y pip-audit necesitan Python >= 3.10; Amazon Linux 2023 trae
# 3.9 de fabrica. Por eso se busca python3.11 primero.
INTERPRETE=""
for candidato in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidato" > /dev/null 2>&1; then
    VERSION_MENOR="$("$candidato" -c 'import sys; print(sys.version_info[1])' 2>/dev/null || echo 0)"
    if [[ "$VERSION_MENOR" -ge 10 ]]; then
      INTERPRETE="$candidato"
      break
    fi
  fi
done

if [[ -z "$INTERPRETE" ]]; then
  echo "ERROR: no hay Python >= 3.10."
  echo "En Amazon Linux 2023:  sudo dnf install -y python3.11"
  exit 1
fi

echo "[1/3] Entorno virtual con $INTERPRETE ($("$INTERPRETE" --version 2>&1))"
if [[ ! -d "$VENV" ]]; then
  "$INTERPRETE" -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip

echo "[2/3] Herramientas de analisis (bandit, semgrep, pip-audit, checkov, cyclonedx, httpx)"
"$VENV/bin/pip" install --quiet \
  bandit==1.9.4 \
  semgrep==1.177.0 \
  pip-audit==2.10.1 \
  checkov==3.3.17 \
  cyclonedx-bom==4.6.1 \
  httpx==0.28.1 || {
    echo "ERROR: fallo la instalacion de las herramientas Python."
    exit 1
  }

# --- gitleaks (binario) -------------------------------------------------------
echo "[3/3] gitleaks $VERSION_GITLEAKS"
if [[ ! -x "$BIN/gitleaks" ]]; then
  ARQUITECTURA="x64"
  [[ "$(uname -m)" == "aarch64" ]] && ARQUITECTURA="arm64"
  ARCHIVO_GITLEAKS="gitleaks_${VERSION_GITLEAKS}_linux_${ARQUITECTURA}.tar.gz"
  URL_BASE_GITLEAKS="https://github.com/gitleaks/gitleaks/releases/download/v${VERSION_GITLEAKS}"
  TEMP_GITLEAKS="$(mktemp -d)"
  if curl -fsSL "$URL_BASE_GITLEAKS/$ARCHIVO_GITLEAKS" -o "$TEMP_GITLEAKS/$ARCHIVO_GITLEAKS" \
      && curl -fsSL "$URL_BASE_GITLEAKS/gitleaks_${VERSION_GITLEAKS}_checksums.txt" -o "$TEMP_GITLEAKS/checksums.txt" \
      && HASH_GITLEAKS="$(awk -v archivo="$ARCHIVO_GITLEAKS" '$2 == archivo {print $1}' "$TEMP_GITLEAKS/checksums.txt")" \
      && [[ -n "$HASH_GITLEAKS" ]] \
      && [[ "$HASH_GITLEAKS" == "$(sha256sum "$TEMP_GITLEAKS/$ARCHIVO_GITLEAKS" | awk '{print $1}')" ]] \
      && tar -xzf "$TEMP_GITLEAKS/$ARCHIVO_GITLEAKS" -C "$BIN" gitleaks; then
    chmod +x "$BIN/gitleaks"
  else
    echo "  AVISO: no se pudo descargar y verificar gitleaks."
    echo "  La etapa 01 va a reportar ERROR_OPERATIVO (y bloquear) hasta instalarlo."
  fi
  rm -rf "$TEMP_GITLEAKS"
fi

# --- trivy (binario) ----------------------------------------------------------
# Trivy no se instala con pip. En Amazon Linux 2023 la via documentada por Aqua
# es su instalador o su repositorio RPM. Si ninguna funciona, la etapa 06
# reportara ERROR_OPERATIVO y el pipeline bloqueara: es el comportamiento
# correcto, no se aprueba un control que no corrio.
if ! command -v trivy > /dev/null 2>&1 && [[ ! -x "$BIN/trivy" ]]; then
  echo "[extra] trivy"
  VERSION_TRIVY="${VERSION_TRIVY:-$(curl -fsSL https://api.github.com/repos/aquasecurity/trivy/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))' 2>/dev/null)}"
  ARQUITECTURA_TRIVY="64bit"
  [[ "$(uname -m)" == "aarch64" ]] && ARQUITECTURA_TRIVY="ARM64"
  ARCHIVO_TRIVY="trivy_${VERSION_TRIVY}_Linux-${ARQUITECTURA_TRIVY}.tar.gz"
  URL_BASE_TRIVY="https://github.com/aquasecurity/trivy/releases/download/v${VERSION_TRIVY}"
  TEMP_TRIVY="$(mktemp -d)"
  if [[ "$VERSION_TRIVY" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
      && curl -fsSL "$URL_BASE_TRIVY/$ARCHIVO_TRIVY" -o "$TEMP_TRIVY/$ARCHIVO_TRIVY" \
      && curl -fsSL "$URL_BASE_TRIVY/trivy_${VERSION_TRIVY}_checksums.txt" -o "$TEMP_TRIVY/checksums.txt" \
      && HASH_TRIVY="$(awk -v archivo="$ARCHIVO_TRIVY" '$2 == archivo {print $1}' "$TEMP_TRIVY/checksums.txt")" \
      && [[ -n "$HASH_TRIVY" ]] \
      && [[ "$HASH_TRIVY" == "$(sha256sum "$TEMP_TRIVY/$ARCHIVO_TRIVY" | awk '{print $1}')" ]] \
      && tar -xzf "$TEMP_TRIVY/$ARCHIVO_TRIVY" -C "$BIN" trivy; then
    chmod +x "$BIN/trivy"
    echo "  trivy $VERSION_TRIVY instalado y verificado en $BIN"
  else
    echo "  AVISO: no se pudo descargar y verificar trivy."
    echo "  La etapa 06 reportara ERROR_OPERATIVO hasta resolverlo."
  fi
  rm -rf "$TEMP_TRIVY"
fi

echo ""
echo "============================================================"
echo " Versiones instaladas"
echo "============================================================"
"$VENV/bin/bandit" --version 2>&1 | head -1
"$VENV/bin/semgrep" --version 2>&1 | head -1 | sed 's/^/semgrep /'
"$VENV/bin/pip-audit" --version 2>&1 | head -1
"$VENV/bin/checkov" --version 2>&1 | head -1 | sed 's/^/checkov /'
"$VENV/bin/cyclonedx-py" --version 2>&1 | head -1
[[ -x "$BIN/gitleaks" ]] && "$BIN/gitleaks" version 2>&1 | head -1 | sed 's/^/gitleaks /'
command -v trivy > /dev/null 2>&1 && trivy --version 2>&1 | head -1
[[ -x "$BIN/trivy" ]] && "$BIN/trivy" --version 2>&1 | head -1

echo ""
echo "Listo. Ahora puedes correr:  bash pipeline/orquestador.sh"
