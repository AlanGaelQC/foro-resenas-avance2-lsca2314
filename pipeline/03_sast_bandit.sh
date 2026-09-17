#!/usr/bin/env bash
# Etapa 03 - Patrones inseguros en el codigo Python (SAST general).
#
# Riesgo que cubre: errores clasicos que yo mismo puedo introducir escribiendo
# la app -- ejecutar comandos con shell=True, usar hashes debiles para las
# contrasenas del foro, deserializar datos sin validar, peticiones HTTP sin
# verificar TLS. Bandit conoce ese catalogo para Python.
#
# Umbral: CERO hallazgos de severidad MEDIA o ALTA con confianza MEDIA o ALTA
# (bandit -ll -ii). Los LOW se reportan pero no bloquean: en su mayoria son
# avisos de estilo defensivo (por ejemplo assert_used) cuyo costo de arreglar
# no se justifica frente al riesgo real en esta aplicacion.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="03"
NOMBRE="Patrones inseguros en Python (SAST)"
HERRAMIENTA="bandit"
BLOQUEANTE="si"
UMBRAL="0 hallazgos con severidad >= MEDIA y confianza >= MEDIA (-ll -ii)"
REPORTE="$DIR_REPORTES/03_sast_bandit.txt"
REPORTE_JSON="$DIR_REPORTES/03_sast_bandit.json"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

VERSION="$(version_de bandit --version)"
if ! command -v bandit > /dev/null 2>&1; then
  echo "  bandit no esta instalado. Corre pipeline/preparar_herramientas.sh" | tee "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"

timeout "$TIEMPO_LIMITE_ETAPA" bandit -r app/ -ll -ii -f txt -o "$REPORTE" 2>&1
CODIGO=$?
# Copia en JSON para poder contar hallazgos sin interpretar texto.
timeout "$TIEMPO_LIMITE_ETAPA" bandit -r app/ -ll -ii -f json -o "$REPORTE_JSON" > /dev/null 2>&1
CODIGO_JSON=$?

VALIDACION_JSON="$(python3 - "$REPORTE_JSON" <<'PYTHON'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as entrada:
        datos = json.load(entrada)
    resultados = datos.get("results")
    metricas = datos.get("metrics")
    if not isinstance(resultados, list) or not isinstance(metricas, dict) or not metricas:
        raise ValueError("estructura incompleta")
    print("VALIDO", len(resultados))
except Exception:
    print("INVALIDO 0")
PYTHON
)"
read -r VALIDEZ_JSON CANTIDAD <<< "${VALIDACION_JSON:-INVALIDO 0}"

if [[ "$CODIGO" -gt 1 || "$CODIGO_JSON" -gt 1 || "$VALIDEZ_JSON" != "VALIDO" ]]; then
    ESTADO="$ESTADO_ERROR"
    DETALLE="bandit no produjo evidencia valida (texto=$CODIGO, json=$CODIGO_JSON)"
elif [[ "$CANTIDAD" -gt 0 ]]; then
    ESTADO="$ESTADO_HALLAZGO"
    DETALLE="Bandit reporto $CANTIDAD hallazgos que superan el umbral"
else
    ESTADO="$ESTADO_OK"
    DETALLE="Sin hallazgos por encima del umbral"
fi

if [[ "$ESTADO" == "$ESTADO_OK" ]] && ! reporte_con_contenido "$REPORTE"; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="El reporte quedo vacio: no hay evidencia de que el control corriera"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
