"""
Módulo: logger.py
Objetivo: Estandarizar y centralizar el sistema de trazas (logs) de toda la ETL.
Lógica:   Configura un sistema de registro dual: envía los mensajes a la consola 
          (para monitorización en tiempo real durante el desarrollo/ejecución manual) 
          y a un archivo de texto rotatorio (para auditoría histórica desatendida).
          Implementa un mecanismo de rotación para asegurar que los logs no consuman 
          infinitamente el espacio en disco del servidor.
"""

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_path: str, logger_name: str = "ETL_CIMA") -> logging.Logger:
    """
    Crea y configura el logger principal de la aplicación.
    
    Lógica:
        - Crea automáticamente la carpeta de logs si no existe.
        - Configura un 'RotatingFileHandler' que crea un archivo nuevo cuando el 
          actual alcanza los 5MB, conservando solo los últimos 5 archivos históricos.
        - Fuerza la codificación UTF-8 para prevenir crashes ('UnicodeEncodeError') 
          al intentar registrar nombres de medicamentos con caracteres especiales (tildes, ñ).
          
    Args:
        log_path (str): Ruta relativa o absoluta donde se guardará el archivo de log 
                        (ej. 'logs/etl_cima.log').
        logger_name (str, opcional): Nombre de la instancia del logger para identificarlo 
                                     en los mensajes. Por defecto es "ETL_CIMA".
                        
    Returns:
        logging.Logger: Instancia del logger configurado y listo para ser usado 
                        en toda la aplicación.
    """
    if not os.path.exists(os.path.dirname(log_path)):
        os.makedirs(os.path.dirname(log_path))

    # Nombramos el logger dinámicamente
    logger = logging.getLogger(logger_name)
    
    # Evitamos añadir handlers duplicados si la función se llama varias veces por error
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(logging.INFO)

    # Añadimos encoding='utf-8' para forzar la codificación correcta y evitar fallos 
    # con textos en español o caracteres especiales del XML.
    handler = RotatingFileHandler(
        log_path, 
        maxBytes=5*1024*1024,  # 5 MB por archivo
        backupCount=5,         # Conserva 5 archivos históricos antes de borrar el más antiguo
        encoding='utf-8'       # <--- ESTA ES LA CLAVE DE ESTABILIDAD
    )
    
    # Formato estándar profesional: Fecha/Hora - Nombre - Nivel - Mensaje
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # Handler para consola (vital para ver ejecución en vivo o si se usa en contenedores Docker)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Acoplamos los canales de salida al logger principal
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Recupera una instancia de un logger por su nombre.
    
    Lógica:
        Se apoya en el patrón Singleton que implementa internamente la librería 
        'logging' de Python. Asume que setup_logger() ya ha configurado los handlers 
        globales al inicio del programa.
        
    Args:
        name (str): Nombre del logger que se desea recuperar.
        
    Returns:
        logging.Logger: Instancia del logger solicitado.
    """
    return logging.getLogger(name)