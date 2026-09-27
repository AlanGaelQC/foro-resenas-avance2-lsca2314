"""Diagramas documentales de la Entrega Final, sin acceso a AWS.
Uso: python3 docs/generar_diagrama.py
Requiere matplotlib. Genera PNG y SVG junto a este archivo.
Topología basada en código y registros archivados, no en una consulta en vivo.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

DESTINO = Path(__file__).resolve().parent
TINTA, SECUNDARIO = "#152B43", "#516477"
AZUL, VERDE, VIOLETA = "#3267AE", "#127968", "#6650A1"
BORDE, FONDO, AMBAR = "#D7E1EB", "#F4F7FB", "#9A5A16"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})

def texto(ax, x, y, contenido, tam=11, color=TINTA, peso="normal", ha="left"):
    return ax.text(x, y, contenido, fontsize=tam, color=color, fontweight=peso,
                   ha=ha, va="center", linespacing=1.5)

def pagina(titulo, subtitulo, alto=11):
    fig, ax = plt.subplots(figsize=(16, alto))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set(xlim=(0, 16), ylim=(0, alto))
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 16, alto, color="white"))
    ax.add_patch(Rectangle((0, alto - 1.45), 16, 1.45, color=TINTA))
    texto(ax, .65, alto-.38, "PULSO PIXEL  /  ENTREGA FINAL", 10, "#84DFCB", peso="bold")
    texto(ax, .65, alto-.87, titulo, 23, "white", peso="bold")
    texto(ax, .65, alto-1.19, subtitulo, 10, "#D6E2EE")
    return fig, ax

def caja(ax, x, y, w, h, fondo="white", borde=BORDE, grosor=1.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015,rounding_size=0.12",
                               facecolor=fondo, edgecolor=borde, linewidth=grosor))

def flecha(ax, x1, y1, x2, y2, color=SECUNDARIO, estilo="solid"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                mutation_scale=15, linewidth=1.7, color=color,
                                linestyle=estilo, shrinkA=2, shrinkB=2))

def etiqueta(ax, x, y, contenido, color=SECUNDARIO, tam=9.5):
    return ax.text(x, y, contenido, ha="center", va="center", fontsize=tam, color=color,
                   bbox={"boxstyle": "round,pad=.35", "facecolor": "white", "edgecolor": "none"})

def guardar(fig, nombre):
    for extension in ("png", "svg"):
        ruta = DESTINO / f"{nombre}.{extension}"
        fig.savefig(ruta, dpi=180, facecolor="white")
        if extension == "svg":
            ruta.write_text("\n".join(linea.rstrip() for linea in ruta.read_text().splitlines()) + "\n")
        print(ruta)
    plt.close(fig)

def arquitectura():
    fig, ax = pagina("Arquitectura desplegada", "Dos EC2 · dos redes Compose · un RDS y un bucket compartidos · release documentada: 0ec86bb")
    caja(ax, .65, 8.45, 14.7, .65, FONDO)
    texto(ax, 8, 8.78, "NAVEGADOR  ·  jugadores y moderadores con sesión", 12, ha="center", peso="bold")
    for x, rotulo in ((4.13, "HTTP :8080 · SG de QA"), (11.88, "HTTP :8080 · SG de Producción")):
        flecha(ax, x, 8.45, x, 7.88)
        etiqueta(ax, x, 8.15, rotulo)
    for x, color, nombre, descripcion, inferior, detalle in (
        (.65, AZUL, "01  QA", "EC2 del Avance 2 · desarrollo y validación",
         "PIPELINE DE SEGURIDAD", "8 etapas → veredicto → exportación de imágenes"),
        (8.4, VERDE, "02  PRODUCCIÓN", "EC2 nueva · despliegue del candidato aprobado",
         "EJECUCIÓN DE LA RELEASE", "Importación de imágenes · arranque · verificación"),
    ):
        caja(ax, x, 4.38, 6.95, 3.49, FONDO, color, 1.6)
        texto(ax, x+.25, 7.48, nombre, 15, color, peso="bold")
        texto(ax, x+.25, 7.11, descripcion, 10, SECUNDARIO)
        caja(ax, x+.25, 5.52, 3.3, 1.25)
        texto(ax, x+.45, 6.47, "API · FastAPI", 12, peso="bold")
        texto(ax, x+.45, 6.12, "8080 del host → 8000", 10, SECUNDARIO)
        texto(ax, x+.45, 5.78, "Sesiones · reseñas · adjuntos", 9.5, SECUNDARIO)
        caja(ax, x+4.48, 5.52, 2.22, 1.25)
        texto(ax, x+4.66, 6.47, "Moderador", 12, peso="bold")
        texto(ax, x+4.66, 6.12, "Reglas y render seguro", 9, SECUNDARIO)
        texto(ax, x+4.66, 5.78, "Sin puerto público", 9.5, SECUNDARIO)
        flecha(ax, x+3.55, 6.22, x+4.48, 6.22, color)
        etiqueta(ax, x+4.0, 6.61, "HTTP", color, 8.5)
        etiqueta(ax, x+4.0, 5.9, ":8001", color, 8.5)
        texto(ax, x+.25, 5.2, "Red red_foro propia · ambos sin root · HEALTHCHECK real /salud", 9, SECUNDARIO)
        texto(ax, x+.25, 4.88, inferior, 9.5, color, peso="bold")
        texto(ax, x+.25, 4.59, detalle, 9.5, SECUNDARIO)
    for x in (4.13, 11.88):
        flecha(ax, x, 4.38, x, 3.65)
        etiqueta(ax, x, 4.04, "API → datos y adjuntos")
    caja(ax, .65, 1.0, 14.7, 2.64, "#F8FAFC", BORDE)
    texto(ax, .92, 3.34, "SERVICIOS AWS COMPARTIDOS", 11, peso="bold")
    texto(ax, 15.05, 3.34, "Separación lógica; no aislamiento entre cuentas AWS", 9.5, SECUNDARIO, ha="right")
    caja(ax, .92, 1.31, 6.68, 1.65)
    texto(ax, 1.15, 2.64, "Amazon RDS · una instancia PostgreSQL", 12, AZUL, peso="bold")
    texto(ax, 1.15, 2.26, "QA: foro   |   Producción: foro_prod / usuario foro_prod", 10, SECUNDARIO)
    texto(ax, 1.15, 1.88, "TCP :5432 · SG permite a las EC2 · sin acceso público¹", 10, SECUNDARIO)
    texto(ax, 1.15, 1.52, "Tablas: usuarios · hilos · comentarios", 10, SECUNDARIO)
    caja(ax, 8.01, 1.31, 7.06, 1.65)
    texto(ax, 8.24, 2.64, "Amazon S3 · un bucket de adjuntos", 12, VERDE, peso="bold")
    texto(ax, 8.24, 2.26, "QA: adjuntos/   |   Producción: produccion/adjuntos/", 10, SECUNDARIO)
    texto(ax, 8.24, 1.88, "HTTPS · boto3 / perfil IAM · objetos privados¹", 10, SECUNDARIO)
    texto(ax, 8.24, 1.52, "Descarga por URL prefirmada de 5 minutos, tras autorizar", 10, SECUNDARIO)
    texto(ax, .65, .65, "Límite de transporte: navegador → EC2 usa HTTP; COOKIE_SEGURA=false. No se declara HTTPS integral.", 10, AMBAR)
    texto(ax, .65, .33, "¹ Topología y acceso según código y registros archivados. Cifrado, políticas y permisos efectivos requieren comprobación actual en AWS.", 9, SECUNDARIO)
    guardar(fig, "diagrama_arquitectura")

def promocion():
    fig, ax = pagina("De QA a Producción: controles y evidencia", "Flujo ejecutado · sin reconstruir imágenes en el destino · los pasos manuales se indican expresamente", alto=10.3)
    caja(ax, .65, 6.77, 3.45, 1.44, FONDO)
    texto(ax, .88, 7.87, "1. CANDIDATO EN QA", 12, AZUL, peso="bold")
    texto(ax, .88, 7.46, "Commit + árbol limpio", 11, SECUNDARIO)
    texto(ax, .88, 7.1, "Construir imágenes y ejecutar app", 10, SECUNDARIO)
    flecha(ax, 4.1, 7.5, 4.7, 7.5)
    caja(ax, 4.72, 6.36, 10.63, 1.85, "#F4F1FA", "#D7CEEA")
    texto(ax, 4.96, 7.86, "2. OCHO ETAPAS · pipeline/orquestador.sh", 12, VIOLETA, peso="bold")
    texto(ax, 4.96, 7.36, "01 Secretos        02 Dependencias        03 Bandit        04 Semgrep", 11, SECUNDARIO)
    texto(ax, 4.96, 6.88, "05 IaC / Docker    06 Imágenes / Trivy    07 SBOM          08 Flujos HTTP", 11, SECUNDARIO)
    flecha(ax, 10.03, 6.36, 10.03, 5.77, VIOLETA)
    caja(ax, 7.62, 4.93, 4.82, .84, "#F4F1FA", VIOLETA)
    texto(ax, 10.03, 5.35, "¿Ocho estados OK con evidencia?", 12, VIOLETA, peso="bold", ha="center")
    flecha(ax, 7.62, 5.35, 6.75, 5.35, "#B44043")
    etiqueta(ax, 7.16, 5.65, "NO", "#B44043", 9)
    caja(ax, .65, 4.78, 6.08, 1.16, "#FFF4F3", "#DEAEB0")
    texto(ax, .88, 5.6, "BLOQUEADO · no se promueve", 12, "#A2393D", peso="bold")
    texto(ax, .88, 5.19, "Hallazgo, error o control sin ejecutar → corregir y repetir en QA", 9.3, SECUNDARIO)
    flecha(ax, 10.03, 4.93, 10.03, 4.27, VERDE)
    etiqueta(ax, 10.43, 4.58, "SÍ", VERDE, 9)
    bloques = [
        (.65, "3. EMPAQUETAR EN QA", "promover.sh", "Veredicto + commit + árbol limpio", "Image IDs de Trivy → docker save", "Manifiesto + SHA-256 de los tar"),
        (5.71, "4. TRANSFERIR E IMPORTAR", "Operación manual por SSH", "Copiar tar y manifiesto aprobado", "Comprobar hashes → docker load", "Tag Git del candidato aprobado"),
        (10.77, "5. ACTIVAR Y VERIFICAR", "Operación en EC2 Producción", "compose up --no-build --pull never", "Contenedores activos: inspección manual", "Verificador: salud, HTTP, tags y tar"),
    ]
    ax.plot([10.03, 2.96], [4.24, 4.24], color=VERDE, linewidth=1.7)
    flecha(ax, 2.96, 4.24, 2.96, 3.93, VERDE)
    for x, titulo, subtitulo, a, b, c in bloques:
        caja(ax, x, 1.73, 4.58, 2.2, FONDO)
        texto(ax, x+.2, 3.58, titulo, 10.5, VERDE, peso="bold")
        texto(ax, x+.2, 3.2, subtitulo, 9.5, VIOLETA)
        texto(ax, x+.2, 2.76, a, 9.5, SECUNDARIO)
        texto(ax, x+.2, 2.37, b, 9.1, SECUNDARIO)
        texto(ax, x+.2, 1.98, c, 9.5, SECUNDARIO)
    flecha(ax, 5.24, 2.86, 5.7, 2.86, VERDE)
    flecha(ax, 10.3, 2.86, 10.76, 2.86, VERDE)
    caja(ax, .65, .67, 14.7, .65, "#EAF6F2", "#B8DFD3")
    texto(ax, 8, 1.0, "EVIDENCIA ARCHIVADA  ·  rojo 84443a4 → corrección 30a764b → release 0ec86bb: QA 8/8 y 19/19; Producción 12/12", 10, VERDE, ha="center")
    texto(ax, .65, .3, "Límite detectado: el verificador consulta tags cargados; comprobar el Image ID del contenedor activo aún es un paso manual. Ver auditoría.", 9, AMBAR)
    guardar(fig, "diagrama_promocion")

if __name__ == "__main__":
    arquitectura()
    promocion()
