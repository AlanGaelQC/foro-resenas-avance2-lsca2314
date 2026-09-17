#!/usr/bin/env bash
# Fija la imagen base por digest REAL, tomado de tu propio docker pull.
#
# Por que existe este script: "python:3.11-slim" es una etiqueta movil -- manana
# puede apuntar a otra imagen. El requisito del Avance 2 pide version fija. Un
# digest escrito a mano seria un dato inventado; este script obtiene el digest
# verdadero de la imagen que tu descargaste y reescribe la linea FROM.
#
# Uso:  bash pipeline/fijar_imagen_base.sh
# Resultado:  FROM python:3.11-slim@sha256:<digest real>

set -uo pipefail

RAIZ_PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ETIQUETA="${ETIQUETA_BASE:-python:3.11-slim}"

cd "$RAIZ_PROYECTO"

if ! docker info > /dev/null 2>&1; then
  echo "ERROR: el demonio de Docker no responde. Arranca Docker y vuelve a intentar."
  exit 1
fi

echo "Descargando $ETIQUETA para leer su digest..."
docker pull "$ETIQUETA" || exit 1

DIGEST="$(docker inspect --format='{{index .RepoDigests 0}}' "$ETIQUETA" 2>/dev/null | cut -d'@' -f2)"

if [[ -z "$DIGEST" ]]; then
  echo "ERROR: no se pudo leer el digest de $ETIQUETA."
  exit 1
fi

echo "Digest real: $DIGEST"

for archivo in Dockerfile Dockerfile.moderador; do
  # Reemplaza la linea FROM completa, tenga o no digest previo.
  sed -i -E "s|^FROM ${ETIQUETA%%:*}:[^@[:space:]]+(@sha256:[a-f0-9]+)?|FROM ${ETIQUETA}@${DIGEST}|" "$archivo"
  echo "  $archivo -> $(grep '^FROM' "$archivo")"
done

echo ""
echo "Listo. Reconstruye con: docker compose build"
echo "Confirma el pin en el repositorio con: git diff Dockerfile Dockerfile.moderador"
