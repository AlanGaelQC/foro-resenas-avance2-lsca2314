"""
Suite de verificacion de PRODUCCION - Entrega Final (LSCA2314).

ESTADO: andamio. Comprueba que la release remediada corre en la instancia nueva,
SIN reusar T1 de QA (que exige entorno == "qa"). Aqui se exige entorno ==
"produccion". No corre pruebas destructivas ni limpia datos indiscriminadamente.

Uso:  python3 verificar_produccion.py https://<host-o-ip-de-produccion>

Las comprobaciones que dependen de datos/credenciales de la instancia quedan como
PENDIENTE-AWS: se completan cuando exista la EC2 de Produccion. Este archivo NO
inventa resultados: si no puede alcanzar el destino, lo dice y sale != 0.
"""
import sys

import httpx

URL_BASE = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
TIEMPO = 10.0
resultados: list[tuple[str, bool, str]] = []


def registrar(nombre: str, ok: bool, detalle: str = "") -> None:
    resultados.append((nombre, ok, detalle))
    print(f"  [{'PASA ' if ok else 'FALLA'}] {nombre}" + (f" -- {detalle}" if detalle else ""))


def main() -> int:
    if not URL_BASE:
        print("Falta la URL de Produccion. Uso: verificar_produccion.py https://<host>")
        return 2

    try:
        salud = httpx.get(f"{URL_BASE}/salud", timeout=TIEMPO)
        cuerpo = salud.json()
    except Exception as error:  # noqa: BLE001
        registrar("Produccion responde /salud", False, f"sin respuesta: {error}")
        return 1

    # A diferencia de QA, aqui se exige entorno == produccion.
    registrar(
        "P1 La instancia se identifica como Produccion y esta viva",
        salud.status_code == 200 and cuerpo.get("entorno") == "produccion",
        f"http {salud.status_code}; entorno={cuerpo.get('entorno')}",
    )
    registrar(
        "P2 Base de datos alcanzable",
        cuerpo.get("base_datos") == "ok",
        f"base_datos={cuerpo.get('base_datos')}",
    )
    registrar(
        "P3 Almacenamiento S3 alcanzable",
        cuerpo.get("almacenamiento_s3") == "ok",
        f"s3={cuerpo.get('almacenamiento_s3')}",
    )

    # PENDIENTE-AWS: identidad de release (comparar Image IDs cargados contra el
    # manifiesto), recorrido usuario/moderador con cuentas de prueba
    # identificables, y comprobacion de que la vista previa YA remediada escapa el
    # contenido. Se completan con la instancia real.

    fallidas = [n for n, ok, _ in resultados if not ok]
    print(f"\nResultado Produccion: {len(resultados) - len(fallidas)}/{len(resultados)}")
    return 1 if fallidas else 0


if __name__ == "__main__":
    raise SystemExit(main())
