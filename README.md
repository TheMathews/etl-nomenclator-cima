# 💊 ETL / ELT Nomenclátor CIMA (AEMPS) - Oracle & Python

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle%20DB-19c%20%7C%2021c-F80000?logo=oracle&logoColor=white)
![python-oracledb](https://img.shields.io/badge/Driver-python--oracledb-orange)

Motor de integración de datos (ETL/ELT) robusto, escalable y tolerante a fallos desarrollado en Python para procesar de forma masiva el Nomenclátor de medicamentos de la Agencia Española de Medicamentos y Productos Sanitarios (AEMPS).

---

## 🚀 Características Principales

* **Streaming Perezoso (Lazy Streaming):** Emplea generadores de Python (`xml.etree.ElementTree.iterparse` y `xmlschema`) para leer ficheros XML gigantescos de cientos de megabytes nodo a nodo, manteniendo un consumo de RAM extremadamente estable.
* **Arquitectura ELT (Extract, Load, Transform):** Python actúa como un orquestador ligero encargado de la extracción y el volcado ciego masivo (`bulk_insert`) en tablas de *Staging*. Toda la transformación pesada y cruce relacional se delega de forma nativa al motor de base de datos Oracle mediante scripts SQL.
* **Idempotencia Lógica y de Ficheros:** Calcula hashes SHA-256 globales del ZIP y hashes lógicos de contenido para evitar procesar ficheros idénticos si no hay cambios en el origen.
* **Sincronización Multi-Esquema:** Incluye un replicador automatizado que clona las tablas maestras resultantes al resto de esquemas (clientes/hospitales) en el servidor Oracle, restaurando claves primarias, índices y metadatos.
* **Monitorización con Telemetría Enriquecida:** Un módulo auditor evalúa la salud diaria del proceso (patrón *"No news is good news"*) y envía alertas HTML que incorporan métricas de hardware del servidor (OS, RAM, CPU, IP Local)[cite: 3].
* **Evasión Anti-Scraping:** Inyecta dinámicamente cabeceras HTTP de navegador (`User-Agent`) para evitar bloqueos institucionales (Error 403) al descargar los paquetes ZIP y esquemas XSD[cite: 3].

---

## 🏗️ Estructura del Proyecto

```text
ETL_Nomenclator_To_Oracle/
├── config/
│   ├── config.json         # Configuración centralizada y metadatos de tablas
│   └── credenciales.json   # Parámetros de conexión a Oracle y servidor SMTP
├── module/                 # Clases core del sistema (Extractor, XML Handler, Oracle Client, etc.)
├── sql/                    # Scripts de lógica relacional (Staging, Insert, Drop Logic, Update)
├── templates/              # Plantillas HTML para correos de alerta y monitorización
├── utils/                  # Utilidades de log rotatorio y operaciones I/O
├── main.py                 # Orquestador principal de la ETL
├── replicador.py           # Sincronizador de esquemas Oracle
└── monitor.py              # Auditor de calidad y emisor de alertas proactivas