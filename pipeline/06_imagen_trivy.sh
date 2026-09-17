#!/usr/bin/env bash
# Etapa 06 - Vulnerabilidades de las imagenes construidas.
#
# Riesgo que cubre: mi codigo puede estar limpio y mis dependencias de Python al
# dia, y aun asi la imagen que despliego arrastra paquetes del sistema operativo
# base (openssl, zlib, libc) con CVE conocidos. Lo que corre en la instancia es
# la imagen, no el repositorio: si no la escaneo, no se que estoy desplegando.
#
# Umbral: CERO vulnerabilidades HIGH o CRITICAL **con correccion disponible**
# (--ignore-unfixed). Bloquear por vulnerabilidades sin parche disponible
# detendria el despliegue sin darme ninguna accion posible; esas quedan como
# riesgo residual documentado en la tabla de decisiones.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="06"
NOMBRE="Vulnerabilidades de las imagenes de contenedor"
HERRAMIENTA="trivy"
BLOQUEANTE="si"
UMBRAL="0 vulnerabilidades HIGH/CRITICAL con parche disponible en las dos imagenes"
REPORTE="$DIR_REPORTES/06_imagen.txt"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

IMAGEN_API="${IMAGEN_API:-foro-resenas-api:local}"
IMAGEN_MODERADOR="${IMAGEN_MODERADOR:-foro-resenas-moderador:local}"

VERSION="$(version_de trivy --version)"
: > "$REPORTE"

if ! command -v trivy > /dev/null 2>&1; then
  echo "trivy no esta instalado. Corre pipeline/preparar_herramientas.sh" >> "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

# Sin demonio de Docker no hay imagen que escanear. Eso es un control NO
# EJECUTADO, no un control aprobado: se registra como error operativo y bloquea.
if ! docker info > /dev/null 2>&1; then
  {
    echo "No hay demonio de Docker disponible en este entorno."
    echo "La etapa 06 necesita las imagenes ya construidas:"
    echo "  docker compose build"
    echo "Sin ellas el control no se ejecuto; no se puede afirmar que las"
    echo "imagenes esten limpias."
  } >> "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 125 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Sin demonio de Docker: imagenes no disponibles"
  resumir_resultado "$ESTADO_ERROR" 125 "$REPORTE"
  exit 1
fi

PEOR_CODIGO=0
HUBO_ERROR=0

for imagen in "$IMAGEN_API" "$IMAGEN_MODERADOR"; do
  echo "=== trivy image $imagen ===" >> "$REPORTE"

  if ! docker image inspect "$imagen" > /dev/null 2>&1; then
    echo "  La imagen $imagen no existe. Construye con: docker compose build" >> "$REPORTE"
    HUBO_ERROR=1
    continue
  fi

  timeout "$TIEMPO_LIMITE_ETAPA" trivy image \
    --severity HIGH,CRITICAL \
    --ignore-unfixed \
    --exit-code 1 \
    --no-progress \
    "$imagen" >> "$REPORTE" 2>&1
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
  DETALLE="trivy no pudo evaluar alguna imagen (codigo $PEOR_CODIGO)"
elif [[ "$PEOR_CODIGO" -eq 1 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="Hay vulnerabilidades HIGH/CRITICAL con parche disponible"
else
  ESTADO="$ESTADO_OK"
  DETALLE="Imagenes sin HIGH/CRITICAL corregibles"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$PEOR_CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$PEOR_CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
