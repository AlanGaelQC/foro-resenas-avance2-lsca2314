#!/usr/bin/env bash
# ============================================================================
#  VERIFICADOR PROPIO - NO es el verificar_entrega.sh del profesor
# ============================================================================
#  El documento del Avance 2 menciona un verificar_entrega.sh que se entrega
#  junto con la plantilla de repositorio. Esa plantilla no llego con el
#  material, asi que este archivo es una version propia, escrita a partir de la
#  tabla de entregables del documento. Cuando aparezca el verificador oficial,
#  usa ese: el tuyo no lo sustituye.
#
#  Comprueba que la entrega este completa. No califica la calidad.
#
#  Uso:  bash verificar_entrega_extendido.sh
# ============================================================================

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

TOTAL=0
BIEN=0
FALTANTES=()

revisar() {
  # revisar <descripcion> <condicion>
  TOTAL=$((TOTAL + 1))
  if eval "$2" > /dev/null 2>&1; then
    echo "  [OK] $1"
    BIEN=$((BIEN + 1))
  else
    echo "  [  ] $1"
    FALTANTES+=("$1")
  fi
}

echo "============================================================"
echo " Verificacion de la entrega - Avance 2 (verificador propio)"
echo "============================================================"
echo ""
echo "Codigo y orquestacion"
revisar "app/ con el codigo de la aplicacion"          "[ -d app/api ] && [ -d app/moderador ]"
revisar "Dockerfile de la API"                          "[ -f Dockerfile ]"
revisar "Dockerfile del segundo servicio"               "[ -f Dockerfile.moderador ]"
revisar "docker-compose.yml con dos servicios propios"  "grep -q 'moderador:' docker-compose.yml && grep -q 'api:' docker-compose.yml"
revisar "Imagen base con version fija (no :latest)"     "! grep -qE '^FROM .*:latest' Dockerfile Dockerfile.moderador"
revisar "Los contenedores no corren como root"          "grep -q '^USER ' Dockerfile && grep -q '^USER ' Dockerfile.moderador"
revisar "Los dos Dockerfile tienen HEALTHCHECK"         "grep -q 'HEALTHCHECK' Dockerfile && grep -q 'HEALTHCHECK' Dockerfile.moderador"
revisar "Endpoint /salud en el codigo"                  "grep -rq '/salud' app/api"

echo ""
echo "Infraestructura como codigo"
revisar "infra/ con archivos .tf"                       "ls infra/*.tf"
revisar "El .tf describe el bucket de S3"               "grep -rq 'aws_s3_bucket' infra/"
revisar "El .tf describe la base de datos"              "grep -rq 'aws_db_instance' infra/"
revisar "RDS cifrada en el .tf"                         "grep -rq 'storage_encrypted *= *true' infra/"
revisar "RDS sin acceso publico en el .tf"              "grep -rq 'publicly_accessible *= *false' infra/"
revisar "Bloqueo de acceso publico del bucket"          "grep -rq 'aws_s3_bucket_public_access_block' infra/"

echo ""
echo "Credenciales fuera del repositorio"
revisar ".gitignore excluye .env"                       "grep -qE '^\.env$' .gitignore"
revisar "No hay un .env versionado"                     "! git ls-files --error-unmatch .env"
revisar "Existe .env.ejemplo como plantilla"            "[ -f .env.ejemplo ]"
revisar "El .gitignore excluye el estado de Terraform"  "grep -q 'tfstate' .gitignore"

echo ""
echo "Pipeline"
revisar "pipeline/ con los scripts de control"          "ls pipeline/*.sh"
revisar "Orquestador con la decision final"             "[ -f pipeline/orquestador.sh ]"
revisar "El orquestador imprime un veredicto unico"     "grep -q 'DESPLIEGUE BLOQUEADO' pipeline/orquestador.sh && grep -q 'DESPLIEGUE PERMITIDO' pipeline/orquestador.sh"
revisar "Reglas propias de analisis estatico"           "[ -f pipeline/reglas_semgrep_foro.yml ]"
revisar "Excepciones de IaC justificadas por escrito"   "[ -s pipeline/excepciones_checkov.txt ]"

echo ""
echo "Evidencias"
revisar "reportes/corrida_roja.txt"                     "[ -s reportes/corrida_roja.txt ]"
revisar "La corrida roja realmente bloquea"             "grep -q 'DESPLIEGUE BLOQUEADO' reportes/corrida_roja.txt"
revisar "reportes/corrida_verde.txt"                    "[ -s reportes/corrida_verde.txt ]"
revisar "La corrida verde realmente permite"            "grep -q 'DESPLIEGUE PERMITIDO' reportes/corrida_verde.txt"
revisar "SBOM en formato CycloneDX"                     "[ -s reportes/sbom_cyclonedx.json ] && grep -q 'CycloneDX' reportes/sbom_cyclonedx.json"

echo ""
echo "Documentacion"
revisar "docs/README.md"                                "[ -s docs/README.md ]"
revisar "docs/diagrama_arquitectura.png"                "[ -s docs/diagrama_arquitectura.png ]"
revisar "docs/ADR-001-decisiones-tecnicas.md"           "[ -s docs/ADR-001-decisiones-tecnicas.md ]"
revisar "docs/tabla_decisiones_pipeline.md"             "[ -s docs/tabla_decisiones_pipeline.md ]"
revisar "docs/declaracion_uso_ia.md"                    "[ -s docs/declaracion_uso_ia.md ]"
revisar "Video o enlace al video"                       "[ -s docs/enlace_video.txt ] || ls video/* "

echo ""
echo "Plantillas sin terminar"
revisar "Ningun [COMPLETAR] en docs/README.md"          "! grep -q 'COMPLETAR' docs/README.md"
revisar "Ningun [COMPLETAR] en el ADR"                  "! grep -q 'COMPLETAR' docs/ADR-001-decisiones-tecnicas.md"
revisar "Ningun [COMPLETAR] en la tabla de decisiones"  "! grep -q 'COMPLETAR' docs/tabla_decisiones_pipeline.md"
revisar "Declaracion de uso de IA sin [COMPLETAR]"      "! grep -q 'COMPLETAR' docs/declaracion_uso_ia.md"
revisar "Enlace del video puesto"                       "! grep -q 'COMPLETAR' docs/enlace_video.txt"

echo ""
echo "============================================================"
echo " Resultado: $BIEN / $TOTAL"
echo "============================================================"

if [[ "$BIEN" -eq "$TOTAL" ]]; then
  echo " La entrega esta completa. Falta lo que este verificador no puede"
  echo " comprobar: que el bucket y la base existan de verdad en tu cuenta,"
  echo " y que el video muestre lo que dice mostrar."
  exit 0
fi

echo " Pendientes:"
for faltante in "${FALTANTES[@]}"; do
  echo "   - $faltante"
done
echo ""
echo " Lo que aparece aqui como pendiente simplemente no esta entregado."
exit 1
