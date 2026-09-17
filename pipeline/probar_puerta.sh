#!/usr/bin/env bash
# Prueba de la puerta de control (la logica de decision del orquestador).
#
# Esto NO es un escaneo de seguridad ni produce evidencia de la aplicacion:
# comprueba que la decision final se comporta como esta documentada, usando
# estados sinteticos en un directorio temporal. El profesor pregunta "¿tu
# pipeline de verdad bloquea?"; esta prueba responde por los cuatro casos,
# incluido el que mas se olvida: el control que nunca corrio.
#
# Casos que verifica:
#   1. Las 8 etapas en OK                  -> DESPLIEGUE PERMITIDO, salida 0
#   2. Una etapa con HALLAZGO              -> DESPLIEGUE BLOQUEADO,  salida 1
#   3. Una etapa con ERROR_OPERATIVO       -> DESPLIEGUE BLOQUEADO,  salida 1
#   4. Una etapa sin archivo de estado     -> DESPLIEGUE BLOQUEADO,  salida 1
#
# Uso:  bash pipeline/probar_puerta.sh

set -uo pipefail

RAIZ_PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPORAL="$(mktemp -d)"
trap 'rm -rf "$TEMPORAL"' EXIT

ETAPAS=("01" "02" "03" "04" "05" "06" "07" "08")
PASARON=0
TOTAL=0

escribir_estado() {
  local etapa="$1" estado="$2"
  local reporte="$TEMPORAL/reporte_${etapa}.txt"
  printf 'Evidencia sintetica para probar la puerta, etapa %s\n' "$etapa" > "$reporte"
  cat > "$TEMPORAL/estado_${etapa}.json" <<JSON
{
  "etapa": "$etapa",
  "nombre": "Estado sintetico de prueba",
  "herramienta": "prueba",
  "estado": "$estado",
  "codigo_salida": 0,
  "bloqueante": "si",
  "umbral": "prueba de la puerta",
  "reporte": "$reporte",
  "detalle": "generado por probar_puerta.sh",
  "momento": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
}

preparar_todo_ok() {
  rm -f "$TEMPORAL"/estado_*.json "$TEMPORAL"/reporte_*.txt
  for etapa in "${ETAPAS[@]}"; do
    escribir_estado "$etapa" "OK"
  done
}

comprobar() {
  # comprobar <descripcion> <veredicto esperado> <codigo esperado>
  local descripcion="$1" veredicto_esperado="$2" codigo_esperado="$3"
  TOTAL=$((TOTAL + 1))

  local salida
  salida="$(cd "$RAIZ_PROYECTO" && SOLO_CONSOLIDAR=1 DIR_REPORTES="$TEMPORAL" \
    bash pipeline/orquestador.sh 2>&1)"
  local codigo=$?

  if grep -q "DESPLIEGUE $veredicto_esperado" <<< "$salida" && [[ "$codigo" -eq "$codigo_esperado" ]]; then
    echo "  [PASA ] $descripcion -> DESPLIEGUE $veredicto_esperado (salida $codigo)"
    PASARON=$((PASARON + 1))
  else
    echo "  [FALLA] $descripcion"
    echo "          esperaba DESPLIEGUE $veredicto_esperado con salida $codigo_esperado"
    echo "          obtuvo salida $codigo y:"
    grep -E "DESPLIEGUE" <<< "$salida" | sed 's/^/            /'
  fi
}

echo "============================================================"
echo " Prueba de la puerta de control"
echo "============================================================"

preparar_todo_ok
comprobar "Caso 1: las 8 etapas en OK" "PERMITIDO" 0

preparar_todo_ok
escribir_estado "04" "HALLAZGO"
comprobar "Caso 2: una etapa con HALLAZGO" "BLOQUEADO" 1

preparar_todo_ok
escribir_estado "06" "ERROR_OPERATIVO"
comprobar "Caso 3: una etapa con ERROR_OPERATIVO" "BLOQUEADO" 1

preparar_todo_ok
rm -f "$TEMPORAL/estado_02.json"
comprobar "Caso 4: una etapa sin archivo de estado (nunca corrio)" "BLOQUEADO" 1

echo ""
echo "Resultado: $PASARON/$TOTAL casos de la puerta se comportan como documentado"
[[ "$PASARON" -eq "$TOTAL" ]]
