#!/usr/bin/env bash
# Etapa 04 - Reglas propias del foro (SAST dirigido).
#
# Riesgo que cubre: lo que bandit no puede saber. Bandit conoce Python; no
# conoce que en MI aplicacion nada puede publicarse sin pasar por el servicio de
# moderacion, ni que los adjuntos solo pueden subirse por la funcion que valida
# tipo y tamano. Esas invariantes las escribo yo en
# pipeline/reglas_semgrep_foro.yml y esta etapa las hace cumplir.
#
# Umbral: CERO hallazgos de severidad ERROR. Los WARNING se reportan y no
# bloquean, porque describen higiene (depuracion encendida) y no una via de
# evasion de un control.
#
# Se usa un archivo de reglas local y --disable-version-check para no depender
# de semgrep.dev: la instancia del Learner Lab no siempre tiene esa salida.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="04"
NOMBRE="Reglas propias del foro (SAST dirigido)"
HERRAMIENTA="semgrep"
BLOQUEANTE="si"
UMBRAL="0 hallazgos de severidad ERROR con reglas_semgrep_foro.yml"
REPORTE="$DIR_REPORTES/04_sast_semgrep.txt"
REPORTE_JSON="$DIR_REPORTES/04_sast_semgrep.json"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

export SEMGREP_SEND_METRICS=off

VERSION="$(version_de semgrep --version)"
if ! command -v semgrep > /dev/null 2>&1; then
  echo "  semgrep no esta instalado. Corre pipeline/preparar_herramientas.sh" | tee "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"

timeout "$TIEMPO_LIMITE_ETAPA" semgrep scan \
  --config pipeline/reglas_semgrep_foro.yml \
  --disable-version-check \
  --metrics off \
  --error \
  --json --output "$REPORTE_JSON" \
  app/ > "$REPORTE" 2>&1
CODIGO=$?

# Version legible para el reporte de texto (el JSON es para contar).
timeout "$TIEMPO_LIMITE_ETAPA" semgrep scan \
  --config pipeline/reglas_semgrep_foro.yml \
  --disable-version-check --metrics off \
  app/ >> "$REPORTE" 2>&1

LECTURA="$(python3 -c "
import json
try:
    with open('$REPORTE_JSON') as archivo:
        datos = json.load(archivo)
except Exception as error:
    print('INVALIDO 0 0')
else:
    resultados = datos.get('results', [])
    errores_operativos = datos.get('errors', [])
    rutas = datos.get('paths', {}).get('scanned', [])
    if not isinstance(resultados, list) or errores_operativos or not rutas:
        print('INVALIDO 0 0')
        raise SystemExit(0)
    errores = [r for r in resultados if r.get('extra', {}).get('severity') == 'ERROR']
    avisos = [r for r in resultados if r.get('extra', {}).get('severity') == 'WARNING']
    print('VALIDO', len(errores), len(avisos))
" 2>/dev/null)"

read -r VALIDEZ CANTIDAD_ERROR CANTIDAD_AVISO <<< "${LECTURA:-INVALIDO 0 0}"

if [[ "$VALIDEZ" != "VALIDO" ]]; then
  # Salida ilegible: no se puede afirmar que no hay hallazgos.
  ESTADO="$ESTADO_ERROR"
  DETALLE="semgrep no produjo un JSON valido (codigo $CODIGO)"
elif [[ "$CODIGO" -eq 124 ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="Tiempo agotado tras ${TIEMPO_LIMITE_ETAPA}s"
elif [[ "$CANTIDAD_ERROR" -gt 0 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="$CANTIDAD_ERROR hallazgos ERROR y $CANTIDAD_AVISO WARNING con reglas propias"
elif [[ "$CODIGO" -gt 1 ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="semgrep termino con codigo inesperado $CODIGO"
else
  ESTADO="$ESTADO_OK"
  DETALLE="Sin hallazgos ERROR ($CANTIDAD_AVISO WARNING informativos)"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
