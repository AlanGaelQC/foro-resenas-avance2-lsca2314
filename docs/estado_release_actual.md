# Estado de la release verificada — Pulso Pixel

Resultados documentados el 27 de septiembre de 2026. Este registro resume evidencia histórica sin direcciones de red, identificadores de infraestructura ni credenciales. No constituye una consulta en vivo de AWS.

| Control | Resultado |
|---|---|
| Código aprobado | `8d1b74236fe43913d1a37329bf05860e3b66b479`. |
| QA | Pipeline completo: **8/8 etapas OK**, **21/21 pruebas** y árbol limpio. [Veredicto](../reportes/entrega_final/veredicto_revision_final.json) · [Pruebas](../reportes/entrega_final/08_pruebas_revision_final.txt). |
| Promoción | Se transfirieron los artefactos examinados en QA sin reconstruirlos en el destino. [Manifiesto](../reportes/entrega_final/manifest_revision_final.json). |
| Producción | Checkout, imágenes cargadas, contenedores activos y saludables, RDS, S3 y flujos HTTP contrastados con el manifiesto. [Verificación: 15/15](../reportes/entrega_final/verificacion_produccion_revision_final_8d1b742.log). |
| Respaldo anterior | Se conservan los artefactos de las promociones anteriores para reversión; las evidencias históricas siguen archivadas. |

Tras una promoción anterior se respaldaron privadamente los datos de prueba de QA y se eliminaron **75 publicaciones y 45 comentarios** identificados por cuenta y patrón de título. Quedaron cuatro publicaciones ajenas a esas pruebas y los **17 adjuntos privados de prueba**. Las corridas posteriores del pipeline volvieron a generar datos de prueba en QA. La base de Producción no intervino en aquella limpieza.

El diseño vigente se llama **Pulso Pixel** y usa arte arcade original, una portada de reseñas de videojuegos y una vista compacta para reseñas largas. Los commits que archivan evidencias son posteriores al commit aprobado; no sustituyen su veredicto ni los identificadores de las imágenes.

**Revisión posterior:** se reprodujeron huecos en las exclusiones de secretos,
la identificación automática de contenedores activos, la protección del destino
de las pruebas QA y la aserción de comentarios T11. El
[informe del 27 de septiembre](auditoria/revision_final_2026-09-27.md) contiene
pruebas aisladas y criterios de cierre. Los parches superaron la corrida completa de QA y la verificación reforzada en Producción; esto no implica que las releases anteriores incumplieran sus propios controles.

**Candidatos posteriores:** imágenes públicas de reseñas y mejoras del formulario requieren un nuevo ciclo QA → veredicto verde → promoción → verificación del destino. La evidencia de `8d1b742` no certifica los cambios posteriores.

**Pendiente para la entrega académica:** comprobar las
configuraciones vivas de AWS indicadas en el informe, incorporar capturas de QA
y Producción a la plantilla oficial, y completar en primera persona la
declaración de uso de IA y la autoevaluación. Este archivo no afirma que esas
capturas ya estén adjuntas.
