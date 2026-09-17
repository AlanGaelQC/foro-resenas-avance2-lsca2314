#!/usr/bin/env bash
# Funciones compartidas por todas las etapas del pipeline.
#
# El objetivo de este archivo es que ninguna etapa pueda "aprobar por accidente".
# Cada etapa termina registrando un estado explicito en reportes/estado_NN.json:
#
#   OK              el control corrio y no encontro nada por encima del umbral
#   HALLAZGO        el control corrio y encontro algo que supera el umbral
#   ERROR_OPERATIVO el control no pudo correr bien (falta el binario, timeout,
#                   salida invalida). NO es lo mismo que "sin vulnerabilidades"
#   NO_EJECUTADO    la etapa nunca escribio su estado
#
# El orquestador exige un archivo de estado por cada etapa esperada. Si falta,
# cuenta como NO_EJECUTADO y bloquea: la ausencia de evidencia nunca se lee
# como evidencia de ausencia.

set -uo pipefail

RAIZ_PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR_REPORTES="${DIR_REPORTES:-$RAIZ_PROYECTO/reportes}"
DIR_HERRAMIENTAS="$RAIZ_PROYECTO/.herramientas"
VENV_PIPELINE="$DIR_HERRAMIENTAS/venv"

mkdir -p "$DIR_REPORTES"

ESTADO_OK="OK"
ESTADO_HALLAZGO="HALLAZGO"
ESTADO_ERROR="ERROR_OPERATIVO"

TIEMPO_LIMITE_ETAPA="${TIEMPO_LIMITE_ETAPA:-600}"

# Ruta de las herramientas: primero las del proyecto, luego las del sistema.
export PATH="$DIR_HERRAMIENTAS/bin:$VENV_PIPELINE/bin:$PATH"

_escapar_json() {
  # Escapa comillas, barras y saltos de linea para incrustar texto en JSON.
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip())[1:-1])' <<< "${1:-}"
}

version_de() {
  # Devuelve la version de una herramienta sin romper la etapa si falla.
  local binario="$1"
  shift
  if ! command -v "$binario" > /dev/null 2>&1; then
    echo "no_disponible"
    return
  fi
  "$binario" "$@" 2>&1 | head -1 | tr -d '\r' || echo "desconocida"
}

registrar_estado() {
  # registrar_estado <etapa> <nombre> <herramienta> <estado> <codigo_salida>
  #                  <bloqueante si|no> <reporte> <umbral> <version> <detalle>
  local etapa="$1" nombre="$2" herramienta="$3" estado="$4" codigo="$5"
  local bloqueante="$6" reporte="$7" umbral="$8" version="$9" detalle="${10:-}"

  cat > "$DIR_REPORTES/estado_${etapa}.json" <<JSON
{
  "etapa": "$etapa",
  "nombre": "$(_escapar_json "$nombre")",
  "herramienta": "$(_escapar_json "$herramienta")",
  "version_herramienta": "$(_escapar_json "$version")",
  "estado": "$estado",
  "codigo_salida": $codigo,
  "bloqueante": "$bloqueante",
  "umbral": "$(_escapar_json "$umbral")",
  "reporte": "$(_escapar_json "$reporte")",
  "detalle": "$(_escapar_json "$detalle")",
  "momento": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
}

reporte_con_contenido() {
  # Un reporte vacio significa que la herramienta no llego a escribir nada:
  # eso es un error operativo, no un resultado limpio.
  local ruta="$1"
  [[ -s "$ruta" ]]
}

anunciar_etapa() {
  echo ""
  echo "------------------------------------------------------------"
  echo "[Etapa $1] $2  (herramienta: $3)"
  echo "  Umbral de bloqueo: $4"
  echo "------------------------------------------------------------"
}

resumir_resultado() {
  # resumir_resultado <estado> <codigo> <reporte>
  case "$1" in
    "$ESTADO_OK")       echo "  -> OK: sin hallazgos por encima del umbral (codigo $2)." ;;
    "$ESTADO_HALLAZGO") echo "  -> HALLAZGO: supera el umbral, este control bloquea (codigo $2)." ;;
    "$ESTADO_ERROR")    echo "  -> ERROR OPERATIVO: el control no pudo evaluarse (codigo $2)." ;;
    *)                  echo "  -> Estado desconocido: $1 (codigo $2)." ;;
  esac
  echo "     Reporte: $3"
}
