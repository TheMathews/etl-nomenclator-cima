"""
Módulo: xml_handler.py
Objetivo: Actuar como el motor de extracción principal. Lee archivos XML gigantes 
          (cientos de megabytes) y los convierte en un flujo (stream) continuo de 
          diccionarios de Python (simulando JSON).
Lógica:   Utiliza técnicas de "Lazy Streaming" (iterparse) para leer el XML nodo a nodo. 
          En lugar de cargar todo el archivo en la RAM, lee un registro, lo emite (yield), 
          y libera la memoria antes de leer el siguiente. Además, realiza introspección 
          automática para descubrir las URLs de los esquemas XSD, descargándolos 
          previamente de forma segura simulando un navegador real para evitar bloqueos.
"""

import os
import xml.etree.ElementTree as ET
import xmlschema
import hashlib
import json
import requests
from typing import Dict, Any

class XmlHandler:
    """
    Procesador avanzado de archivos XML masivos mediante streaming y validación XSD.
    
    Attributes:
        logger (Logger): Instancia del sistema de trazas para documentar el proceso.
        user_agent (str): Cabecera de navegador HTTP para evadir bloqueos institucionales.
        temp_dir (str): Directorio temporal para almacenar los esquemas descargados.
        ns_xsi (str): Namespace estándar del W3C para instancias XML Schema.
    """
    
    def __init__(self, logger, user_agent: str, temp_dir: str):
        """
        Inicializa el manejador XML.
        
        Args:
            logger (Logger): Objeto de log configurado en el orquestador principal.
            user_agent (str): Identificador de navegador extraído de la configuración.
            temp_dir (str): Ruta al directorio temporal de trabajo.
        """
        self.logger = logger
        self.user_agent = user_agent
        self.temp_dir = temp_dir
        self.ns_xsi = "{http://www.w3.org/2001/XMLSchema-instance}"

    def _iterador_seguro(self, schema, ruta_xml):
        """
        Envuelve la lectura del XML en un context manager (with) para asegurar el 
        cierre físico del archivo en el sistema operativo.
        
        Lógica:
            Previene el famoso error de Windows donde los archivos se quedan 
            bloqueados ('El proceso no tiene acceso al archivo...') si ocurre una 
            excepción a mitad del bucle ETL y el generador se destruye prematuramente.
            
        Args:
            schema (xmlschema.XMLSchema): Objeto de validación de esquema XSD.
            ruta_xml (str): Ruta local del fichero XML a leer.
            
        Yields:
            dict: Registro decodificado desde el XML.
        """
        with open(ruta_xml, 'rb') as xml_file:
            for item in schema.iter_decode(xml_file):
                yield item

    def convertir_xml_a_stream_json(self, ruta_xml: str) -> Dict[str, Any]:
        """
        Pipeline principal de conversión. Analiza el XML, descubre su esquema, 
        descarga el XSD localmente burlando restricciones y devuelve un generador 
        que emitirá los registros validados uno a uno.
        
        Args:
            ruta_xml (str): Ruta del fichero XML que se va a procesar.
            
        Returns:
            Dict[str, Any]: Un diccionario con:
                - 'success' (bool): Si la inicialización fue exitosa.
                - 'stream' (generator): El iterador que expulsa los registros.
                - 'metadata' (dict): Los datos del esquema y rutas descubiertas.
        """
        meta = self.obtener_metadata_xml(ruta_xml)
        if not meta["success"]:
            return meta

        # Determinamos la ruta de los datos (path) basándonos en el fichero
        nombre_fichero = os.path.basename(ruta_xml)
        
        if nombre_fichero == "Prescripcion.xml":
            # Regla dura (Hardcode) para el fichero maestro por su complejidad
            target_path = "prescription"
        else:
            # Para los diccionarios, la adivinanza dinámica o el comodín '*' funciona perfecto
            target_path = meta.get("child_tag", "*")

        def generador_seguro():
            """Sub-generador para aislar la apertura del fichero y garantizar el cierre (finally)"""
            
            # 1. INTERCEPCIÓN Y DESCARGA DEL XSD
            # La librería xmlschema hace peticiones sin User-Agent. Para evitar el bloqueo (Error 403), 
            # descargamos nosotros el XSD primero inyectando la cabecera de navegador.
            xsd_local_path = os.path.join(self.temp_dir, f"esquema_{nombre_fichero}.xsd")
            
            if not os.path.exists(xsd_local_path):
                self.logger.info(f"Descargando esquema XSD oficial ({meta['xsd_url']}) con cabeceras seguras...")
                headers = {"User-Agent": self.user_agent}
                res = requests.get(meta["xsd_url"], headers=headers)
                res.raise_for_status() # Lanza excepción si la AEMPS devuelve error
                
                with open(xsd_local_path, "wb") as f_xsd:
                    f_xsd.write(res.content)

            f = open(ruta_xml, 'rb')
            try:
                # 2. Inicialización del esquema XSD apuntando al fichero de nuestro disco duro 
                # en lugar de la URL, neutralizando la conexión automática de la librería.
                schema = xmlschema.XMLSchema(xsd_local_path)

                # 3. NUEVO: Envolvemos el fichero en un XMLResource 'lazy' para 
                # evadir el límite de 1M de elementos y liberar la RAM en tiempo real.
                recurso_lazy = xmlschema.XMLResource(f, lazy=True)
                
                # 4. Le pasamos el recurso perezoso a iter_decode
                for item in schema.iter_decode(recurso_lazy, path=target_path):
                    yield item
            finally:
                f.close() 

        self.logger.info(f"Validando {nombre_fichero} contra XSD (Ruta de datos: <{target_path}>)...")
        return {
            "success": True,
            "stream": generador_seguro(),
            "metadata": meta
        }

    def generar_hash_diccionario(self, diccionario: dict) -> str:
        """
        Genera un código SHA-256 único a partir del contenido de un registro.
        
        Lógica:
            Utiliza 'sort_keys=True' para asegurar que el JSON generado siempre 
            tenga las claves en el mismo orden. Así, si la AEMPS manda los datos 
            en orden distinto pero con los mismos valores, el Hash será idéntico 
            y no se registrará como una actualización innecesaria.
            
        Args:
            diccionario (dict): Registro del medicamento o diccionario extraído.
            
        Returns:
            str: Cadena hexadecimal de 64 caracteres con la huella digital del registro.
        """
        dict_str = json.dumps(diccionario, sort_keys=True)
        return hashlib.sha256(dict_str.encode('utf-8')).hexdigest()

    def obtener_metadata_xml(self, ruta_xml: str) -> Dict[str, Any]:
        """
        Realiza "Introspección" del archivo XML leyendo solo los primeros nodos.
        
        Lógica:
            Permite que el código sea independiente del formato de la AEMPS. 
            Busca dinámicamente dónde está el XSD (schemaLocation) y qué nombre 
            tienen las etiquetas repetitivas para saber de dónde extraer los datos.
            
        Args:
            ruta_xml (str): Ruta del fichero XML a inspeccionar.
            
        Returns:
            Dict[str, Any]: Diccionario con la URL del XSD, el nodo raíz y el nodo hijo.
        """
        try:
            with open(ruta_xml, 'rb') as xml_file:
                context = ET.iterparse(xml_file, events=("start",))
                _, root = next(context)
                
                schema_location = root.attrib.get(f"{self.ns_xsi}schemaLocation")
                if not schema_location:
                    return {"success": False, "error": "No se encontró xsi:schemaLocation"}

                parts = schema_location.split()
                target_ns = "http://schemas.aemps.es/prescripcion/aemps_prescripcion"
                xsd_url = parts[-1] 

                for i in range(0, len(parts) - 1, 2):
                    if parts[i] == target_ns:
                        xsd_url = parts[i + 1]
                        break

                root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag

                # MAGIA: Obtenemos el nombre exacto de las etiquetas repetidas (los hijos)
                try:
                    _, first_child = next(context)
                    child_tag = first_child.tag.split('}')[-1] if '}' in first_child.tag else first_child.tag
                    
                    # FIX: Excepción para la cabecera de Prescripcion.xml
                    if child_tag == 'listprescriptiondate':
                        # Saltamos este nodo informativo y leemos el siguiente (el dato real)
                        _, second_child = next(context)
                        child_tag = second_child.tag.split('}')[-1] if '}' in second_child.tag else second_child.tag
                        
                except StopIteration:
                    child_tag = "*"

                return {
                    "success": True,
                    "xsd_url": xsd_url,
                    "root_tag": root_tag,
                    "child_tag": child_tag
                }
        except Exception as e:
            return {"success": False, "error": f"Fallo al leer metadatos: {str(e)}"}

    def obtener_fecha_prescripcion(self, ruta_xml: str) -> str:
        """
        Busca la marca de tiempo (timestamp) de exportación del fichero maestro.
        
        Lógica:
            En lugar de leer los 200MB de Prescripcion.xml, utiliza iterparse para 
            leer solo los primeros kilobytes, interceptar la etiqueta <listprescriptiondate>, 
            guardar la fecha y abortar la lectura inmediatamente. Esto ahorra muchísimo tiempo.
            
        Args:
            ruta_xml (str): Ruta del fichero Prescripcion.xml.
            
        Returns:
            str: Fecha encontrada (ej. '2026-05-07') o None si falla.
        """
        self.logger.info(f"Buscando fecha de exportación en {os.path.basename(ruta_xml)}...")
        try:
            # ABRIMOS CON WITH PARA GARANTIZAR EL CIERRE FÍSICO DEL ARCHIVO AL SALIR
            with open(ruta_xml, 'rb') as xml_file:
                context = ET.iterparse(xml_file, events=("end",))
                
                for event, elem in context:
                    # Limpiamos el namespace por si CIMA usa algo como {http://schemas...}listprescriptiondate
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    
                    if tag_name == 'listprescriptiondate':
                        fecha_exportacion = elem.text.strip() if elem.text else None
                        self.logger.info(f"Fecha detectada: {fecha_exportacion}. Abortando lectura del resto del XML.")
                        
                        # Limpieza de memoria crucial antes de salir
                        elem.clear()
                        # Al hacer return aquí, salimos del 'with' y Python cierra el archivo automáticamente.
                        return fecha_exportacion
                    
                    # Liberamos memoria de otras cabeceras que hayamos leído mientras buscábamos
                    elem.clear()
                    
            self.logger.warning("No se encontró la etiqueta <listprescriptiondate> en el XML.")
            return None
            
        except Exception as e:
            self.logger.error(f"Error interceptando la fecha en el XML: {str(e)}")
            return None