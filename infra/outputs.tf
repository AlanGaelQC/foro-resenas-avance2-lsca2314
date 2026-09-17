output "nombre_bucket_adjuntos" {
  description = "Bucket que usa la aplicacion para los adjuntos de las resenas."
  value       = aws_s3_bucket.adjuntos.bucket
}

output "punto_conexion_base" {
  description = "Host de la base de datos. Se combina con la contrasena (que no sale de aqui) para armar URL_BASE_DATOS."
  value       = aws_db_instance.foro.address
}

output "sg_base_datos" {
  description = "Security group aplicado a la base de datos."
  value       = aws_security_group.base_datos.id
}
