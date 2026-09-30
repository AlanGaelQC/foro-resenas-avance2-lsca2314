# Declaración de uso de IA — Entrega Final

## Herramientas utilizadas

Usé ChatGPT/Codex y Claude como apoyo durante el proyecto. Les compartí los
andamios, las instrucciones, la plantilla y el parche del maestro para trabajar
sobre los requisitos reales de la entrega. Pedí ayuda para desarrollar la
aplicación, entender la falla, ampliar el pipeline, preparar las pruebas y
redactar la documentación.

## Qué hizo la IA y qué hice yo

Las herramientas propusieron y generaron una parte importante del código, las
pruebas, los comandos y los borradores del documento. No presento todo eso como
si lo hubiera escrito manualmente sin ayuda. También les pedí revisiones
críticas: cuando una encontraba un posible error, yo le pasaba ese resultado a
la otra para contrastar las respuestas. Claude y ChatGPT/Codex no conversaron
directamente entre sí.

Yo dirigí el proceso: indiqué qué quería que hiciera el foro, decidí los cambios
de diseño y funcionamiento, compartí las salidas reales y pedí correcciones
cuando algo falló o no coincidía con lo esperado. Ejecuté los pasos en mis
instancias de QA y Producción y comprobé los resultados antes de seguir. Por
ejemplo, no di por buena la promoción solo porque apareciera la palabra
`PERMITIDO`: revisé a qué commit correspondía el veredicto, las pruebas y las
imágenes transferidas.

## Verificación personal

Comprobé que el pipeline original dejó pasar el parche vulnerable porque aún no
tenía un control para esa vista previa construida en Python. Después de añadir
la regla de Semgrep y la prueba HTTP, repetí la corrida con la falla presente y
la promoción quedó bloqueada. El arreglo cambió la vista previa para escapar el
texto del usuario antes de aplicar el formato permitido.

En la release final comprobé ocho etapas en verde y 27/27 pruebas en QA. Para
Producción se cotejaron el commit, los hashes de los archivos y los
identificadores de imagen con el manifiesto; el verificador terminó 16/16. Los
reportes se conservan en `reportes/`. La prueba de XSS examinó el HTML de la
respuesta: no ejecutó JavaScript en un navegador ni demuestra que hubiera
ocurrido un ataque real en Producción.

## Lo que me costó

Lo más difícil de entender fue por qué el pipeline decía `PERMITIDO` cuando el
parche todavía tenía una falla. Aprendí que ese veredicto solo cubría las reglas
y pruebas que existían en ese momento. En un sistema real con usuarios,
restringiría primero la vista previa afectada, conservaría los registros y
avisaría a quienes operan el servicio. Después evaluaría si conviene volver a
una versión anterior y probaría la corrección en QA antes de actualizar
Producción.

Esta declaración fue redactada con ayuda de IA y revisada para reflejar mi
participación y los límites de lo que se comprobó.
