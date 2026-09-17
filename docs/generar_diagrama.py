"""
Genera docs/diagrama_arquitectura.png.

El diagrama se genera con codigo y no a mano para poder regenerarlo cuando
cambie la arquitectura: un diagrama que muestra servicios que ya no existen es
justamente lo que la rubrica penaliza.

Uso:  python3 docs/generar_diagrama.py
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt

TINTA = "#1b1b1f"
GRIS = "#5b6470"
NUBE = "#e8f0fb"
NUBE_BORDE = "#3f74b8"
CONTENEDOR = "#edf7ee"
CONTENEDOR_BORDE = "#3f8f52"
INSTANCIA = "#fafafc"
SALUD_FONDO = "#fff6df"
SALUD_BORDE = "#b0810f"

figura, eje = plt.subplots(figsize=(14, 9.6))
eje.set_xlim(0, 14)
eje.set_ylim(0, 9.6)
eje.axis("off")


def caja(x, y, ancho, alto, titulo, lineas, color, borde, grosor=1.7, guion="solid", tamano=8.2):
    eje.add_patch(
        patches.FancyBboxPatch(
            (x, y), ancho, alto,
            boxstyle="round,pad=0.02",
            facecolor=color, edgecolor=borde, linewidth=grosor, linestyle=guion,
        )
    )
    eje.text(x + ancho / 2, y + alto - 0.34, titulo,
             ha="center", va="top", fontsize=11.5, fontweight="bold", color=TINTA)
    for indice, linea in enumerate(lineas):
        eje.text(x + ancho / 2, y + alto - 0.78 - indice * 0.26, linea,
                 ha="center", va="top", fontsize=tamano, color="#333")


def insignia_salud(x, y, ancho, texto):
    eje.add_patch(
        patches.FancyBboxPatch(
            (x, y), ancho, 0.42,
            boxstyle="round,pad=0.02",
            facecolor=SALUD_FONDO, edgecolor=SALUD_BORDE, linewidth=1.4,
        )
    )
    eje.text(x + ancho / 2, y + 0.21, texto, ha="center", va="center",
             fontsize=8.8, fontweight="bold", color=SALUD_BORDE)


def flecha(inicio, fin, color=GRIS, guion="solid"):
    eje.annotate("", xy=fin, xytext=inicio,
                 arrowprops=dict(arrowstyle="-|>", color=color, linewidth=1.7,
                                 linestyle=guion, shrinkA=1, shrinkB=1))


def etiqueta(x, y, texto, tamano=8.4, alineacion="center"):
    eje.text(x, y, texto, ha=alineacion, va="center", fontsize=tamano, color=TINTA,
             bbox=dict(boxstyle="round,pad=0.26", facecolor="white",
                       edgecolor="#d5d8de", linewidth=0.8))


# --- Titulo -------------------------------------------------------------------
eje.text(7, 9.25, "Foro y reseñas — arquitectura del Avance 2",
         ha="center", fontsize=15.5, fontweight="bold", color=TINTA)
eje.text(7, 8.92, "LSCA2314 · tema 4 · el moderador corre en su propio contenedor, separado de la API",
         ha="center", fontsize=9.6, color="#666")

# --- Instancia EC2 ------------------------------------------------------------
eje.add_patch(
    patches.FancyBboxPatch((3.05, 1.95), 5.85, 6.35, boxstyle="round,pad=0.03",
                           facecolor=INSTANCIA, edgecolor=GRIS,
                           linewidth=1.6, linestyle=(0, (6, 4)))
)
eje.text(5.97, 8.05, "Instancia EC2 · AWS Academy · Docker Compose",
         ha="center", fontsize=10, fontweight="bold", color=TINTA)
eje.text(5.97, 7.79, "red interna:  red_foro", ha="center", fontsize=8.4, color="#777")

# --- Usuario ------------------------------------------------------------------
caja(0.35, 6.15, 2.2, 1.15, "Usuario", ["navegador web"], "#ffffff", GRIS)
flecha((2.55, 6.72), (3.35, 6.72))
etiqueta(2.95, 7.12, "HTTP\n:8080", tamano=8.0)

# --- Contenedor API -----------------------------------------------------------
caja(3.35, 5.70, 5.25, 1.95, "contenedor   api",
     ["FastAPI + Uvicorn · usuario no root · HEALTHCHECK",
      "publica 8080 → 8000",
      "registro · sesión · reseñas · comentarios · adjuntos"],
     CONTENEDOR, CONTENEDOR_BORDE, tamano=7.6)
insignia_salud(3.62, 5.76, 4.71, "GET /salud   →   vivo · base de datos · S3")

# --- Contenedor moderador -----------------------------------------------------
caja(3.35, 3.15, 5.25, 1.95, "contenedor   moderador",
     ["FastAPI + Uvicorn · usuario no root · HEALTHCHECK",
      "puerto 8001, solo en la red interna",
      "5 reglas: léxico · enlaces · contacto · gritería · vacío"],
     CONTENEDOR, CONTENEDOR_BORDE, tamano=7.6)
insignia_salud(3.62, 3.21, 4.71, "GET /salud   →   vivo")

# Ida y vuelta entre api y moderador
flecha((4.55, 5.70), (4.55, 5.10))
etiqueta(3.55, 5.40, "POST /moderar\nantes de publicar", tamano=7.9)
flecha((7.30, 5.10), (7.30, 5.70))
etiqueta(8.18, 5.40, "aprobado / rechazado\n+ motivo", tamano=7.9)

# --- Pipeline -----------------------------------------------------------------
caja(3.35, 2.10, 5.25, 0.98, "pipeline/   ·   8 controles → un solo veredicto",
     ["gitleaks · pip-audit · bandit · semgrep · checkov · trivy · SBOM · pruebas de flujo"],
     "#f1eff9", "#6a5acd", grosor=1.5, tamano=7.0)

# --- Servicios de AWS ---------------------------------------------------------
caja(9.85, 6.30, 3.85, 1.60, "Amazon S3",
     ["bucket privado de adjuntos", "acceso público bloqueado · cifrado AES256",
      "versionado · solo TLS · URL prefirmada 5 min"],
     NUBE, NUBE_BORDE)

caja(9.85, 3.75, 3.85, 1.60, "Amazon RDS · PostgreSQL",
     ["cifrada en reposo · sin acceso público", "alcanzable solo desde el SG de la instancia",
      "tablas: usuarios · hilos · comentarios"],
     NUBE, NUBE_BORDE)

flecha((8.60, 7.15), (9.85, 7.15))
etiqueta(9.22, 7.58, "HTTPS · boto3\nput_object / presigned", tamano=7.9)

flecha((8.60, 6.10), (9.85, 4.95))
etiqueta(9.32, 5.66, "SQL :5432\ndentro de la VPC", tamano=7.9)

# --- Flujo --------------------------------------------------------------------
eje.text(0.35, 1.72, "Flujo completo de una reseña",
         fontsize=10.5, fontweight="bold", color=TINTA)
pasos = [
    "1.  El usuario con sesión iniciada envía título, texto, calificación de 1 a 5 y, si quiere, una imagen.",
    "2.  Si hay imagen, la API valida tamaño, tipo, extensión y firma real; todavía no la sube.",
    "3.  La API consulta al moderador. Si no responde, la petición falla con 503 y no se guarda nada.",
    "4.  Si se aprueba, sube el adjunto a S3; después guarda en RDS el estado y el motivo del veredicto.",
    "5.  Lo publicado aparece en la portada; lo rechazado solo lo ve su autor en /mis-publicaciones, junto con el motivo.",
]
for indice, paso in enumerate(pasos):
    eje.text(0.35, 1.38 - indice * 0.30, paso, fontsize=8.9, color="#333")

eje.text(13.75, 0.12, "Regenerar con:  python3 docs/generar_diagrama.py",
         ha="right", fontsize=7.6, color="#a5a5a5")

destino = pathlib.Path(__file__).parent / "diagrama_arquitectura.png"
plt.savefig(destino, dpi=170, bbox_inches="tight", facecolor="white")
print(f"diagrama escrito en {destino}")
