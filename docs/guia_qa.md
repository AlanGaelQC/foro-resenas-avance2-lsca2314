# Ejecución en QA · orden y evidencia

**Estado:** procedimiento preparado; las salidas con `[PENDIENTE-QA]` se sustituyen al operar la EC2 existente. Todos los comandos se ejecutan en la **instancia QA del Avance 2**, con la misma base de datos persistente; no borres usuarios ni datos para conseguir un verde.

## Antes de actualizar QA

1. Conserva dos capturas del sistema vigente: portada y detalle. Guarda Instance ID, hora local, commit desplegado, `docker compose ps`, espacio y memoria disponibles. Confirma qué valores siguen disponibles si la sesión Learner Lab caducó; renueva credenciales cuando haga falta, sin recrear recursos automáticamente.
2. Asegura una rama `entrega-final` que contiene estos commits desde `430fc6a`. Si solo tienes el bundle, sobre un clon cuyo `main` esté exactamente en `430fc6a`: `git fetch /ruta/entrega_final_integrado.bundle refs/heads/entrega-final:refs/heads/entrega-final`. Confirma `git log --oneline main..entrega-final`. Si el remoto cambió, detente antes de mezclar historias.
3. Prepara `.env` de QA (sin publicarlo): conserva los valores RDS/S3 originales y añade `MODERADORES` y una contraseña aleatoria `MODERADOR_PASS`. La cuenta no debe corresponder a un usuario antiguo de procedencia desconocida. No uses `CAMBIA_ESTE_VALOR`. Comprueba permisos de lectura del archivo y credenciales AWS de la instancia. `MODERADOR_PRUEBA` en `.env` es opcional; si falta, la etapa 08 toma el primer correo de `MODERADORES`.
4. Ejecuta `bash pipeline/preparar_herramientas.sh` si faltan herramientas. Reserva espacio suficiente: se construirán dos imágenes y se archivan reportes. No pegues `.env`, contraseñas o URLs prefirmadas en las evidencias.

## Corridas en orden

Cada cambio de commit requiere **reconstruir ambas imágenes y reiniciar** antes del pipeline:

```bash
docker compose build
docker compose up -d
docker compose ps
bash pipeline/orquestador.sh
```

El orquestador ejecuta ocho etapas y crea `reportes/veredicto.json` y `reportes/corridas/<fecha>-<veredicto>/`. Guarda fuera del directorio que sobrescribe la siguiente corrida el nombre exacto de esa carpeta y el commit. Un retorno 1 puede significar **HALLAZGO** o **ERROR_OPERATIVO**: identifica cuál en los reportes. Un escáner que no corrió no demuestra la XSS.

**Evidencia observada en QA, 2026-09-25 21:55–21:57 UTC:** sobre el commit vulnerable `215be19`, la corrida completa devolvió código 0 y `PERMITIDO`: las ocho etapas figuraron `OK`, incluidas 04 y 08. Archivo: `reportes/corridas/20260925T215712762170233Z-permitido/`. Esto acredita una brecha de cobertura del pipeline previo, **no** la seguridad del parche. El veredicto anotó `arbol: CON CAMBIOS SIN CONFIRMAR` aunque `git status` estaba limpio antes y después: el orquestador borraba temporalmente los SBOM versionados antes de medir el árbol y la etapa 07 los regeneraba idénticos. La corrección del registro se incorpora en un commit posterior; no se altera la evidencia histórica de esta corrida.

| Orden | Checkout en la rama local | Qué observar y registrar |
|---|---|---|
| 1 | `git switch --detach 215be19` | Parche del profesor vivo. Corre el **pipeline original** antes de añadir detección. Registra si pasa por una brecha real o se bloquea por otra causa. No promuevas aunque diga PERMITIDO. |
| 2 | `git switch --detach 84443a4` | Regla Semgrep y T10d contra la reseña de un autor distinto del moderador. La corrida debe terminar BLOQUEADO por la XSS, con etapas 04 y/u 08 que lo demuestren. |
| 3 | `git switch --detach 30a764b` | El formato seguro debe escapar `<script>` y conservar `<b>` y `<br>`. La detección XSS debe pasar. Este verde intermedio no autoriza producción porque falta la vista pública. |
| 4 | `git switch entrega-final` | Candidato completo: portada paginada y tres comentarios por reseña, T11, SBOM por servicio e identidad de las imágenes. Ejecuta el pipeline completo y guarda el **verde final** de ocho etapas sobre este HEAD. |

En cada paso verifica que `git status --short` está limpio. El script `pipeline/promover.sh` solo debe ejecutarse tras el último verde; guarda el manifiesto y las imágenes exportadas para transferir a la EC2 nueva cuando se conozca su inventario. Si cambias código, reconstruyes o cambias etiquetas de imágenes, vuelve a pasar las ocho etapas. Los Image IDs que se empaquetan deben coincidir con `reportes/06_image_ids.json`.

## Capturas y documentos

- Captura **antes** (QA Avance 2), la vista vulnerable limitada al moderador y el **después** público y moderado. Para portada, prepara ejemplos con 0, 1, 3 y 4 comentarios; la tarjeta nunca muestra más de tres, el detalle muestra todos.
- Conserva la carpeta de la corrida original, la bloqueada y la verde, junto a `veredicto.json`, las salidas 04/08, el commit y los dos Image IDs. No sobrescribas el rojo con el verde.
- Completa `docs/clasificacion_hallazgo.md` y `docs/respuesta_incidente.md` con la etapa real, exit code y rutas de los archivos. La contención puede retirar temporalmente `MODERADORES`; la corrección es escapar el contenido conservando el formato.
- Tras verificar QA, completa la plantilla oficial de evidencias con capturas y enlaces reales. La plantilla de declaración de IA requiere palabras y comprobaciones personales de Alan.

**Pendiente:** `[PENDIENTE-QA]` Instance ID, saldo, IAM, SG, estado de RDS/S3, fechas y veredictos reales. No se asignan valores en este documento antes de ver la instancia.
