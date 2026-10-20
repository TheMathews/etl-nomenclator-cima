"""
Módulo: extractor.py
Objetivo: Gestionar la comunicación HTTP con los servidores de la AEMPS y realizar
          la descarga segura del archivo maestro (ZIP).
Lógica:   Utiliza "Stream Downloading" para descargar archivos grandes sin cargar
          la memoria RAM. Inmediatamente después de la descarga, calcula la huella
          digital (SHA-256) leyendo el archivo en bloques (chunks) pequeños. Este 
          hash es la clave que permite a la ETL ser idempotente (abortar si no hay cambios).
"""

import requests
import hashlib
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Tuple

def download_cima_zip(url: str, dest_folder: str, logger: Any, user_agent: str) -> Tuple[str, str]:
    """
    Descarga el ZIP oficial de CIMA mediante un flujo de datos (streaming) 
    y calcula su huella digital criptográfica (Hash).
    
    Lógica:
        En lugar de descargar los 50MB-100MB del ZIP directamente en una variable
        (lo cual bloquea la RAM), copia los bytes desde la tarjeta de red (requests)
        directamente al disco duro (shutil).
        Luego, calcula el Hash SHA-256 leyendo el fichero físico en bloques de 4KB.
        
    Args:
        url (str): URL oficial de la AEMPS (ej. 'https://.../prescripcion.zip').
        dest_folder (str): Ruta de la carpeta temporal local donde guardar el ZIP.
        logger (Any): Objeto de log configurado en el orquestador.
        
    Returns:
        Tuple[str, str]: Una tupla con:
            - [0]: Ruta absoluta al fichero ZIP descargado.
            - [1]: Hash SHA-256 en formato string hexadecimal.
            
    Raises:
        requests.exceptions.RequestException: Si la URL no responde o da error 404/500.
    """
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    temp_zip = os.path.join(dest_folder, "prescripcion_temp.zip")
    headers = {"User-Agent": user_agent}

    try:
        logger.info(f"Iniciando descarga desde {url}")
        
        # 1. Descarga por Streaming HTTP directo a Disco
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status() # Fuerza excepción si el servidor da error HTTP
            with open(temp_zip, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        
        # 2. Cálculo Eficiente de Huella Digital (SHA-256 en chunks de 4KB)
        sha256_hash = hashlib.sha256()
        with open(temp_zip, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        current_hash = sha256_hash.hexdigest()
        logger.info(f"Fichero descargado. Hash SHA256: {current_hash}")
        
        return temp_zip, current_hash

    except Exception as e:
        logger.error(f"Error en la descarga: {e}")
        raise


def extract_and_validate_zip(zip_path: str, extract_folder: str, logger: Any) -> List[str]:
    """
    (Legacy/Utilidad Alternativa)
    Descomprime un archivo ZIP e identifica todos los ficheros XML contenidos.
    
    Args:
        zip_path (str): Ruta local del ZIP.
        extract_folder (str): Carpeta donde se volcarán los ficheros extraídos.
        logger (Any): Objeto de trazas.
        
    Returns:
        List[str]: Rutas absolutas a todos los archivos .xml extraídos.
        
    Raises:
        ValueError: Si el archivo está corrupto o no contiene ningún XML.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"El archivo {zip_path} está corrupto o no es un ZIP válido.")
    
    xml_files = []
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        archivos = zip_ref.namelist()
        logger.info(f"Ficheros detectados en el ZIP: {archivos}")
        
        for archivo in archivos:
            if archivo.endswith('.xml'):
                # Extraemos solo los archivos con extensión XML
                zip_ref.extract(archivo, extract_folder)
                xml_files.append(os.path.join(extract_folder, archivo))
                
    if not xml_files:
        raise ValueError("El ZIP de CIMA no contiene ficheros XML.")
        
    return xml_files


def parse_cima_xml_to_json(xml_path: str, expected_tags: List[str], logger: Any) -> List[Dict[str, Any]]:
    """
    (Legacy/Utilidad Alternativa)
    Procesa un XML estructural básico mediante iterparse manual.
    
    Lógica:
        Vigila si faltan etiquetas esperadas o si la AEMPS ha añadido nuevas 
        etiquetas al XML que no estaban mapeadas, alertando en el log.
        
    Args:
        xml_path (str): Ruta al fichero XML.
        expected_tags (List[str]): Lista de nombres de etiquetas a capturar.
        logger (Any): Objeto de trazas.
        
    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con la información parseada.
    """
    datos = []
    
    # Usamos iterparse para no cargar todo el XML de golpe en memoria
    context = ET.iterparse(xml_path, events=("start", "end"))
    
    root = None
    registro_actual = {}
    
    for event, elem in context:
        if root is None:
            root = elem # Guardamos el nodo raíz
            
        # Cuando termina de leer un nodo (etiqueta)
        if event == "end":
            tag_name = elem.tag
            
            # Si es una etiqueta hija de datos
            if tag_name in expected_tags:
                registro_actual[tag_name] = elem.text.strip() if elem.text else None
                
            # Validar si el XML trae etiquetas nuevas que NO esperamos
            elif tag_name != 'medicamento' and tag_name != root.tag: 
                logger.warning(f"¡Atención! Nueva etiqueta detectada en el XML de CIMA: <{tag_name}>. No se está importando.")

            # Cuando termina el bloque de un medicamento entero, lo guardamos y limpiamos
            if tag_name == 'medicamento': 
                datos.append(registro_actual)
                registro_actual = {}
                # Liberamos memoria del sub-árbol
                root.clear()
                
    logger.info(f"Transformación de {os.path.basename(xml_path)} completada: {len(datos)} registros procesados.")
    return datos