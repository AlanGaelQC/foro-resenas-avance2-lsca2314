#!/usr/bin/env bash
# Promocion a Produccion - Entrega Final (LSCA2314)
#
# ESTADO: andamio. Construye el manifiesto y empaqueta las imagenes ya probadas,
# pero los pasos que tocan la EC2 nueva estan marcados PENDIENTE-AWS: no se
# ejecutan hasta tener el inventario real (IP/host de Produccion, clave, SG) y el
# OK de Alan. "Construir una vez y promover la misma imagen": no se reconstruye
# en el destino.
#
# Regla: solo se promueve una version que paso el pipeline en VERDE. Este script
# rechaza promover si el veredicto no es PERMITIDO o si esta en modo prueba.

set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib_comun.sh"

VEREDICTO_JSON="$DIR_REPORTES/veredicto.json"
MANIFIESTO="$DIR_REPORTES/manifest_release.json"
IMAGEN_API="${IMAGEN_API:-foro-resenas-api:local}"
IMAGEN_MODERADOR="${IMAGEN_MODERADOR:-foro-resenas-moderador:local}"

COMMIT="$(git rev-parse HEAD 2>/dev/null || echo 'n/d')"

# 1. Comprobar que el ultimo veredicto es PERMITIDO, no es modo prueba, y que su
#    commit COINCIDE con el candidato actual (HEAD). Un veredicto de otro commit
#    no autoriza promover este arbol.
if [[ ! -f "$VEREDICTO_JSON" ]]; then
  echo "No hay veredicto.json: corre el pipeline en verde antes de promover." >&2
  exit 1
fi
if ! python3 - "$VEREDICTO_JSON" "$COMMIT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
commit_actual = sys.argv[2]
if d.get("veredicto") != "PERMITIDO":
    print(f"Veredicto = {d.get('veredicto')}: no se promueve.", file=sys.stderr); raise SystemExit(1)
if d.get("modo") != "completo":
    print("Solo un pipeline completo autoriza el empaquetado.", file=sys.stderr); raise SystemExit(1)
if d.get("arbol") != "limpio":
    print(f"Arbol no limpio ({d.get('arbol')}): no se promueve.", file=sys.stderr); raise SystemExit(1)
if d.get("commit") != commit_actual:
    print(f"El veredicto es del commit {d.get('commit')}, pero HEAD es "
          f"{commit_actual}: no coinciden, no se promueve.", file=sys.stderr)
    raise SystemExit(1)
print(f"Veredicto PERMITIDO sobre el commit candidato {commit_actual}.")
PY
then
  exit 1
fi

# El veredicto historico no certifica cambios locales posteriores al verde.
if [[ -n "$(git status --porcelain)" ]]; then
  echo "El arbol actual tiene cambios sin confirmar: repite el pipeline sobre un commit limpio." >&2
  exit 1
fi

# 2. Las imagenes del candidato DEBEN existir. Sin Docker o sin imagenes, esto es
#    un fallo (no se promueve algo que no se puede identificar), no un PENDIENTE.
if ! command -v docker > /dev/null 2>&1 || ! docker info > /dev/null 2>&1; then
  echo "Docker no esta disponible: no se puede identificar ni empaquetar las imagenes." >&2
  exit 1
fi
ID_API="$(docker image inspect --format '{{.Id}}' "$IMAGEN_API" 2>/dev/null)" || {
  echo "La imagen $IMAGEN_API no existe. Construye el candidato antes de promover." >&2
  exit 1
}
ID_MOD="$(docker image inspect --format '{{.Id}}' "$IMAGEN_MODERADOR" 2>/dev/null)" || {
  echo "La imagen $IMAGEN_MODERADOR no existe. Construye el candidato antes de promover." >&2
  exit 1
}

# La etapa 06 registro los Image IDs efectivamente analizados por Trivy.
# Una reconstruccion o cambio de etiqueta posterior al verde bloquea el empaquetado.
if [[ ! -f "$DIR_REPORTES/06_image_ids.json" ]]; then
  echo "Faltan los Image IDs de la etapa 06: repite el pipeline completo." >&2
  exit 1
fi
if ! python3 - "$DIR_REPORTES/06_image_ids.json" "$COMMIT" "$IMAGEN_API" "$ID_API" "$IMAGEN_MODERADOR" "$ID_MOD" <<'PYTHON'
import json
import sys
ruta, commit, tag_api, id_api, tag_mod, id_mod = sys.argv[1:]
try:
    with open(ruta, encoding="utf-8") as entrada:
        registrados = json.load(entrada)
    esperado = (registrados["commit"], registrados["api"]["tag"],
                registrados["api"]["image_id"], registrados["moderador"]["tag"],
                registrados["moderador"]["image_id"])
except (OSError, ValueError, KeyError, TypeError) as error:
    print(f"Registro de imagenes de la etapa 06 invalido: {error}", file=sys.stderr)
    raise SystemExit(1)
if esperado != (commit, tag_api, id_api, tag_mod, id_mod):
    print("Las imagenes actuales difieren de las escaneadas por la etapa 06.", file=sys.stderr)
    raise SystemExit(1)
PYTHON
then
  exit 1
fi

# 3. Exportar las imagenes y su hash. Cualquier fallo aqui termina != 0.
DIR_PAQUETE="$DIR_REPORTES/release"
mkdir -p "$DIR_PAQUETE"
docker image save "$IMAGEN_API" -o "$DIR_PAQUETE/api.tar" || { echo "Fallo al exportar api.tar" >&2; exit 1; }
docker image save "$IMAGEN_MODERADOR" -o "$DIR_PAQUETE/moderador.tar" || { echo "Fallo al exportar moderador.tar" >&2; exit 1; }
[[ -s "$DIR_PAQUETE/api.tar" && -s "$DIR_PAQUETE/moderador.tar" ]] || { echo "Los .tar exportados estan vacios." >&2; exit 1; }
HASH_API="$(sha256sum "$DIR_PAQUETE/api.tar" | awk '{print $1}')"
HASH_MOD="$(sha256sum "$DIR_PAQUETE/moderador.tar" | awk '{print $1}')"

cat > "$MANIFIESTO" <<JSON
{
  "source_commit": "$COMMIT",
  "imagen_api":       {"tag": "$IMAGEN_API", "image_id": "$ID_API", "sha256_tar": "$HASH_API"},
  "imagen_moderador": {"tag": "$IMAGEN_MODERADOR", "image_id": "$ID_MOD", "sha256_tar": "$HASH_MOD"},
  "momento": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
echo "Imágenes escaneadas empaquetadas; manifiesto escrito en $MANIFIESTO"

# 4. PENDIENTE-AWS: transferir a la EC2 nueva y cargar SIN reconstruir.
#    scp -i <clave> "$DIR_PAQUETE"/*.tar ec2-user@<IP-PROD>:~/release/
#    ssh ...  'sha256sum -c' (verificar hashes) && 'docker image load -i ...'
#    docker compose up -d   # usando las imagenes cargadas, sin build ni :latest
#    Verificar que los Image IDs cargados == los del manifiesto.
echo "[PENDIENTE-AWS] Transferencia y despliegue en Produccion: requiere IP/clave"
echo "                de la EC2 nueva y el OK de Alan. Solo terminó el empaquetado."
