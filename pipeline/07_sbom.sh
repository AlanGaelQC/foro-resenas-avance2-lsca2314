#!/usr/bin/env bash
# Etapa 07 - Inventario de componentes (SBOM en formato CycloneDX).
#
# Riesgo que cubre: cuando manana salga un CVE de una libreria, la pregunta va a
# ser "¿mi foro la usa, en que version?". Sin inventario esa respuesta tarda
# horas de revisar imagenes a mano. El SBOM es ademas entregable obligatorio del
# Avance 2 (reportes/sbom_cyclonedx.json).
#
# Alcance declarado: el SBOM cubre las dependencias Python de los dos servicios,
# que es lo que instala cada imagen. No incluye los paquetes del sistema
# operativo de la imagen base; esos los cubre la etapa 06 con trivy.
#
# Umbral: el archivo debe existir, ser JSON CycloneDX valido y traer al menos un
# componente. Un SBOM vacio o corrupto cuenta como control no cumplido: sin
# evidencia valida no hay promocion.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="07"
NOMBRE="Inventario de componentes (SBOM CycloneDX)"
HERRAMIENTA="cyclonedx-py"
BLOQUEANTE="si"
UMBRAL="SBOM CycloneDX valido, con >= 1 componente, para los dos servicios"
REPORTE="$DIR_REPORTES/07_sbom.txt"
SBOM="$DIR_REPORTES/sbom_cyclonedx.json"
SBOM_MODERADOR="$DIR_REPORTES/sbom_cyclonedx_moderador.json"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

VERSION="$(version_de cyclonedx-py --version)"
: > "$REPORTE"

if ! command -v cyclonedx-py > /dev/null 2>&1; then
  echo "cyclonedx-py no esta instalado. Corre pipeline/preparar_herramientas.sh" >> "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"

timeout "$TIEMPO_LIMITE_ETAPA" cyclonedx-py requirements app/api/requirements.txt \
  --of JSON --output-reproducible -o "$SBOM" >> "$REPORTE" 2>&1
CODIGO_API=$?

timeout "$TIEMPO_LIMITE_ETAPA" cyclonedx-py requirements app/moderador/requirements.txt \
  --of JSON --output-reproducible -o "$SBOM_MODERADOR" >> "$REPORTE" 2>&1
CODIGO_MODERADOR=$?

VALIDACION="$(python3 - "$SBOM" "$SBOM_MODERADOR" <<'PYTHON'
import json
import sys

total = 0
for ruta in sys.argv[1:]:
    try:
        with open(ruta) as archivo:
            documento = json.load(archivo)
    except Exception:
        print("INVALIDO 0")
        raise SystemExit(0)
    if documento.get("bomFormat") != "CycloneDX":
        print("INVALIDO 0")
        raise SystemExit(0)
    total += len(documento.get("components", []))

print("VALIDO", total)
PYTHON
)"

read -r VALIDEZ COMPONENTES <<< "${VALIDACION:-INVALIDO 0}"

{
  echo ""
  echo "=== Validacion del SBOM ==="
  echo "Formato CycloneDX valido: $VALIDEZ"
  echo "Componentes inventariados (api + moderador): $COMPONENTES"
  echo "Archivo principal: $SBOM"
} >> "$REPORTE"

if [[ "$CODIGO_API" -ne 0 || "$CODIGO_MODERADOR" -ne 0 ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="cyclonedx-py fallo (api=$CODIGO_API, moderador=$CODIGO_MODERADOR)"
elif [[ "$VALIDEZ" != "VALIDO" ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="El SBOM no es CycloneDX valido"
elif [[ "$COMPONENTES" -lt 1 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="El SBOM no inventario ningun componente"
else
  ESTADO="$ESTADO_OK"
  DETALLE="SBOM valido con $COMPONENTES componentes"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CODIGO_API" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CODIGO_API" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
