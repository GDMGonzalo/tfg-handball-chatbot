# Sistema Conversacional Inteligente para Análisis Estadístico en Balonmano

Repositorio asociado al Trabajo de Fin de Grado **“Sistema Conversacional Inteligente para Análisis Estadístico en Balonmano Basado en LLM y Datos Estructurados”**.

El proyecto parte de la aplicación base *handballAnalytics*, proporcionada por los tutores, y añade un módulo conversacional para consultar estadísticas de balonmano mediante lenguaje natural.

## Estructura del repositorio

* `app-tfg/`: código principal de la aplicación.
* `app-tfg/app/`: aplicación Flask.
* `app-tfg/app/services/`: servicios principales de la aplicación, incluyendo los módulos del chatbot.
* `app-tfg/app/routes/`: rutas de la aplicación web.
* `app-tfg/app/templates/`: plantillas HTML.
* `app-tfg/app/static/`: recursos estáticos.
* `app-tfg/restore.sql`: script SQL de restauración/base de datos utilizado en el proyecto.
* `documents/`: documentación incluida en el repositorio base.
* `CONTRIBUTING.md`: instrucciones generales de trabajo del repositorio base.

## Parte correspondiente al proyecto base

La aplicación base *handballAnalytics* fue proporcionada por los tutores del TFG. Esta base incluye la estructura general de la aplicación web, autenticación, modelos, rutas, plantillas y funcionalidades previas para la gestión de datos deportivos.

## Parte desarrollada en este TFG

La contribución principal de este TFG corresponde al diseño, implementación e integración del chatbot estadístico dentro de *handballAnalytics*.

Los archivos principales desarrollados o modificados se encuentran en:

```text
app-tfg/app/services/
```

En concreto:

* `chatbot_service.py`: orquesta el flujo del chatbot, decide el tipo de consulta y coordina parser, SQL y SLM.
* `chatbot_parser.py`: normaliza el texto y detecta equipos, jugadores, contexto y errores tipográficos leves.
* `chatbot_queries.py`: contiene las consultas SQL para obtener estadísticas, rankings, zonas de tiro y datos de jugadores.
* `chatbot_slm.py`: gestiona la comunicación con el modelo de lenguaje local ejecutado mediante Ollama.
* - `chatbot_routes.py`: define las rutas Flask del módulo de chatbot, muestra la interfaz y expone el endpoint que recibe la pregunta del usuario y devuelve la respuesta generada.

## Funcionalidades del chatbot

El chatbot permite realizar consultas en lenguaje natural sobre:

* estadísticas básicas de equipos;
* estadísticas individuales de jugadores;
* rankings de equipos y jugadores;
* comparativas;
* goles anotados y recibidos;
* zonas de tiro;
* porcentaje de uso y porcentaje de acierto;
* consultas con errores tipográficos leves.

Ejemplos de consultas soportadas:

```text
¿Cuántas victorias tiene X equipo?
Dame los 3 jugadores con más goles.
Dame los 5 equipos con más goles recibidos.
Dame los 5 equipos con menos goles anotados.
¿Qué equipo tira más desde 6m?
Distribución de tiro de X equipo.
¿Cuántas asistencias tiene X jugador?
```

## Tecnologías principales

* Python
* Flask
* SQLAlchemy
* MySQL / MariaDB
* Ollama
* Modelos SLM locales

## Autor

Gonzalo Delgado Martín
Grado en Ingeniería de Computadores
Universidad de Málaga
