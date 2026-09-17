########################################
# Almacenamiento de adjuntos (S3)
########################################

# Bucket de los adjuntos de las resenas. Privado: la aplicacion entrega las
# imagenes con URL prefirmada, nunca por URL publica.
resource "aws_s3_bucket" "adjuntos" {
  bucket = var.nombre_bucket

  tags = {
    Proyecto = var.nombre_proyecto
    Entrega  = "avance2"
  }
}

# Bloqueo total de acceso publico: los cuatro interruptores, no solo uno.
resource "aws_s3_bucket_public_access_block" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Cifrado en reposo del lado del servidor.
resource "aws_s3_bucket_server_side_encryption_configuration" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Versionado: si un adjunto se sobrescribe o se borra por error queda la version
# anterior. En un foro tambien ayuda a investigar contenido retirado.
resource "aws_s3_bucket_versioning" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Solo se aceptan peticiones por TLS: sin esto, un PUT por HTTP plano viajaria
# sin cifrar aunque el bucket este cifrado en reposo.
resource "aws_s3_bucket_policy" "solo_tls" {
  bucket = aws_s3_bucket.adjuntos.id
  policy = data.aws_iam_policy_document.solo_tls.json

  depends_on = [aws_s3_bucket_public_access_block.adjuntos]
}

data "aws_iam_policy_document" "solo_tls" {
  statement {
    sid     = "NegarTransporteInseguro"
    effect  = "Deny"
    actions = ["s3:*"]

    resources = [
      aws_s3_bucket.adjuntos.arn,
      "${aws_s3_bucket.adjuntos.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

# Los adjuntos rechazados o huerfanos no se acumulan indefinidamente.
resource "aws_s3_bucket_lifecycle_configuration" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  rule {
    id     = "expirar-versiones-viejas"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

########################################
# Base de datos (RDS PostgreSQL)
########################################

# La base solo acepta trafico del security group de la instancia que corre los
# contenedores. No hay regla con 0.0.0.0/0 en ningun puerto.
resource "aws_security_group" "base_datos" {
  name        = "${var.nombre_proyecto}-sg-base"
  description = "Acceso a PostgreSQL unicamente desde la instancia de la aplicacion"
  vpc_id      = var.id_vpc

  tags = {
    Proyecto = var.nombre_proyecto
  }
}

resource "aws_vpc_security_group_ingress_rule" "postgres_desde_aplicacion" {
  security_group_id            = aws_security_group.base_datos.id
  description                  = "PostgreSQL desde la instancia de la aplicacion"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = var.sg_instancia_aplicacion
}

resource "aws_vpc_security_group_egress_rule" "salida_base" {
  security_group_id = aws_security_group.base_datos.id
  description       = "Salida necesaria para respuestas y actualizaciones gestionadas"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_db_subnet_group" "base_datos" {
  name       = "${var.nombre_proyecto}-subredes"
  subnet_ids = var.ids_subredes_base

  tags = {
    Proyecto = var.nombre_proyecto
  }
}

resource "aws_db_instance" "foro" {
  identifier     = "${var.nombre_proyecto}-${var.entorno}"
  engine         = "postgres"
  engine_version = var.version_motor
  instance_class = var.clase_instancia_base

  allocated_storage = 20
  storage_type      = "gp3"
  # Cifrado en reposo: requisito explicito del Avance 2.
  storage_encrypted = true

  db_name  = "foro"
  username = var.usuario_base_datos
  password = var.contrasena_base_datos

  # Sin IP publica: la base no es alcanzable desde Internet.
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.base_datos.name
  vpc_security_group_ids = [aws_security_group.base_datos.id]

  # Respaldo y trazabilidad.
  backup_retention_period         = 7
  copy_tags_to_snapshot           = true
  auto_minor_version_upgrade      = true
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  # Proteccion de borrado activada, y snapshot final al destruir: en un entorno
  # de clase es facil perder datos con un 'terraform destroy' distraido.
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.nombre_proyecto}-snapshot-final"

  # IAM database authentication: permite conectarse con credenciales temporales
  # de IAM ademas de la contrasena maestra.
  iam_database_authentication_enabled = true

  tags = {
    Proyecto = var.nombre_proyecto
    Entrega  = "avance2"
  }
}
