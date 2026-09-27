# Estado de la release vigente — Pulso Pixel v2

Actualizado el 26 de septiembre de 2026. Este registro resume resultados observados sin incluir direcciones de red, identificadores de infraestructura ni credenciales.

| Control | Resultado |
|---|---|
| Código aprobado | `0ec86bb5498fc8f91090edf3ec4e77498586644d`, etiqueta `qa-verde-pulso-pixel-v2-0ec86bb`. |
| QA | Pipeline completo: **8/8 etapas OK**, **19/19 pruebas** y árbol limpio. [Log](../reportes/pipeline_verde_pulso_pixel_v2.txt) · [Veredicto](../reportes/entrega_final/veredicto_pulso_pixel_v2.json). |
| Promoción | Se transfirieron las dos imágenes examinadas en QA sin reconstruirlas en el destino. [Manifiesto](../reportes/entrega_final/manifest_pulso_pixel_v2.json). |
| Producción | Ambas imágenes coinciden con el manifiesto; API y moderador están sanos. [Verificación original del destino: 12/12](../reportes/entrega_final/verificacion_produccion_pulso_pixel_v2_0ec86bb.log). La portada y el detalle de una reseña existente respondieron HTTP 200. |
| Respaldo anterior | Se conservan los artefactos de las promociones anteriores para reversión; las evidencias históricas siguen archivadas. |

Después del último verde y de la verificación del destino se respaldaron privadamente los datos generados por las pruebas de QA. Se eliminaron de la base de QA **75 publicaciones y 45 comentarios** identificados por cuenta y patrón de título; quedaron cuatro publicaciones ajenas a las pruebas. Los **17 adjuntos privados de prueba** se conservaron para que el respaldo siga siendo recuperable. La base de Producción no intervino en esta limpieza. El pipeline de QA generará nuevos datos de prueba si vuelve a ejecutarse.

El diseño vigente se llama **Pulso Pixel** y usa arte arcade original, una portada de reseñas de videojuegos y una vista compacta para reseñas largas. El commit que archiva evidencias es posterior al commit aprobado; no sustituye su veredicto ni los identificadores de las imágenes.

**Pendiente para la entrega académica:** incorporar capturas actuales de QA y Producción a la plantilla oficial; completar en primera persona la declaración de uso de IA y la autoevaluación. Este archivo no afirma que esas capturas ya estén adjuntas.
