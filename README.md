# Anax Forensics Email Extractor

Herramientas de nivel pericial diseñada para la extracción automatizada de correos electrónicos desde contenedores Mbox, convirtiéndolos en documentos PDF con preservación de metadatos, gestión de imágenes incrustadas (CID) y validación de integridad mediante hashing SHA-256.

## Características principales

* **Preservación forense:** Incluye los encabezados técnicos originales (Raw Headers) al final de cada PDF generado.
* **Integridad de evidencia:** Genera automáticamente un reporte maestro en HTML con la firma digital SHA-256 de cada archivo extraído.
* **Gestión de ajuntos:** Extrae y renombra adjuntos e imágenes `inline` vinculándolos correctamente en el cuerpo del mensaje procesado.
* **Higiene de contenido:** Limpia scripts y estilos maliciosos o problemáticos del HTML original para garantizar un renderizado seguro y fiel.

## Estructura del proyecto

```text
.
├── afee.py                 # Script principal (Anax Forensics)
├── cutpdf.py               # Fragmentador inteligente de PDFs (Anax Forensics)
├── .gitignore              # Archivo de exclusión de evidencia
├── README.md               # Documentación oficial
└── requirements.txt        # Dependencias (xhtml2pdf)
```

## Requisitos e instalación

1. **Python 3.x**
2. Instalar las dependencias necesarias:
   ```bash
   pip install xhtml2pdf
   ```

## Uso

1. Coloque su archivo `Inbox` (formato Mbox) en la raíz del proyecto.
2. Ejecute el script:
   ```bash
   python afee.py
   ```
3. Los resultados se encontrarán en la carpeta `anax_extraction_result/`, organizados por correos y adjuntos.

## Consideraciones de seguridad forense

Este script ha sido diseñado para no modificar el archivo origen (`Mbox`). Sin embargo, se recomienda trabajar siempre sobre una **copia de trabajo** y no sobre la evidencia original directamente.

---
*Parte de la suite Anax Forensics - Preservando la integridad digital.*