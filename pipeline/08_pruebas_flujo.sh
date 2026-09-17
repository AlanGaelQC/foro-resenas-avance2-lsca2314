#!/usr/bin/env bash
# Etapa 08 - Comportamiento de la aplicacion en ejecucion.
#
# Riesgo que cubre: todo lo anterior mira archivos. Esta etapa mira la
# aplicacion corriendo y comprueba las cosas que solo se ven ahi: que el
# anonimo no publica, que el moderador de verdad detiene el contenido
# prohibido de punta a punta, que el texto del usuario se renderiza escapado y
# que un usuario no ve lo de otro.
#
# Umbral: TODAS las pruebas deben pasar. No hay margen: cada una corresponde a
# un requisito funcional o de autorizacion del proyecto, no a una preferencia.
#
# Nota sobre el alcance: /salud solo dice que el proceso vive. Que /salud
# responda 200 no prueba estas comprobaciones; por eso existe
# esta etapa aparte.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="08"
NOMBRE="Flujos de negocio y autorizacion en ejecucion"
HERRAMIENTA="pruebas_flujo.py (httpx)"
BLOQUEANTE="si"
UMBRAL="todas las pruebas de flujo deben pasar (0 fallos tolerados)"
REPORTE="$DIR_REPORTES/08_pruebas_flujo.txt"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

URL_APLICACION="${URL_APLICACION:-http://localhost:8080}"
VERSION="$(version_de python3 --version)"

INTERPRETE="python3"
if [[ -x "$VENV_PIPELINE/bin/python" ]]; then
  INTERPRETE="$VENV_PIPELINE/bin/python"
fi

cd "$RAIZ_PROYECTO"

timeout "$TIEMPO_LIMITE_ETAPA" "$INTERPRETE" pipeline/pruebas_flujo.py "$URL_APLICACION" \
  > "$REPORTE" 2>&1
CODIGO=$?

case "$CODIGO" in
  0)
    ESTADO="$ESTADO_OK"
    DETALLE="Todas las pruebas de flujo pasaron contra $URL_APLICACION"
    ;;
  1)
    # Distingue "la app no respondio" (error operativo) de "una prueba fallo"
    # (hallazgo de seguridad o funcional).
    if grep -q "no respondio /salud" "$REPORTE"; then
      ESTADO="$ESTADO_ERROR"
      DETALLE="La aplicacion no respondio en $URL_APLICACION: control no ejecutado"
    else
      ESTADO="$ESTADO_HALLAZGO"
      DETALLE="$(grep -c '^  \[FALLA\]' "$REPORTE" 2>/dev/null || echo '?') pruebas de flujo fallaron"
    fi
    ;;
  2)
    ESTADO="$ESTADO_ERROR"
    DETALLE="La aplicacion no respondio en $URL_APLICACION: control no ejecutado"
    ;;
  124)
    ESTADO="$ESTADO_ERROR"
    DETALLE="Tiempo agotado tras ${TIEMPO_LIMITE_ETAPA}s"
    ;;
  *)
    ESTADO="$ESTADO_ERROR"
    DETALLE="Las pruebas terminaron con codigo inesperado $CODIGO"
    ;;
esac

if [[ "$ESTADO" == "$ESTADO_OK" ]] && ! reporte_con_contenido "$REPORTE"; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="El reporte quedo vacio: no hay evidencia de que las pruebas corrieran"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
