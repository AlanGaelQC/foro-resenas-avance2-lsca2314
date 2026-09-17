#!/usr/bin/env bash
# Etapa 02 - Dependencias vulnerables (SCA) de los dos servicios.
#
# Riesgo que cubre: la API y el moderador corren sobre codigo de terceros
# (FastAPI, SQLAlchemy, boto3, Jinja2...). Una vulnerabilidad en cualquiera de
# esas piezas es una vulnerabilidad de mi foro, y yo no la escribi ni la voy a
# ver leyendo mi propio codigo. pip-audit consulta la base de avisos de PyPI y
# la Open Source Vulnerability database.
#
# Alcance: se auditan los dos archivos de requisitos fijados, que es justo lo
# que se instala dentro de las imagenes. Auditar el entorno del pipeline en vez
# de los requirements medirian otra cosa.
#
# Umbral: CERO vulnerabilidades conocidas en dependencias directas o
# transitivas de los requirements. Es un umbral duro y se puede sostener porque
# las versiones estan fijadas: si aparece una, se sube la version y ya.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="02"
NOMBRE="Dependencias vulnerables (SCA)"
HERRAMIENTA="pip-audit"
BLOQUEANTE="si"
UMBRAL="0 vulnerabilidades conocidas en requirements de api y moderador"
REPORTE="$DIR_REPORTES/02_dependencias.txt"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

VERSION="$(version_de pip-audit --version)"
if ! command -v pip-audit > /dev/null 2>&1; then
  echo "  pip-audit no esta instalado. Corre pipeline/preparar_herramientas.sh" | tee "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"
: > "$REPORTE"
PEOR_CODIGO=0
HUBO_ERROR=0

for archivo in app/api/requirements.txt app/moderador/requirements.txt; do
  echo "=== pip-audit sobre $archivo ===" >> "$REPORTE"
  timeout "$TIEMPO_LIMITE_ETAPA" pip-audit \
    --requirement "$archivo" \
    --progress-spinner off \
    >> "$REPORTE" 2>&1
  CODIGO=$?
  echo "(codigo de salida: $CODIGO)" >> "$REPORTE"
  echo "" >> "$REPORTE"

  case "$CODIGO" in
    0) ;;
    1) [[ "$PEOR_CODIGO" -eq 0 ]] && PEOR_CODIGO=1 ;;
    *) HUBO_ERROR=1; PEOR_CODIGO="$CODIGO" ;;
  esac
done

if [[ "$HUBO_ERROR" -eq 1 ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="pip-audit fallo al evaluar algun archivo (codigo $PEOR_CODIGO)"
elif [[ "$PEOR_CODIGO" -eq 1 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="Hay dependencias con vulnerabilidades conocidas"
elif ! reporte_con_contenido "$REPORTE"; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="El reporte quedo vacio: no hay evidencia de que el control corriera"
else
  ESTADO="$ESTADO_OK"
  DETALLE="Sin vulnerabilidades conocidas en los requirements auditados"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$PEOR_CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$PEOR_CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
