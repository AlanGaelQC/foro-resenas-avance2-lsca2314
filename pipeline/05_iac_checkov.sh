#!/usr/bin/env bash
# Etapa 05 - Configuracion insegura de infraestructura y de las imagenes.
#
# Riesgo que cubre: los dos requisitos de infraestructura del Avance 2 se
# pierden por configuracion, no por codigo. Un bucket sin bloqueo de acceso
# publico expone los adjuntos de los usuarios; una RDS con publicly_accessible
# en true queda expuesta a Internet; un Dockerfile que corre como root anula el
# aislamiento del contenedor. Checkov revisa Terraform y Dockerfile sin
# desplegar nada.
#
# Umbral: CERO checks fallidos, salvo los IDs listados en
# pipeline/excepciones_checkov.txt, cada uno con su justificacion escrita.
# Checkov (edicion abierta) no entrega escala de severidad, asi que no se puede
# poner un umbral "solo HIGH": la politica compatible con su salida es
# cero fallos con excepciones nombradas una por una.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="05"
NOMBRE="Configuracion de infraestructura y contenedores (IaC)"
HERRAMIENTA="checkov"
BLOQUEANTE="si"
UMBRAL="0 checks fallidos salvo excepciones justificadas en pipeline/excepciones_checkov.txt"
REPORTE="$DIR_REPORTES/05_iac.txt"
REPORTE_JSON="$DIR_REPORTES/05_iac.json"
ARCHIVO_EXCEPCIONES="$RAIZ_PROYECTO/pipeline/excepciones_checkov.txt"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

VERSION="$(version_de checkov --version)"
if ! command -v checkov > /dev/null 2>&1; then
  echo "  checkov no esta instalado. Corre pipeline/preparar_herramientas.sh" | tee "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"

# --soft-fail: el veredicto no lo decide el codigo de salida de checkov sino la
# politica de excepciones de abajo. Aun asi se conserva su salida completa.
timeout "$TIEMPO_LIMITE_ETAPA" checkov \
  --directory infra/ \
  --framework terraform \
  --compact --quiet --soft-fail \
  --output cli > "$REPORTE" 2>&1
CODIGO_TF=$?

echo "" >> "$REPORTE"
echo "=== Dockerfiles ===" >> "$REPORTE"
timeout "$TIEMPO_LIMITE_ETAPA" checkov \
  --file Dockerfile --file Dockerfile.moderador \
  --framework dockerfile \
  --compact --quiet --soft-fail \
  --output cli >> "$REPORTE" 2>&1
CODIGO_DOCKER=$?

# Salida JSON combinada para aplicar la politica de forma ejecutable.
# Sin --quiet a proposito: el JSON debe incluir tambien los checks que pasaron,
# porque la evidencia de que el bucket no es publico y la base esta cifrada
# esta justamente ahi. Un reporte que solo lista fallos no demuestra que se
# haya comprobado lo importante.
timeout "$TIEMPO_LIMITE_ETAPA" checkov \
  --directory infra/ --file Dockerfile --file Dockerfile.moderador \
  --soft-fail --output json > "$REPORTE_JSON" 2>/dev/null
CODIGO_JSON=$?

if [[ ! -s "$REPORTE_JSON" ]]; then
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" "$CODIGO_JSON" "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "checkov no produjo salida JSON evaluable"
  resumir_resultado "$ESTADO_ERROR" "$CODIGO_JSON" "$REPORTE"
  exit 1
fi

EVALUACION="$(python3 - "$REPORTE_JSON" "$ARCHIVO_EXCEPCIONES" <<'PYTHON'
import json
import sys

ruta_json, ruta_excepciones = sys.argv[1], sys.argv[2]

try:
    with open(ruta_json) as archivo:
        datos = json.load(archivo)
except Exception:
    print("INVALIDO 0 0")
    raise SystemExit(0)

# checkov devuelve un objeto o una lista de objetos segun cuantos frameworks corrio.
bloques = datos if isinstance(datos, list) else [datos]
if not bloques or any(
    not isinstance(bloque, dict)
    or not isinstance(bloque.get("results"), dict)
    or not isinstance(bloque["results"].get("failed_checks"), list)
    or not isinstance(bloque["results"].get("passed_checks"), list)
    for bloque in bloques
):
    print("INVALIDO 0 0 0")
    raise SystemExit(0)

excepciones = set()
try:
    with open(ruta_excepciones) as archivo:
        for linea in archivo:
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                excepciones.add(linea.split()[0])
except FileNotFoundError:
    pass

fallidos = []
pasados = []
for bloque in bloques:
    for revision in bloque.get("results", {}).get("failed_checks", []):
        fallidos.append(
            (
                revision.get("check_id", "?"),
                revision.get("resource", "?"),
                revision.get("check_name", "?"),
            )
        )
    for revision in bloque.get("results", {}).get("passed_checks", []):
        pasados.append(
            (
                revision.get("check_id", "?"),
                revision.get("resource", "?"),
                revision.get("check_name", "?"),
            )
        )

# Comprobaciones que sostienen los requisitos del Avance 2: si alguna de estas
# no aparece entre los checks que pasaron, no basta con que no haya fallos.
PALABRAS_CRITICAS = ("public", "encrypt")
criticos_pasados = [
    p for p in pasados if any(palabra in p[2].lower() for palabra in PALABRAS_CRITICAS)
]

bloqueantes = [f for f in fallidos if f[0] not in excepciones]
exceptuados = [f for f in fallidos if f[0] in excepciones]
if not pasados and not fallidos:
    print("INVALIDO 0 0 0")
    raise SystemExit(0)

# Estos IDs prueban directamente los requisitos obligatorios del proyecto.
# Si un cambio de configuracion hace que Checkov deje de evaluar cualquiera de
# ellos, la etapa bloquea aunque el resto del reporte este limpio.
REQUERIDOS = {
    "CKV_AWS_16",   # RDS cifrada
    "CKV_AWS_17",   # RDS sin acceso publico
    "CKV_AWS_19",   # cifrado del bucket
    "CKV_AWS_20",   # bucket sin ACL publica
    "CKV2_AWS_6",   # bloqueo de acceso publico de S3
    "CKV_DOCKER_3", # contenedores con usuario no root
}
ids_pasados = {check_id for check_id, _, _ in pasados}
faltantes = sorted(REQUERIDOS - ids_pasados)

with open("REPORTE_POLITICA", "w") as salida:
    salida.write("Checks fallidos que BLOQUEAN (no estan en la lista de excepciones):\n")
    if bloqueantes:
        for check_id, recurso, nombre in bloqueantes:
            salida.write(f"  - {check_id}  {recurso}\n      {nombre}\n")
    else:
        salida.write("  (ninguno)\n")
    salida.write("\nChecks fallidos exceptuados con justificacion escrita:\n")
    if exceptuados:
        for check_id, recurso, nombre in exceptuados:
            salida.write(f"  - {check_id}  {recurso}\n      {nombre}\n")
    else:
        salida.write("  (ninguno)\n")

    salida.write(
        f"\nChecks que pasaron: {len(pasados)} en total, "
        f"{len(criticos_pasados)} sobre acceso publico y cifrado:\n"
    )
    for check_id, recurso, nombre in sorted(set(criticos_pasados)):
        salida.write(f"  + {check_id}  {recurso}\n      {nombre}\n")

    salida.write("\nChecks obligatorios que no aparecen como aprobados:\n")
    if faltantes:
        for check_id in faltantes:
            salida.write(f"  - {check_id}\n")
    else:
        salida.write("  (ninguno)\n")

print("VALIDO", len(bloqueantes), len(exceptuados), len(faltantes))
PYTHON
)"

read -r VALIDEZ CANTIDAD_BLOQUEANTES CANTIDAD_EXCEPTUADOS CANTIDAD_FALTANTES <<< "${EVALUACION:-INVALIDO 0 0 0}"

if [[ -f REPORTE_POLITICA ]]; then
  echo "" >> "$REPORTE"
  echo "=== Politica de bloqueo aplicada ===" >> "$REPORTE"
  cat REPORTE_POLITICA >> "$REPORTE"
  rm -f REPORTE_POLITICA
fi

if [[ "$VALIDEZ" != "VALIDO" ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="No se pudo evaluar la salida de checkov"
elif [[ "$CODIGO_TF" -ne 0 || "$CODIGO_DOCKER" -ne 0 || "$CODIGO_JSON" -ne 0 ]]; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="Checkov fallo al ejecutarse (tf=$CODIGO_TF, docker=$CODIGO_DOCKER, json=$CODIGO_JSON)"
elif [[ "$CANTIDAD_BLOQUEANTES" -gt 0 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="$CANTIDAD_BLOQUEANTES checks fallidos sin excepcion ($CANTIDAD_EXCEPTUADOS exceptuados)"
elif [[ "$CANTIDAD_FALTANTES" -gt 0 ]]; then
  ESTADO="$ESTADO_HALLAZGO"
  DETALLE="$CANTIDAD_FALTANTES checks obligatorios no aparecen como aprobados"
else
  ESTADO="$ESTADO_OK"
  DETALLE="Sin checks fallidos fuera de las $CANTIDAD_EXCEPTUADOS excepciones justificadas"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CANTIDAD_BLOQUEANTES" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CANTIDAD_BLOQUEANTES" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
