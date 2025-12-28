import mailbox
import email
from email.utils import parsedate_to_datetime
from email.header import decode_header
import os
import re
import hashlib
from datetime import datetime

# ==============================================================================
# ANAX FORENSICS EMAIL EXTRACTOR - CONFIGURACIÓN DE ENTORNO
# ==============================================================================
# El archivo origen debe ser el contenedor Mbox de Thunderbird (ej. 'Inbox')
mbox_file = 'Inbox'  
output_base_dir = 'anax_extraction_result'
emails_dir = os.path.join(output_base_dir, 'emails')
adjuntos_dir = os.path.join(output_base_dir, 'adjuntos')
log_file_path = os.path.join(output_base_dir, 'anax_reporte_maestro.html')

# Creación de la estructura de directorios forenses para organización de evidencia
for folder in [emails_dir, adjuntos_dir]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==============================================================================
# FUNCIONES DE SEGURIDAD E INTEGRIDAD (CADENA DE CUSTODIA)
# ==============================================================================

def get_file_hash(filepath):
    """
    Calcula el hash SHA-256 de un archivo para asegurar la cadena de custodia
    e integridad de la evidencia digital generada.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        return f"ERROR_HASH: {str(e)}"

def decode_mime_header(s):
    """
    Decodifica encabezados MIME (RFC 2047) para asegurar que caracteres 
    especiales, tildes y codificaciones diversas sean legibles.
    """
    if not s:
        return ""
    try:
        decoded_fragments = decode_header(s)
        result = ""
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                if encoding:
                    result += fragment.decode(encoding, errors='ignore')
                else:
                    result += fragment.decode('utf-8', errors='ignore')
            else:
                result += fragment
        return result
    except Exception:
        return str(s)

def clean_filename(text):
    """
    Normaliza cadenas para crear nombres de archivo válidos.
    CORRECCIÓN: Se utiliza una regex que solo elimina caracteres prohibidos
    (\ / : * ? " < > |) preservando el resto del texto (evita truncar nombres).
    """
    if not text:
        return "sin_asunto"
    text = decode_mime_header(text)
    # Eliminación estricta de caracteres prohibidos por OS
    clean = re.sub(r'[\\/*?:"<>|]', "", text)
    return clean.strip()[:100]

# ==============================================================================
# PROCESAMIENTO DE CONTENIDO (HTML, CSS E IMÁGENES EMBEBIDAS)
# ==============================================================================

def process_images_and_clean_html(html_content, image_map):
    """
    Realiza la higiene del HTML para compatibilidad con el motor xhtml2pdf.
    Reemplaza referencias CID (Content-ID) por rutas locales absolutas.
    """
    if not html_content:
        return ""
    
    # 1. Eliminación de scripts y bloques de estilo para evitar errores de renderizado
    html_content = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Eliminación de estilos inline que pueden romper el layout del PDF
    html_content = re.sub(r'style="[^"]*"', '', html_content, flags=re.IGNORECASE)
    
    # 3. Mapeo de CIDs a imágenes locales extraídas previamente
    for cid, local_path in image_map.items():
        cid_clean = cid.strip('<>')
        # Soporta tanto comillas simples como dobles en el atributo src
        pattern = r'src=["\']cid:' + re.escape(cid_clean) + r'["\']'
        replacement = f'src="{os.path.abspath(local_path)}"'
        html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)

    return html_content

def get_email_data(msg, prefix, clean_sub):
    """
    Extrae de forma recursiva el cuerpo (HTML/Plain), adjuntos y recursos
    embebidos (Inline) manteniendo la integridad técnica.
    """
    body_html = ""
    body_plain = ""
    adjuntos_registrados = []
    image_map = {}

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get('Content-Disposition'))
        
        # Extracción de Imágenes CID (Inline)
        if 'inline' in content_disposition and content_type.startswith('image/'):
            cid = part.get('Content-ID')
            if cid:
                cid_clean = cid.strip('<>')
                original_fname = part.get_filename() or f"img_{cid_clean}.png"
                local_fname = f"{prefix}_CID_{clean_filename(original_fname)}"
                local_path = os.path.join(adjuntos_dir, local_fname)
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        with open(local_path, 'wb') as f:
                            f.write(payload)
                        image_map[cid_clean] = local_path
                except Exception as e:
                    print(f"      [!] Error en imagen CID {cid_clean}: {e}")
                continue

        # Extracción de Adjuntos Independientes
        if 'attachment' in content_disposition:
            fname = part.get_filename()
            if fname:
                decoded_fname = decode_mime_header(fname)
                clean_fname = clean_filename(decoded_fname)
                final_adjunto_name = f"{prefix}_{clean_sub}_{clean_fname}"
                path_adjunto = os.path.join(adjuntos_dir, final_adjunto_name)
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        with open(path_adjunto, 'wb') as f:
                            f.write(payload)
                        adjuntos_registrados.append(decoded_fname)
                except Exception as e:
                    print(f"      [!] Error en adjunto {decoded_fname}: {e}")
            continue

        # Extracción de Cuerpo del mensaje
        if content_type == 'text/html':
            try:
                body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            except: pass
        elif content_type == 'text/plain':
            try:
                body_plain = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            except: pass

    return (body_html or body_plain, adjuntos_registrados, image_map)

# ==============================================================================
# GENERACIÓN DE ENTREGABLES (PDF PERICIAL Y REPORTE MAESTRO)
# ==============================================================================

def create_pdf(content, headers, image_map, output_path):
    """
    Construye el PDF con el estilo visual de Anax Forensics, integrando
    metadatos, contenido limpio y headers originales.
    """
    from xhtml2pdf import pisa
    
    # Decodificación de metadatos críticos
    h_from = decode_mime_header(headers.get('From', 'Desconocido'))
    h_to = decode_mime_header(headers.get('To', 'Desconocido'))
    h_date = headers.get('Date', 'Desconocida')
    h_subject = decode_mime_header(headers.get('Subject', 'Sin Asunto'))

    # Reconstrucción de headers técnicos (Raw Headers) para la sección de evidencia
    tech_headers_html = ""
    for key, value in headers.items():
        v_safe = str(value).replace('<', '&lt;').replace('>', '&gt;')
        tech_headers_html += f"<b>{key}:</b> {v_safe}<br>\n"

    # Preparación del contenido
    clean_content = process_images_and_clean_html(content, image_map)
    # Si no es HTML nativo, convertimos saltos de línea para preservar estructura
    if "<body" not in clean_content.lower() and "<div" not in clean_content.lower():
        clean_content = clean_content.replace('\n', '<br>')

    # Plantilla con diseño pericial
    html_template = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: a4; margin: 1.5cm; }}
                body {{ font-family: sans-serif; font-size: 10pt; color: #333; line-height: 1.4; }}
                .main-headers {{ background-color: #f4f4f4; padding: 15px; border-bottom: 2px solid #004d40; margin-bottom: 20px; }}
                .label {{ font-weight: bold; color: #000; width: 80px; display: inline-block; }}
                .content-box {{ padding: 10px; border-left: 2px solid #eee; }}
                img {{ max-width: 100%; height: auto; margin: 10px 0; }}
                .forensic-footer {{ margin-top: 40px; border-top: 3px solid #004d40; padding-top: 15px; }}
                .tech-title {{ font-weight: bold; font-size: 11pt; color: #004d40; margin-bottom: 10px; }}
                .tech-data {{ font-family: monospace; font-size: 7.5pt; background-color: #fafafa; padding: 10px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="main-headers">
                <p><span class="label">DE:</span> {h_from}</p>
                <p><span class="label">PARA:</span> {h_to}</p>
                <p><span class="label">FECHA:</span> {h_date}</p>
                <p><span class="label">ASUNTO:</span> {h_subject}</p>
            </div>
            <div class="content-box">
                {clean_content}
            </div>
            <div class="forensic-footer">
                <p class="tech-title">ANAX FORENSICS - ENCABEZADOS ORIGINALES</p>
                <div class="tech-data">
                    {tech_headers_html}
                </div>
            </div>
        </body>
    </html>
    """
    try:
        with open(output_path, "wb") as f:
            pisa.CreatePDF(html_template, dest=f, encoding='utf-8')
    except Exception as e:
        print(f"      [!] Error crítico en generación PDF: {e}")

def initialize_log():
    """Inicia la estructura del Reporte Maestro de Anax Forensics."""
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w", encoding='utf-8') as f:
            f.write("""
            <html>
            <head>
                <meta charset='UTF-8'>
                <style>
                    body { font-family: Arial, sans-serif; margin: 30px; background-color: #fdfdfd; }
                    h2 { color: #004d40; border-bottom: 2px solid #004d40; padding-bottom: 5px; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }
                    th, td { border: 1px solid #ccc; padding: 10px; font-size: 9pt; text-align: left; word-wrap: break-word; }
                    th { background-color: #004d40; color: white; }
                    .hash-row { background-color: #fffde7; font-family: 'Courier New', monospace; font-size: 8pt; }
                    .tag-hash { font-weight: bold; color: #c62828; }
                </style>
            </head>
            <body>
                <h2>ANAX FORENSICS - REPORTE MAESTRO DE EXTRACCIÓN</h2>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 15%;">Fecha</th>
                            <th style="width: 35%;">Asunto</th>
                            <th style="width: 25%;">Remitente</th>
                            <th style="width: 25%;">Adjuntos</th>
                        </tr>
                    </thead>
                    <tbody>
            """)

def add_log_entry(fecha, asunto, remitente, adjuntos, pdf_hash):
    """Registra un mensaje procesado y su firma digital en el log maestro."""
    adj_str = ", ".join(adjuntos) if adjuntos else "Ninguno"
    with open(log_file_path, "a", encoding='utf-8') as f:
        f.write(f"""
        <tr>
            <td>{fecha}</td>
            <td>{asunto}</td>
            <td>{remitente}</td>
            <td>{adj_str}</td>
        </tr>
        <tr class="hash-row">
            <td colspan="4"><span class="tag-hash">SHA-256:</span> {pdf_hash}</td>
        </tr>
        """)

# ==============================================================================
# MOTOR DE EJECUCIÓN
# ==============================================================================

if __name__ == "__main__":
    if not os.path.exists(mbox_file):
        print(f"\n[!] ERROR: No se encontró el archivo '{mbox_file}'.")
    else:
        mbox = mailbox.mbox(mbox_file)
        count = len(mbox)
        
        print("\n" + "═"*60)
        print("   ANAX FORENSICS EMAIL EXTRACTOR v2.2")
        print("═"*60)
        print(f"   Fuente: {mbox_file}")
        print(f"   Mensajes detectados: {count}")
        
        val = input("\n   Cantidad a procesar (Enter para TODOS): ").strip()
        limit = min(int(val) if val.isdigit() else count, count)
        
        initialize_log()
        
        for i in range(limit):
            try:
                # Lectura de bytes crudos para máxima fidelidad
                raw_bytes = mbox[i].as_bytes()
                msg = email.message_from_bytes(raw_bytes)
                
                # Manejo de fecha y prefijo
                date_header = msg.get('Date')
                try:
                    dt = parsedate_to_datetime(date_header)
                except:
                    dt = datetime.now()
                
                prefix = dt.strftime('%Y%m%d-%H%M')
                subject_raw = msg.get('Subject', 'Sin Asunto')
                clean_sub = clean_filename(subject_raw)
                
                print(f"   [{i+1}/{limit}] {decode_mime_header(subject_raw)[:55]}...")
                
                # Proceso de extracción y PDF
                cuerpo, adjs, cids = get_email_data(msg, prefix, clean_sub)
                nombre_pdf = f"{prefix} - {clean_sub}.pdf"
                path_pdf = os.path.join(emails_dir, nombre_pdf)
                
                create_pdf(cuerpo, msg, cids, path_pdf)
                
                # Registro e integridad
                hash_final = get_file_hash(path_pdf)
                add_log_entry(
                    dt.strftime('%Y-%m-%d %H:%M'),
                    decode_mime_header(subject_raw),
                    decode_mime_header(msg.get('From', 'Desconocido')),
                    adjs,
                    hash_final
                )
                
            except Exception as e:
                print(f"   [!] Error en índice {i}: {e}")
        
        with open(log_file_path, "a", encoding='utf-8') as f:
            f.write("</tbody></table><p style='font-size:8pt; color:#666;'>Fin del proceso Anax Forensics.</p></body></html>")
            
        print("\n" + "═"*60)
        print("   EXTRACCIÓN FINALIZADA")
        print(f"   Resultados en: {output_base_dir}")
        print("═"*60 + "\n")
