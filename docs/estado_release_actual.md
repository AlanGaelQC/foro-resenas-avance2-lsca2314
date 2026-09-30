# Estado de la release verificada — Pulso Pixel

Resultados documentados el 27 de septiembre de 2026. Este registro resume evidencia histórica sin direcciones de red, identificadores de infraestructura ni credenciales. No constituye una consulta en vivo de AWS.

| Control | Resultado |
|---|---|
| Código aprobado | `a2123c5ee46aed07dc066bb8cfd3ff62241f9184`, etiqueta `qa-verde-imagenes-a2123c5`. |
| QA | Pipeline completo: **8/8 etapas OK**, **27/27 pruebas** y árbol limpio. [Veredicto](../reportes/entrega_final/veredicto_imagenes_a2123c5.json) · [Pruebas](../reportes/entrega_final/pruebas_imagenes_a2123c5.txt). |
| Promoción | Se transfirieron los artefactos examinados en QA sin reconstruirlos en el destino. [Manifiesto](../reportes/entrega_final/manifest_imagenes_a2123c5.json). |
| Producción | Checkout, imágenes cargadas, contenedores activos y saludables, RDS, S3 y flujos HTTP contrastados con el manifiesto; imagen publicada visible sin sesión. [Verificación: 16/16](../reportes/entrega_final/verificacion_produccion_imagenes_a2123c5.log). |
| Respaldo anterior | Se conservan en el destino los tar y el manifiesto de `8d1b742` para reversión; las evidencias históricas siguen archivadas. |

Tras una promoción anterior se respaldaron privadamente los datos de prueba de QA y se eliminaron **75 publicaciones y 45 comentarios** identificados por cuenta y patrón de título. Quedaron cuatro publicaciones ajenas a esas pruebas y los **17 adjuntos privados de prueba**. Las corridas posteriores del pipeline volvieron a generar datos de prueba en QA. La base de Producción no intervino en aquella limpieza.

El diseño vigente se llama **Pulso Pixel** y usa arte arcade original, imágenes de reseñas publicadas, miniaturas compactas en «Mis publicaciones» y vista compacta para reseñas largas. El formulario impide reenviar la misma solicitud y exige 10 caracteres útiles en el cuerpo. Los commits que archivan evidencias son posteriores al commit aprobado; no sustituyen su veredicto ni los identificadores de las imágenes.

**Revisión posterior:** se reprodujeron huecos en las exclusiones de secretos,
la identificación automática de contenedores activos, la protección del destino
de las pruebas QA y la aserción de comentarios T11. El
[informe del 27 de septiembre](auditoria/revision_final_2026-09-27.md) contiene
pruebas aisladas y criterios de cierre. Los parches superaron la corrida completa de QA y la verificación reforzada en Producción; esto no implica que las releases anteriores incumplieran sus propios controles.

**Release actual:** imágenes públicas de reseñas y mejoras del formulario siguieron un ciclo QA → veredicto verde → promoción → verificación del destino, registrado en las evidencias de `a2123c5`. La evidencia histórica de `8d1b742` solo certifica aquella release.

**Estado del documento académico:** la plantilla oficial se completó por separado
con siete capturas, autoevaluación y respuestas personales para subirla en la
plataforma; ese documento no forma parte de este repositorio. La declaración
de uso de IA está completa en [declaracion_ia.md](declaracion_ia.md).

**Límite de verificación:** los registros 27/27 y 16/16 prueban los controles
indicados para la release `a2123c5`, pero no certifican el estado actual de AWS
ni sustituyen la comprobación en vivo de cifrado y reglas de acceso señalada
en el [informe de auditoría](auditoria/revision_final_2026-09-27.md).
