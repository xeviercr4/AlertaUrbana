# Alerta Urbana / Smart City IA — Documentación del Proyecto

---

## 1. Problema (Discovery)

En las ciudades latinoamericanas, los ciudadanos enfrentan problemas urbanos cotidianos —baches, acumulación de basura, fugas de agua, fallas en el alumbrado público— y no disponen de un canal ágil para reportarlos. Los mecanismos tradicionales (llamadas telefónicas, oficinas presenciales) son lentos, no priorizan incidentes por gravedad y carecen de trazabilidad. Esto provoca que problemas urgentes (un bache que causa accidentes, una fuga de agua potable) tengan el mismo tratamiento que situaciones menores, desperdiciando recursos municipales y afectando la calidad de vida.

---

## 2. Usuario y contexto

| Aspecto | Detalle |
|---|---|
| **Usuario primario** | Ciudadano común que detecta un problema en la vía pública y desea reportarlo desde su navegador o celular. |
| **Usuario secundario** | Funcionario municipal que revisa los tickets generados para despachar cuadrillas de mantenimiento. |
| **Contexto de uso** | El ciudadano llena un formulario con una descripción en texto libre (español) y opcionalmente adjunta una fotografía como evidencia. El sistema analiza ambos inputs con IA y genera un ticket clasificado y priorizado automáticamente. |

---

## 3. Propuesta de valor

*Alerta Urbana* automatiza tres tareas clave que hoy se hacen manualmente:

1. **Clasificación automática** del tipo de incidente (BASURA, BACHE, ALUMBRADO, AGUA, OTRO) usando análisis de texto e imagen con IA.
2. **Priorización inteligente** basada en el sentimiento del reporte y la presencia de palabras de urgencia ("peligro", "accidente", "urgente").
3. **Generación instantánea de tickets** con ID único, categoría, prioridad y fecha, eliminando burocracia y reduciendo el tiempo de respuesta municipal.

El valor diferenciador: la combinación de **NLP** (análisis de sentimiento + frases clave) y **Computer Vision** (etiquetado de imágenes) permite una clasificación más precisa que la que podría hacer un operador humano procesando cientos de reportes al día.

---

## 4. Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│              (HTML + CSS + JavaScript)                       │
│         index.html  ·  style.css  ·  app.js                │
│                                                             │
│   ┌──────────┐   ┌────────────┐   ┌───────────────────┐    │
│   │ Textarea │   │ Input File │   │ Historial tickets │    │
│   │ (texto)  │   │ (imagen)   │   │   GET /tickets    │    │
│   └────┬─────┘   └─────┬──────┘   └───────────────────┘    │
│        │               │                                    │
│        └───────┬───────┘                                    │
│           FormData (multipart)                              │
│           POST /analizar                                    │
└────────────────┬────────────────────────────────────────────┘
                 │  HTTP (fetch)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND  (FastAPI + Uvicorn)             │
│                         main.py                             │
│                                                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │              POST /analizar                      │       │
│  │                                                  │       │
│  │  1. analizar_sentimiento(texto)  ───────────┐    │       │
│  │  2. extraer_frases_clave(texto)  ───────┐   │    │       │
│  │  3. clasificar_categoria(frases)        │   │    │       │
│  │  4. analizar_imagen_bytes(img)  ──────┐ │   │    │       │
│  │  5. clasificar_por_tags(tags)         │ │   │    │       │
│  │  6. calcular_prioridad()              │ │   │    │       │
│  │  7. generar_ticket()                  │ │   │    │       │
│  │  8. guardar_ticket() → tickets.json   │ │   │    │       │
│  └───────────────────────────────────────┼─┼───┼────┘       │
│                                          │ │   │            │
│              GET /tickets ──► tickets.json (persistencia)   │
└──────────────────────────────────────────┼─┼───┼────────────┘
                                           │ │   │
                          HTTPS REST calls │ │   │
                                           ▼ ▼   ▼
┌─────────────────────────────────────────────────────────────┐
│              AZURE AI SERVICES (Cognitive Services)         │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │  Text Analytics      │  │  Computer Vision             │  │
│  │  v3.1                │  │  Image Analysis 2024-02-01   │  │
│  │                      │  │                              │  │
│  │ • /sentiment         │  │ • /imageanalysis:analyze     │  │
│  │ • /keyPhrases        │  │   ?features=tags             │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
│                                                             │
│            Autenticación: Ocp-Apim-Subscription-Key         │
└─────────────────────────────────────────────────────────────┘
```

**Componentes:**
- **Frontend**: SPA ligera servida estáticamente (HTML/CSS/JS vanilla).
- **Backend**: API REST con FastAPI (Python), ejecutada con Uvicorn.
- **Persistencia**: archivo JSON local (`tickets.json`).
- **Servicios de IA**: Azure AI Services (Text Analytics + Computer Vision), consumidos vía REST con clave de suscripción.

---

## 5. Servicios cognitivos utilizados

| Servicio | API / Endpoint | Propósito en el proyecto |
|---|---|---|
| **Azure Text Analytics – Sentiment Analysis** | `/text/analytics/v3.1/sentiment` | Determina si el tono del reporte ciudadano es *positive*, *neutral* o *negative*. Un sentimiento negativo eleva la prioridad a ALTA. |
| **Azure Text Analytics – Key Phrase Extraction** | `/text/analytics/v3.1/keyPhrases` | Extrae las frases clave del texto (ej. "bache enorme", "fuga de agua") para clasificar automáticamente la categoría del problema. |
| **Azure Computer Vision – Image Analysis (Tags)** | `/computervision/imageanalysis:analyze?features=tags` | Analiza la imagen adjunta y devuelve etiquetas descriptivas (ej. "pothole", "trash", "water"). Se usa como segundo clasificador que complementa o reemplaza la clasificación textual. |

Todos los servicios se consumen bajo un mismo recurso multiservicios de Azure AI (`AZURE_ENDPOINT` + `AZURE_KEY`), autenticados mediante la cabecera `Ocp-Apim-Subscription-Key`.

---

## 6. Uso de Azure AI Foundry

El proyecto utiliza **Azure AI Foundry** (anteriormente Azure AI Services / Cognitive Services) como plataforma unificada para aprovisionar y consumir los modelos de IA:

- **Recurso multiservicios**: un único endpoint (`AZURE_ENDPOINT`) expone tanto Text Analytics como Computer Vision, simplificando la gestión de claves y facturación.
- **Consumo REST directo**: el backend invoca los servicios mediante llamadas HTTP POST con la librería `requests` de Python, sin necesidad de SDKs pesados.
- **Idioma español**: se especifica `"language": "es"` en las solicitudes a Text Analytics, aprovechando el soporte multilingüe de los modelos pre-entrenados de Azure.
- **Análisis de imagen por bytes**: las imágenes se envían como `application/octet-stream` directamente al endpoint de Computer Vision, evitando la necesidad de almacenar la imagen en un blob público.

Azure AI Foundry proporciona los modelos pre-entrenados listos para usar —sin necesidad de entrenamiento custom—, lo que permitió una implementación rápida del prototipo.

---

## 7. Flujo técnico

```
CIUDADANO                 FRONTEND (app.js)              BACKEND (main.py)                 AZURE AI
    │                           │                              │                               │
    │  1. Escribe texto         │                              │                               │
    │     + adjunta foto        │                              │                               │
    │  ─────────────────────►   │                              │                               │
    │                           │  2. FormData (texto+imagen)  │                               │
    │                           │  POST /analizar              │                               │
    │                           │  ───────────────────────────►│                               │
    │                           │                              │  3. POST /sentiment            │
    │                           │                              │  ────────────────────────────► │
    │                           │                              │  ◄──── "negative"              │
    │                           │                              │                               │
    │                           │                              │  4. POST /keyPhrases           │
    │                           │                              │  ────────────────────────────► │
    │                           │                              │  ◄──── ["bache","calle"]       │
    │                           │                              │                               │
    │                           │                              │  5. POST /imageanalysis        │
    │                           │                              │  ────────────────────────────► │
    │                           │                              │  ◄──── tags:["pothole",...]    │
    │                           │                              │                               │
    │                           │                              │  6. clasificar_categoria()     │
    │                           │                              │  7. clasificar_por_tags()      │
    │                           │                              │  8. calcular_prioridad()       │
    │                           │                              │  9. generar_ticket()           │
    │                           │                              │  10. guardar → tickets.json    │
    │                           │                              │                               │
    │                           │  ◄──── JSON (ticket)         │                               │
    │  ◄────────────────────    │                              │                               │
    │   Muestra ticket +        │                              │                               │
    │   actualiza historial     │                              │                               │
```

**Detalle paso a paso:**

1. El ciudadano escribe la descripción y opcionalmente sube una imagen.
2. El frontend construye un `FormData` y hace `POST /analizar`.
3. El backend invoca **Sentiment Analysis** → obtiene `positive | neutral | negative`.
4. Invoca **Key Phrases** → obtiene lista de frases relevantes.
5. Si hay imagen, invoca **Image Analysis (tags)** → obtiene etiquetas.
6. `clasificar_categoria()` mapea frases clave a categorías (BASURA, BACHE, ALUMBRADO, AGUA).
7. `clasificar_por_tags()` mapea tags de imagen a categorías (respaldo/complemento).
8. `calcular_prioridad()` combina categoría + sentimiento + palabras de urgencia → BAJA | MEDIA | ALTA.
9. Se genera el ticket con UUID, categoría, prioridad, estado "ABIERTO" y timestamp.
10. Se persiste en `tickets.json` y se retorna al frontend, donde se renderiza con colores según prioridad (rojo=ALTA, amarillo=MEDIA, verde=BAJA).

---

## 8. Impacto de negocio

| Dimensión | Impacto |
|---|---|
| **Eficiencia operativa** | Elimina la clasificación manual de reportes. Un municipio que recibe cientos de reportes diarios puede procesarlos automáticamente en segundos. |
| **Tiempo de respuesta** | La priorización automática permite atender primero los incidentes críticos (sentimiento negativo + palabras de urgencia), reduciendo riesgos ciudadanos. |
| **Reducción de costos** | Menos personal dedicado a triaje de reportes; los funcionarios se enfocan en la resolución, no en la clasificación. |
| **Trazabilidad** | Cada reporte genera un ticket con ID único, fecha y estado, habilitando seguimiento y rendición de cuentas. |
| **Inclusión ciudadana** | Interfaz sencilla que permite a cualquier persona reportar problemas sin trámites burocráticos, fomentando la participación cívica. |
| **Escalabilidad** | El modelo puede extenderse a más categorías urbanas, integrar geolocalización, y conectarse a sistemas de gestión municipal existentes. |

---

## 9. Limitaciones

| Limitación | Descripción |
|---|---|
| **Persistencia frágil** | Los tickets se almacenan en un archivo JSON local (`tickets.json`). No hay base de datos relacional ni sistema de respaldos; un fallo en disco podría perder todos los datos. |
| **Sin autenticación** | No hay sistema de login ni roles. Cualquier persona puede enviar reportes o consultar todos los tickets. Vulnerable a abuso y spam. |
| **Sin geolocalización** | No se captura la ubicación del incidente, información vital para despachar cuadrillas de mantenimiento. |
| **Clasificación basada en reglas** | La categorización usa coincidencia de palabras clave hardcodeadas. Reportes con vocabulario no contemplado se clasifican como "OTRO". |
| **Dependencia de Azure** | Si los servicios de Azure no están disponibles o las credenciales expiran, todo el sistema de análisis falla sin fallback. |
| **Sin actualización de estado** | Los tickets se crean como "ABIERTO" pero no existe endpoint ni UI para cambiar su estado (en progreso, resuelto, cerrado). |
| **Imagen por URL vs. bytes** | Existen dos funciones para análisis de imagen (`analizar_imagen` por URL y `analizar_imagen_bytes`), pero solo se usa la versión por bytes; la otra queda como código muerto. |
| **Sin validación de entrada** | No se valida longitud mínima/máxima del texto ni tipo/tamaño de imagen. Un texto vacío o una imagen corrupta podrían generar errores. |
| **Entorno single-server** | Uvicorn corre en un solo proceso sin balanceo de carga ni despliegue en la nube, limitando la escalabilidad en producción. |

---

## 10. Escalabilidad Futura

- **Geolocalización y mapas** — Capturar GPS del ciudadano y visualizar incidentes en un mapa interactivo (Azure Maps).
- **Base de datos en la nube** — Migrar de JSON local a Azure SQL / PostgreSQL con respaldos automáticos.
- **Autenticación y roles** — Login ciudadano + panel administrativo con permisos por rol.
- **Gestión de estados** — Flujo ABIERTO → EN PROGRESO → RESUELTO → CERRADO con notificaciones.
- **App móvil (PWA)** — Reporte desde el terreno con cámara y GPS integrados.
- **IA avanzada** — Modelos custom en Azure AI Foundry, detección de objetos (Custom Vision) y análisis predictivo.
- **Integraciones** — APIs municipales, chatbot WhatsApp (Azure Bot Service), sensores IoT.

---

## 11. Conclusiones

1. **La IA resuelve un problema real**: Alerta Urbana demuestra que con servicios cognitivos de Azure es posible transformar reportes ciudadanos en texto libre en tickets clasificados y priorizados de forma automática, eliminando la intervención manual.
2. **Combinación texto + imagen es clave**: La fusión de NLP (sentimiento + frases clave) con Computer Vision (etiquetado de imágenes) produce una clasificación más robusta que cualquiera de los dos enfoques por separado.
3. **Azure AI Foundry acelera el desarrollo**: El uso de modelos pre-entrenados y un endpoint multiservicios permitió construir un prototipo funcional sin necesidad de entrenar modelos propios ni gestionar infraestructura de ML.
4. **Arquitectura simple pero efectiva**: La combinación de FastAPI + HTML/JS vanilla + archivo JSON ofrece un MVP rápido de implementar, ideal para validar la idea antes de invertir en infraestructura compleja.
5. **La priorización inteligente genera valor inmediato**: Detectar urgencia a partir del sentimiento y palabras clave permite que los municipios atiendan primero los incidentes críticos, reduciendo riesgos para la ciudadanía.
6. **El prototipo tiene camino claro hacia producción**: Las limitaciones identificadas (persistencia, autenticación, geolocalización) tienen soluciones conocidas en el ecosistema Azure, lo que facilita una evolución incremental del sistema.
7. **Impacto social tangible**: La herramienta democratiza el acceso al reporte urbano, fomentando la participación ciudadana y la transparencia en la gestión municipal.
