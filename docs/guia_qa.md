# Ejecución en QA · orden y evidencia

**Estado:** corridas del parche, detección, remediación y vista pública observadas en QA; aún falta validar el candidato completo para empaquetar. Todos los comandos se ejecutan en la **instancia QA del Avance 2**, con la misma base de datos persistente; no borres usuarios ni datos para conseguir un verde.

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

**Evidencia observada en QA, 2026-09-25 22:17–22:18 UTC:** sobre `84443a4` y con la aplicación vulnerable aún en ejecución, la corrida completa devolvió código 1 y `BLOQUEADO`: 04 marcó un `ERROR` de Semgrep y 08 falló solo en T10d (17/18 pruebas pasaron; el moderador inició sesión y obtuvo la vista previa de la reseña guardada por otra persona). Archivo: `reportes/corridas/20260925T221825549474340Z-bloqueado/`. El veredicto también conserva el defecto temporal del campo `arbol` descrito arriba. No se promueve este commit.

**Contención comprobada en QA, 2026-09-25 22:26:37 UTC:** con la versión vulnerable aún desplegada, se respaldó el entorno en un archivo privado fuera del repositorio, se dejó `MODERADORES=` vacío y se recreó `api`. Los contenedores quedaron sanos; la cuenta del moderador inició sesión (HTTP 303) y la solicitud de vista previa obtuvo HTTP 403. Conservar la captura de esta comprobación. Primero instala y verifica la imagen remediada de `moderador`; solo entonces restaura la lista y recrea `api` para recuperar la vista previa.

**Remediación comprobada en QA, 2026-09-25 22:40–22:41 UTC:** después de instalar el renderizador seguro en `30a764b` y restaurar la lista de moderadores, las ocho etapas terminaron `OK`, el pipeline devolvió código 0 y `PERMITIDO`, y pasaron 18/18 pruebas, incluidas T10d y T10e. Carpeta: `reportes/corridas/20260925T224110120081948Z-permitido/`. El registro aún indicó incorrectamente que había cambios locales, aunque Git terminó limpio.

**Vista pública comprobada en QA, 2026-09-25 23:57–23:59 UTC:** en `ca2529a` el servicio respondió HTTP 200, RDS y S3 estaban disponibles; el pipeline completo terminó con ocho etapas `OK`, código 0 y `PERMITIDO`. Pasaron 19/19 pruebas, incluida T11 (tres comentarios en portada) y T10d (XSS escapada). Carpeta: `reportes/corridas/20260925T235905408924320Z-permitido/`. El registro volvió a indicar cambios locales durante la limpieza temporal de SBOM; Git terminó limpio. **Aún falta** probar el HEAD completo, con el arreglo del registro y los controles de identidad de imágenes, para autorizar la promoción.

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

**Pendiente:** `[PENDIENTE-QA]` Instance ID, saldo, IAM y SG; verificar el verde del candidato completo, exportar imágenes y capturar su identidad. Los reportes descritos arriba son corridas observadas; no se asignan datos de AWS que aún no se hayan comprobado.
