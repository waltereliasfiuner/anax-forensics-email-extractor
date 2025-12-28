import os
import sys
from PyPDF2 import PdfReader, PdfWriter

def dividir_pdf_veloz(archivo_entrada, limite_mb=4.8):
    if not os.path.exists(archivo_entrada):
        print(f"Error: No se encuentra el archivo '{archivo_entrada}'")
        return

    limite_bytes = limite_mb * 1024 * 1024
    reader = PdfReader(archivo_entrada)
    nombre_base = os.path.splitext(archivo_entrada)[0]
    total_paginas = len(reader.pages)
    
    print(f"--- Iniciando división optimizada ---")
    print(f"Total de páginas: {total_paginas}")

    pagina_actual = 0
    numero_parte = 1

    while pagina_actual < total_paginas:
        writer = PdfWriter()
        conteo_paginas_bloque = 0
        
        # Agregamos páginas hasta que el peso exceda el límite
        while pagina_actual < total_paginas:
            writer.add_page(reader.pages[pagina_actual])
            conteo_paginas_bloque += 1
            
            # Verificamos peso
            with open("temp_check.pdf", "wb") as f_temp:
                writer.write(f_temp)
            
            peso_actual = os.path.getsize("temp_check.pdf")
            
            if peso_actual > limite_bytes:
                # Si el bloque tiene más de una página, quitamos la última y cerramos
                if conteo_paginas_bloque > 1:
                    # Re-creamos el writer sin la última página para esta parte
                    writer_final = PdfWriter()
                    for p in range(pagina_actual - conteo_paginas_bloque + 1, pagina_actual):
                        writer_final.add_page(reader.pages[p])
                    
                    output_name = f"{nombre_base}_PARTE_{numero_parte}.pdf"
                    with open(output_name, "wb") as f_out:
                        writer_final.write(f_out)
                    
                    print(f"✔ Generado: {output_name} | Páginas: {conteo_paginas_bloque-1} | Tamaño: {os.path.getsize(output_name)/1024/1024:.2f} MB")
                    
                    # No avanzamos la pagina_actual porque debe ser la primera del próximo bloque
                    numero_parte += 1
                    break 
                else:
                    # Si una sola página ya pesa más de 4.8MB
                    output_name = f"{nombre_base}_PARTE_{numero_parte}_GRANDE.pdf"
                    with open(output_name, "wb") as f_out:
                        writer.write(f_out)
                    print(f"⚠ Página {pagina_actual + 1} excede el límite sola ({peso_actual/1024/1024:.2f} MB).")
                    pagina_actual += 1
                    numero_parte += 1
                    break
            
            pagina_actual += 1
            
            # Si llegamos al final del documento dentro de este bucle
            if pagina_actual == total_paginas:
                output_name = f"{nombre_base}_PARTE_{numero_parte}.pdf"
                with open(output_name, "wb") as f_out:
                    writer.write(f_out)
                print(f"✔ Generado (Final): {output_name} | Páginas: {conteo_paginas_bloque} | Tamaño: {os.path.getsize(output_name)/1024/1024:.2f} MB")

    if os.path.exists("temp_check.pdf"):
        os.remove("temp_check.pdf")
    print("\n--- Proceso finalizado con éxito ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 cutpdf.py archivo.pdf")
    else:
        dividir_pdf_veloz(sys.argv[1])
