#!/usr/bin/env bash
# Etapa 01 - Secretos en el arbol de trabajo y en el historial de git.
#
# Riesgo que cubre: la app necesita la contrasena de RDS, la CLAVE_SESION y las
# credenciales de AWS Academy. Cualquiera de las tres pegada en el codigo, o
# borrada en un commit posterior pero viva en el historial, vale por si sola la
# base completa del foro. El profesor ademas resta puntos por credenciales en el
# repositorio aunque sean de prueba.
#
# Umbral: CERO secretos detectados. No hay un "pocos secretos" tolerable.

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

ETAPA="01"
NOMBRE="Secretos en codigo e historial"
HERRAMIENTA="gitleaks"
BLOQUEANTE="si"
UMBRAL="0 secretos detectados (cualquier hallazgo bloquea)"
REPORTE="$DIR_REPORTES/01_secretos.txt"
REPORTE_JSON="$DIR_REPORTES/01_secretos.json"

anunciar_etapa "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$UMBRAL"

VERSION="$(version_de gitleaks version)"
if ! command -v gitleaks > /dev/null 2>&1; then
  echo "  gitleaks no esta instalado. Corre pipeline/preparar_herramientas.sh" | tee "$REPORTE"
  registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO_ERROR" 127 "$BLOQUEANTE" \
    "$REPORTE" "$UMBRAL" "$VERSION" "Binario no encontrado"
  resumir_resultado "$ESTADO_ERROR" 127 "$REPORTE"
  exit 1
fi

cd "$RAIZ_PROYECTO"

# El historial y el arbol actual son superficies distintas: un archivo sin
# seguimiento no aparece al recorrer commits, y un secreto borrado no aparece
# al revisar solo el arbol. Cuando existe .git se ejecutan ambos modos.
JSON_ARBOL="$DIR_REPORTES/01_secretos_arbol.json"
JSON_HISTORIAL="$DIR_REPORTES/01_secretos_historial.json"
: > "$REPORTE"

# El .env de QA contiene por necesidad la clave de sesion y la contrasena de
# RDS. No se evalua su contenido (gitleaks lo redactaria pero lo marcaria como
# fuga); se evalua el control que evita que llegue al repositorio. La exclusion
# en .gitleaks.toml es segura solo porque estas tres condiciones son
# obligatorias y cualquier incumplimiento bloquea.
CODIGO_ENV=0
echo "=== Proteccion de .env de ejecucion ===" >> "$REPORTE"
if [[ -e .env ]]; then
  if git ls-files --error-unmatch -- .env > /dev/null 2>&1; then
    echo "HALLAZGO: .env esta rastreado por Git." >> "$REPORTE"
    CODIGO_ENV=1
  elif ! git check-ignore -q -- .env; then
    echo "HALLAZGO: .env no esta cubierto por .gitignore." >> "$REPORTE"
    CODIGO_ENV=1
  elif [[ "$(stat -c '%a' .env 2>/dev/null)" != "600" ]]; then
    echo "HALLAZGO: .env no tiene permisos 600." >> "$REPORTE"
    CODIGO_ENV=1
  else
    echo "OK: .env no rastreado, ignorado por Git y con permisos 600." >> "$REPORTE"
  fi
else
  echo "OK: no existe .env de ejecucion en este arbol." >> "$REPORTE"
fi
echo "" >> "$REPORTE"

echo "=== Arbol de trabajo ===" >> "$REPORTE"
timeout "$TIEMPO_LIMITE_ETAPA" gitleaks detect \
  --source . --no-git \
  --config .gitleaks.toml \
  --report-format json --report-path "$JSON_ARBOL" \
  --redact --verbose >> "$REPORTE" 2>&1
CODIGO_ARBOL=$?

CODIGO_HISTORIAL=0
if [[ -d .git ]]; then
  MODO="arbol de trabajo + historial de git"
  echo "" >> "$REPORTE"
  echo "=== Historial de git ===" >> "$REPORTE"
  timeout "$TIEMPO_LIMITE_ETAPA" gitleaks detect \
    --source . \
    --config .gitleaks.toml \
    --report-format json --report-path "$JSON_HISTORIAL" \
    --redact --verbose >> "$REPORTE" 2>&1
  CODIGO_HISTORIAL=$?
else
  MODO="arbol de trabajo (sin historial: no hay .git)"
  printf '[]\n' > "$JSON_HISTORIAL"
fi

python3 - "$JSON_ARBOL" "$JSON_HISTORIAL" "$REPORTE_JSON" <<'PYTHON'
import json
import sys

hallazgos = []
for ruta in sys.argv[1:3]:
    try:
        with open(ruta, encoding="utf-8") as entrada:
            bloque = json.load(entrada)
        if not isinstance(bloque, list):
            raise ValueError("la raiz no es una lista")
        hallazgos.extend(bloque)
    except Exception:
        raise SystemExit(2)
with open(sys.argv[3], "w", encoding="utf-8") as salida:
    json.dump(hallazgos, salida, indent=2)
PYTHON
CODIGO_COMBINACION=$?

if [[ "$CODIGO_ARBOL" -gt 1 || "$CODIGO_HISTORIAL" -gt 1 || "$CODIGO_COMBINACION" -ne 0 ]]; then
  CODIGO=2
elif [[ "$CODIGO_ARBOL" -eq 1 || "$CODIGO_HISTORIAL" -eq 1 || "$CODIGO_ENV" -eq 1 ]]; then
  CODIGO=1
else
  CODIGO=0
fi

echo "Modo de escaneo: $MODO" >> "$REPORTE"

# gitleaks: 0 = limpio, 1 = encontro secretos, cualquier otro = fallo de la
# herramienta. Confundir el tercer caso con el primero es exactamente el error
# que este pipeline debe evitar.
case "$CODIGO" in
  0)
    ESTADO="$ESTADO_OK"
    DETALLE="Sin secretos detectados en $MODO"
    ;;
  1)
    ESTADO="$ESTADO_HALLAZGO"
    CANTIDAD="$(python3 -c "
import json
try:
    with open('$REPORTE_JSON') as archivo:
        print(len(json.load(archivo)))
except Exception:
    print('?')
" 2>/dev/null)"
    if [[ "$CODIGO_ENV" -eq 1 ]]; then
      DETALLE="La proteccion del .env incumple rastreo, ignore o permisos; gitleaks detecto $CANTIDAD secretos adicionales"
    else
      DETALLE="Se detectaron $CANTIDAD secretos"
    fi
    ;;
  124)
    ESTADO="$ESTADO_ERROR"
    DETALLE="Tiempo agotado tras ${TIEMPO_LIMITE_ETAPA}s"
    ;;
  *)
    ESTADO="$ESTADO_ERROR"
    DETALLE="gitleaks termino con codigo inesperado $CODIGO"
    ;;
esac

if [[ "$ESTADO" == "$ESTADO_OK" ]] && ! reporte_con_contenido "$REPORTE"; then
  ESTADO="$ESTADO_ERROR"
  DETALLE="El reporte quedo vacio: no hay evidencia de que el control corriera"
fi

registrar_estado "$ETAPA" "$NOMBRE" "$HERRAMIENTA" "$ESTADO" "$CODIGO" "$BLOQUEANTE" \
  "$REPORTE" "$UMBRAL" "$VERSION" "$DETALLE"
resumir_resultado "$ESTADO" "$CODIGO" "$REPORTE"
[[ "$ESTADO" == "$ESTADO_OK" ]]
