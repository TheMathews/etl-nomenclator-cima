"""
Módulo: zip_handler.py
Objetivo: Gestionar la apertura, validación y extracción segura del paquete ZIP 
          descargado desde el Nomenclátor de la AEMPS.
Lógica:   Actúa como una barrera de seguridad (Gateway) para la ETL. Antes de que el 
          proceso intente leer ficheros a ciegas, este módulo garantiza la integridad 
          del archivo y cruza su contenido real contra la configuración esperada (config.json).
          Esto previene fallos catastróficos en fases posteriores si la AEMPS cambia 
          la estructura del ZIP (ej. olvidando incluir un diccionario clave).
"""

import zipfile
import os
from typing import List, Tuple

class ZipHandler:
    """
    Gestor independiente para la manipulación, validación y extracción de archivos ZIP.
    
    Aisla la lógica de manejo de ficheros comprimidos para que el orquestador principal
    no tenga que lidiar con la librería 'zipfile' directamente.
    
    Attributes:
        zip_path (str): Ruta absoluta o relativa al archivo ZIP local.
    """
    
    def __init__(self, zip_path: str):
        """
        Inicializa el manejador y realiza comprobaciones de integridad básicas.
        
        Args:
            zip_path (str): Ruta donde se encuentra el fichero ZIP descargado.
            
        Raises:
            FileNotFoundError: Si el archivo no existe en la ruta especificada.
            ValueError: Si el archivo existe pero está corrupto o no es un ZIP válido.
        """
        self.zip_path = zip_path
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {zip_path}")
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"El archivo {zip_path} está corrupto o no es un ZIP válido.")

    def get_file_list(self) -> List[str]:
        """
        Lee los metadatos del ZIP para obtener su índice interno sin extraerlo.
        
        Returns:
            List[str]: Lista con los nombres de todos los archivos contenidos en el ZIP.
        """
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            return zf.namelist()

    def compare_with_expected(self, expected_files: List[str]) -> Tuple[List[str], List[str]]:
        """
        Compara el contenido real del ZIP con la lista de diccionarios que la ETL 
        necesita procesar (definidos en config.json).
        
        Lógica:
            Utiliza operaciones de conjuntos (sets) de Python para realizar la 
            comparación con complejidad O(n), siendo extremadamente eficiente.
        
        Args:
            expected_files (List[str]): Lista de nombres de fichero que la ETL espera encontrar.
            
        Returns:
            Tuple[List[str], List[str]]: Una tupla que contiene:
                - [0]: Lista de ficheros que FALTAN en el ZIP (Peligro para la ETL).
                - [1]: Lista de ficheros NUEVOS o inesperados en el ZIP (No bloqueante, pero útil para log).
        """
        actual_files = set(self.get_file_list())
        expected_set = set(expected_files)

        missing_files = list(expected_set - actual_files)
        unexpected_files = list(actual_files - expected_set)

        return missing_files, unexpected_files

    def extract_files(self, dest_folder: str, files_to_extract: List[str] = None):
        """
        Extrae de forma selectiva los archivos indicados a la carpeta temporal (Staging).
        
        Lógica:
            La extracción selectiva evita saturar el disco duro (I/O) extrayendo PDFs, 
            imágenes o ficheros no configurados que la AEMPS pueda haber metido en el ZIP 
            y que no forman parte del proceso ETL actual.
        
        Args:
            dest_folder (str): Ruta del directorio destino (ej. 'temp/'). Se creará si no existe.
            files_to_extract (List[str], optional): Lista específica de ficheros a extraer. 
                                                    Si es None, extrae el ZIP completo.
        """
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            if files_to_extract:
                for file in files_to_extract:
                    # extract() es seguro contra vulnerabilidades de path traversal simples
                    zf.extract(file, dest_folder)
            else:
                zf.extractall(dest_folder)