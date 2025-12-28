# Anax Forensics Email Extractor

Herramienta de nivel pericial diseñada para la extracción automatizada de correos electrónicos desde contenedores Mbox, convirtiéndolos en documentos PDF con preservación de metadatos, gestión de imágenes incrustadas (CID) y validación de integridad mediante hashing SHA-256.

## Características Principales

* **Preservación Forense:** Incluye los encabezados técnicos originales (Raw Headers) al final de cada PDF generado.
* **Integridad de Evidencia:** Genera automáticamente un reporte maestro en HTML con la firma digital SHA-256 de cada archivo extraído.
* **Gestión de Adjuntos:** Extrae y renombra adjuntos e imágenes `inline` vinculándolos correctamente en el cuerpo del mensaje procesado.
* **Higiene de Contenido:** Limpia scripts y estilos maliciosos o problemáticos del HTML original para garantizar un renderizado seguro y fiel.

## Estructura del Proyecto

```text
.
├── extract_to_pdf.py       # Script principal (Anax Forensics)
├── .gitignore              # Archivo de exclusión de evidencia
├── README.md               # Documentación oficial
└── requirements.txt        # Dependencias (xhtml2pdf)