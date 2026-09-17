#!/usr/bin/env bash
# Orquestador del pipeline de seguridad - Foro y resenas (Avance 2, LSCA2314).
#
# Corre las ocho etapas y las consolida en UNA sola decision final. Reglas de
# la puerta de control:
#
#   1. Todas las etapas corren siempre, aunque una falle: si me detuviera en la
#      primera, arreglaria un hallazgo a la vez sin ver el panorama, y ademas
#      perderia la evidencia de las demas.
#   2. La decision NO se toma leyendo la pantalla, se toma leyendo los archivos
#      de estado que cada etapa escribio. Si una etapa no escribio su estado,
#      cuenta como NO_EJECUTADO y bloquea.
#   3. ERROR_OPERATIVO bloquea igual que HALLAZGO. Un escaner que no arranco no
#      es un escaner que no encontro nada.
#   4. El codigo de salida del pipeline es el que decide si se puede promover:
#      0 permite, 1 bloquea.

set -uo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPAS_ESPERADAS=("01" "02" "03" "04" "05" "06" "07" "08")
declare -A NOMBRES_ETAPAS=(
  ["01"]="Secretos en codigo e historial"
  ["02"]="Dependencias vulnerables (SCA)"
  ["03"]="Patrones inseguros en Python (SAST)"
  ["04"]="Reglas propias del foro (SAST dirigido)"
  ["05"]="Configuracion de infraestructura y contenedores"
  ["06"]="Vulnerabilidades de las imagenes"
  ["07"]="Inventario de componentes (SBOM)"
  ["08"]="Flujos de negocio y autorizacion en ejecucion"
)
declare -A GUIONES_ETAPAS=(
  ["01"]="01_secretos.sh"
  ["02"]="02_dependencias.sh"
  ["03"]="03_sast_bandit.sh"
  ["04"]="04_sast_semgrep.sh"
  ["05"]="05_iac_checkov.sh"
  ["06"]="06_imagen_trivy.sh"
  ["07"]="07_sbom.sh"
  ["08"]="08_pruebas_flujo.sh"
)

cd "$RAIZ_PROYECTO"

# SOLO_CONSOLIDAR=1 corre unicamente la logica de decision sobre los archivos de
# estado que ya existan, sin ejecutar ninguna etapa. Sirve para probar la puerta
# (pipeline/probar_puerta.sh). No es una via para aprobar sin controles: si no
# hay estados, todo cuenta como NO_EJECUTADO y bloquea, y tanto el encabezado
# como veredicto.json quedan marcados como modo de prueba.
MODO_EJECUCION="completo"
if [[ "${SOLO_CONSOLIDAR:-0}" == "1" ]]; then
  MODO_EJECUCION="SOLO_CONSOLIDACION (prueba de la puerta, sin ejecutar etapas)"
else
  # Los estados de la corrida anterior se borran: arrastrar un estado viejo
  # haria pasar por ejecutada una etapa que hoy no corrio.
  rm -f \
    "$DIR_REPORTES"/estado_*.json \
    "$DIR_REPORTES"/0[1-8]_*.txt \
    "$DIR_REPORTES"/0[1-8]_*.json \
    "$DIR_REPORTES"/veredicto.json \
    "$DIR_REPORTES"/sbom_cyclonedx*.json
fi

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo 'sin repositorio git')"
RAMA="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'n/d')"
SUCIO="limpio"
if git status --porcelain 2>/dev/null | grep -q .; then
  SUCIO="CON CAMBIOS SIN CONFIRMAR"
fi

echo "============================================================"
echo " Pipeline de seguridad - Foro y resenas (Avance 2)"
echo "============================================================"
echo " Fecha (UTC)   : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo " Commit        : $COMMIT ($RAMA, $SUCIO)"
echo " Equipo        : $(uname -srm)"
echo " Host          : $(hostname)"
echo " Python        : $(python3 --version 2>&1)"
echo " Aplicacion    : ${URL_APLICACION:-http://localhost:8080}"
echo " Modo          : $MODO_EJECUCION"
echo "============================================================"

for etapa in "${ETAPAS_ESPERADAS[@]}"; do
  if [[ "${SOLO_CONSOLIDAR:-0}" == "1" ]]; then
    break
  fi
  guion="$RAIZ_PROYECTO/pipeline/${GUIONES_ETAPAS[$etapa]}"
  if [[ ! -x "$guion" && ! -f "$guion" ]]; then
    echo ""
    echo "[Etapa $etapa] Falta el guion ${GUIONES_ETAPAS[$etapa]}"
    continue
  fi
  # Se ignora el codigo de salida aqui a proposito: la decision se toma despues
  # con los archivos de estado, no con el exit de cada guion.
  bash "$guion" || true
done

echo ""
echo "============================================================"
echo " Consolidacion de las etapas"
echo "============================================================"
printf "%-6s %-46s %-16s %s\n" "ETAPA" "CONTROL" "ESTADO" "BLOQUEA"
printf "%-6s %-46s %-16s %s\n" "-----" "----------------------------------------------" "----------------" "-------"

BLOQUEOS=0
MOTIVOS=()
RESUMEN_JSON="$DIR_REPORTES/veredicto.json"
ENTRADAS_JSON=()

for etapa in "${ETAPAS_ESPERADAS[@]}"; do
  archivo="$DIR_REPORTES/estado_${etapa}.json"
  nombre="${NOMBRES_ETAPAS[$etapa]}"

  if [[ ! -f "$archivo" ]]; then
    estado="NO_EJECUTADO"
    bloqueante="si"
    detalle="La etapa no dejo archivo de estado"
  else
    mapfile -t CAMPOS_ESTADO < <(python3 - "$archivo" "$etapa" <<'PYTHON'
import json
import os
import sys

ruta, etapa_esperada = sys.argv[1:]
try:
    with open(ruta, encoding="utf-8") as archivo_estado:
        datos = json.load(archivo_estado)
    if datos.get("etapa") != etapa_esperada:
        raise ValueError("el numero de etapa no coincide")
    estado = datos.get("estado")
    if estado not in {"OK", "HALLAZGO", "ERROR_OPERATIVO"}:
        raise ValueError("estado desconocido")
    if datos.get("bloqueante") != "si":
        raise ValueError("la etapa obligatoria no esta marcada como bloqueante")
    reporte = datos.get("reporte")
    if not isinstance(reporte, str) or not os.path.isfile(reporte) or os.path.getsize(reporte) == 0:
        raise ValueError("el reporte declarado no existe o esta vacio")
    print(estado)
    print("si")
    print(str(datos.get("detalle", "")))
except Exception as error:
    print("NO_EJECUTADO")
    print("si")
    print(f"Archivo de estado invalido: {error}")
PYTHON
)
    estado="${CAMPOS_ESTADO[0]:-NO_EJECUTADO}"
    bloqueante="si"
    detalle="${CAMPOS_ESTADO[2]:-No se pudo validar el estado}"
  fi

  printf "%-6s %-46s %-16s %s\n" "$etapa" "${nombre:0:46}" "$estado" "$bloqueante"

  if [[ "$estado" != "$ESTADO_OK" ]]; then
    BLOQUEOS=$((BLOQUEOS + 1))
    MOTIVOS+=("Etapa $etapa ($nombre): $estado - $detalle")
  fi

  ENTRADAS_JSON+=("{\"etapa\":\"$etapa\",\"estado\":\"$estado\",\"bloqueante\":\"$bloqueante\"}")
done

echo ""
if [[ "$BLOQUEOS" -gt 0 ]]; then
  echo "Motivos del bloqueo:"
  for motivo in "${MOTIVOS[@]}"; do
    echo "  - $motivo"
  done
  echo ""
fi

VEREDICTO="PERMITIDO"
CODIGO_FINAL=0
if [[ "$BLOQUEOS" -gt 0 ]]; then
  VEREDICTO="BLOQUEADO"
  CODIGO_FINAL=1
fi

{
  echo "{"
  echo "  \"veredicto\": \"$VEREDICTO\","
  echo "  \"modo\": \"$MODO_EJECUCION\","
  echo "  \"commit\": \"$COMMIT\","
  echo "  \"arbol\": \"$SUCIO\","
  echo "  \"momento\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"etapas_bloqueantes_en_falla\": $BLOQUEOS,"
  echo "  \"etapas\": [$(IFS=,; echo "${ENTRADAS_JSON[*]}")]"
  echo "}"
} > "$RESUMEN_JSON"

# Se archiva una copia completa de los reportes de ESTA corrida. La corrida
# roja y la verde tienen que coexistir como evidencia: si cada ejecucion
# pisara la anterior, al terminar de remediar ya no quedaria prueba de que el
# pipeline habia bloqueado.
DIR_ARCHIVO="$DIR_REPORTES/corridas/$(date -u +%Y%m%dT%H%M%S%NZ)-${VEREDICTO,,}"
mkdir -p "$DIR_ARCHIVO"
for archivo in "$DIR_REPORTES"/*.txt "$DIR_REPORTES"/*.json; do
  [[ -f "$archivo" ]] && cp "$archivo" "$DIR_ARCHIVO/" 2>/dev/null
done
{
  echo "commit=$COMMIT"
  echo "rama=$RAMA"
  echo "arbol=$SUCIO"
  echo "veredicto=$VEREDICTO"
  echo "momento=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "sistema=$(uname -srm)"
} > "$DIR_ARCHIVO/contexto.txt"

echo "============================================================"
if [[ "$CODIGO_FINAL" -eq 1 ]]; then
  echo " DESPLIEGUE BLOQUEADO"
  echo " $BLOQUEOS control(es) obligatorio(s) no estan en verde."
  echo " No se promueve nada hasta corregir la causa."
else
  echo " DESPLIEGUE PERMITIDO"
  echo " Los 8 controles obligatorios pasaron con evidencia valida."
fi
echo "============================================================"
echo " Veredicto guardado en: $RESUMEN_JSON"
echo " Reportes por etapa en: $DIR_REPORTES/"
echo " Copia archivada de esta corrida: $DIR_ARCHIVO/"

exit "$CODIGO_FINAL"
