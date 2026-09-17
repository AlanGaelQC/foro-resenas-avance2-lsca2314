variable "region_aws" {
  description = "Region de AWS Academy donde viven el bucket y la base."
  type        = string
  default     = "us-east-1"
}

variable "nombre_proyecto" {
  description = "Prefijo de nombres de recursos."
  type        = string
  default     = "foro-resenas"
}

variable "entorno" {
  description = "Entorno que forma parte del nombre de los recursos."
  type        = string
  default     = "qa"
}

variable "nombre_bucket" {
  description = "Nombre global del bucket de adjuntos (debe ser unico en AWS)."
  type        = string
}

variable "id_vpc" {
  description = "VPC donde estan la instancia EC2 y la base de datos."
  type        = string
}

variable "ids_subredes_base" {
  description = "Subredes para el grupo de subredes de RDS (minimo dos zonas)."
  type        = list(string)
}

variable "sg_instancia_aplicacion" {
  description = <<-DESCRIPCION
    Id del security group de la instancia EC2 que corre los contenedores.
    La base solo acepta conexiones desde este grupo: asi se cumple
    "alcanzable unicamente desde tu instancia" sin abrir la base a Internet.
  DESCRIPCION
  type        = string
}

variable "usuario_base_datos" {
  description = "Usuario maestro de la base."
  type        = string
  default     = "foro_admin"
}

variable "contrasena_base_datos" {
  description = <<-DESCRIPCION
    Contrasena maestra de la base. Sin default a proposito: se entrega por
    variable de entorno TF_VAR_contrasena_base_datos y nunca se escribe en el
    repositorio. Recuerda que el archivo de estado de Terraform guarda este
    valor en claro: mantenlo fuera de git (.gitignore ya lo excluye).
  DESCRIPCION
  type        = string
  sensitive   = true
}

variable "version_motor" {
  description = "Version del motor PostgreSQL disponible en tu cuenta de AWS Academy (confirmala con: aws rds describe-db-engine-versions --engine postgres)."
  type        = string
}

variable "clase_instancia_base" {
  description = "Clase de instancia RDS permitida en el Learner Lab."
  type        = string
  default     = "db.t3.micro"
}
