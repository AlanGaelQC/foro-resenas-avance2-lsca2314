# Declaración de uso de IA

Foro y reseñas · LSCA2314 · El Reto, Avance 2
Autor: [COMPLETAR: tu nombre completo]

> **Antes de entregar:** este archivo tiene dos partes. La primera es un
> registro de hechos que puedes verificar contra el repositorio y el historial
> de git. La segunda son preguntas que **solo tú puedes contestar**: lo que
> revisaste, lo que corregiste y lo que entendiste. No las dejes sin llenar ni
> las respondas con algo que no hiciste — el profesor va a preguntar por estas
> decisiones en la calificación, y la respuesta tiene que ser tuya.
> Borra este recuadro antes de entregar.

## 1. Qué herramientas de IA usé

| Herramienta | Para qué |
|---|---|
| [COMPLETAR: nombre y versión del asistente] | [COMPLETAR: ej. generar el primer borrador del código, revisar decisiones, redactar documentación] |

## 2. En qué partes del proyecto se usó IA

Registro de hechos. **Verifícalo** contra el repositorio y ajústalo si algo no
corresponde a cómo trabajaste:

| Parte | Cómo se generó | Qué falta que confirmes tú |
|---|---|---|
| `app/api/` (API del foro) | Borrador generado con asistencia de IA a partir de los requisitos del Avance 2 | [COMPLETAR: qué leíste, qué cambiaste, qué no te convencía] |
| `app/moderador/` (servicio de moderación) | Borrador generado con asistencia de IA; las reglas de moderación se definieron para este tema | [COMPLETAR: ¿ajustaste el léxico o los umbrales? ¿probaste casos propios?] |
| `Dockerfile`, `Dockerfile.moderador`, `docker-compose.yml` | Borrador con asistencia de IA siguiendo los requisitos de endurecimiento | [COMPLETAR: ¿los construiste y levantaste tú? ¿qué falló la primera vez?] |
| `infra/*.tf` | Borrador con asistencia de IA; ajustado tras correr checkov | [COMPLETAR: ¿comparaste el .tf con lo que creaste en la consola de AWS?] |
| `pipeline/` (8 etapas + orquestador) | Diseño y scripts con asistencia de IA; umbrales y exclusiones discutidos control por control | [COMPLETAR: ¿puedes explicar por qué cada etapa tiene ese umbral? Si no, repásalo antes de entregar] |
| `pipeline/reglas_semgrep_foro.yml` | Reglas escritas para este foro con asistencia de IA | [COMPLETAR: ¿entiendes qué detecta cada una de las 7 reglas?] |
| `docs/` | Borradores con asistencia de IA a partir de las decisiones tomadas | [COMPLETAR: ¿revisaste que lo escrito corresponde con lo que entregas?] |

## 3. Qué NO delegué

[COMPLETAR. Aquí va lo que hiciste tú y no podría haber hecho la IA. Por
ejemplo, si aplica: crear el bucket y la base en tu cuenta de AWS Academy,
decidir el tema, decidir qué controles bloquean y cuáles no, correr el pipeline
en tu instancia, grabar el video, revisar que la documentación corresponda con
lo entregado.]

## 4. Errores o problemas que encontré y cómo los corregí

[COMPLETAR con lo que realmente te pasó. Ejemplos del tipo de cosa que va aquí:
una herramienta que no instalaba, un contenedor que no levantaba, un hallazgo
del pipeline que tuviste que arreglar, una diferencia entre lo que decía el
código y lo que hacía. Si la IA se equivocó en algo y lo corregiste, este es el
lugar para decirlo.]

## 5. Qué aprendí y qué puedo defender

[COMPLETAR. Concretamente: ¿puedes explicar sin ayuda por qué tu pipeline
bloquea, qué hace cada etapa, y por qué elegiste esos umbrales? ¿Qué parte te
costó más entender?]

## 6. Declaración

Declaro que entiendo el código y las decisiones que entrego, que puedo
explicarlas y defenderlas, y que las evidencias incluidas
(`reportes/corrida_roja.txt`, `reportes/corrida_verde.txt`, capturas y video)
son resultados reales obtenidos en mi propio entorno.

Firma: [COMPLETAR: nombre] · Fecha: [COMPLETAR]
