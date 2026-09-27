"""Reproduce las exclusiones del escaneo con una cadena sintética sin valor.

Uso: python3 docs/auditoria/comprobar_gitleaks.py /ruta/al/binario/gitleaks
No escanea secretos del usuario ni contacta AWS. Crea directorios temporales.
Es una reproducción del estado auditado, no una prueba de regresión del arreglo.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

RAIZ = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gitleaks", help="Binario Gitleaks 8.21.2 usado por el proyecto")
    args = parser.parse_args()
    binario = str(Path(args.gitleaks).resolve())
    original = (RAIZ / ".gitleaks.toml").read_text()
    # Retirar únicamente las dos exclusiones que se están contrastando.
    ampliado = original.replace("  '''(^|/)\\.env$''',", "").replace("  '''reportes/''',", "")
    assert ampliado != original
    # Nunca se usa esta cadena para una sesión, cuenta o conexión real.
    marcador = "CLAVE_" + "SESION=" + "SINTETICA_NO_CREDENCIAL_" + "A" * 32 + "\n"

    def ejecutar(nombre, ruta, historico=False, ampliar=False):
        with tempfile.TemporaryDirectory(prefix="foro-secretos-sinteticos-") as temporal:
            base = Path(temporal)
            fuente = base / "fuente"
            fuente.mkdir()
            archivo = fuente / ruta
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(marcador)
            if historico:
                for comando in (
                    ["git", "init", "--quiet"],
                    ["git", "add", "."],
                    ["git", "-c", "user.name=Auditoria", "-c", "user.email=auditoria@example.invalid",
                     "commit", "--quiet", "-m", "Fixture sintético"],
                ):
                    subprocess.run(comando, cwd=fuente, check=True, capture_output=True)
                archivo.unlink()
                subprocess.run(["git", "add", "-u"], cwd=fuente, check=True, capture_output=True)
                subprocess.run(["git", "-c", "user.name=Auditoria", "-c", "user.email=auditoria@example.invalid",
                                "commit", "--quiet", "-m", "Retira fixture del árbol"],
                               cwd=fuente, check=True, capture_output=True)
            config, reporte = base / "config.toml", base / "reporte.json"
            config.write_text(ampliado if ampliar else original)
            comando = [binario, "detect", "--source", str(fuente), "--config", str(config),
                       "--report-format", "json", "--report-path", str(reporte), "--redact"]
            if not historico:
                comando.append("--no-git")
            proceso = subprocess.run(comando, cwd=fuente, capture_output=True, text=True, timeout=30)
            assert proceso.returncode in (0, 1), "El escáner no completó la prueba"
            hallazgos = len(json.loads(reporte.read_text()))
            esperado = 1 if ampliar or ruta == "muestra.txt" else 0
            assert proceso.returncode == esperado and (hallazgos > 0) == bool(esperado)
            print(f"{nombre}: salida={proceso.returncode}, hallazgos={hallazgos}")

    print("REPRODUCCIÓN SINTÉTICA: no contiene credenciales reales.")
    ejecutar("Control: archivo normal", "muestra.txt")
    ejecutar("Hueco: archivo bajo reportes/", "reportes/muestra.txt")
    ejecutar("Hueco: .env anidado", "anidada/.env")
    ejecutar("Hueco: .env eliminado pero presente en historial", ".env", historico=True)
    ejecutar("Control ampliado: reportes/ detectado", "reportes/muestra.txt", ampliar=True)
    ejecutar("Control ampliado: .env histórico detectado", ".env", historico=True, ampliar=True)


if __name__ == "__main__":
    main()
