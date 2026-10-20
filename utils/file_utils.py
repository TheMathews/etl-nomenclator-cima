"""
Módulo: file_utils.py
Objetivo: Proporcionar funciones de utilidad generales para operaciones de Entrada/Salida (I/O) 
          y manipulación de archivos físicos a nivel de sistema operativo.
Lógica:   Aísla operaciones comunes como el cálculo de huellas digitales de archivos y 
          la limpieza sintáctica de scripts SQL. Al ser un módulo independiente, puede 
          ser reutilizado en cualquier otro proyecto de la compañía sin dependencias.
"""

import hashlib
import os

def leer_script_sql(ruta_script: str) -> str:
    """
    Lee un archivo .sql del disco y sanitiza su sintaxis para ser compatible 
    con el driver de conexión a Oracle (oracledb / cx_Oracle).
    
    Lógica:
        Existe una peculiaridad muy conocida al enviar SQL desde Python a Oracle:
        - Las queries estándar (INSERT, UPDATE, DROP) provocan el error 'ORA-00911: carácter no válido' 
          si terminan con punto y coma (';').
        - Sin embargo, los bloques PL/SQL anónimos (BEGIN ... END;) EXIGEN el punto y coma 
          en el END, pero suelen fallar si se incluye la barra inclinada ('/') que usan 
          editores como SQL Developer.
        Esta función detecta el tipo de script de forma inteligente y lo limpia dinámicamente.
    
    Args:
        ruta_script (str): Ruta relativa o absoluta hacia el archivo .sql.
        
    Returns:
        str: El string con la sentencia SQL lista para ser ejecutada por el cursor.
        
    Raises:
        FileNotFoundError: Si el script requerido no existe en el directorio especificado.
    """
    if not os.path.exists(ruta_script):
        raise FileNotFoundError(f"No se encuentra el script SQL requerido: {ruta_script}")

    with open(ruta_script, 'r', encoding='utf-8') as file:
        sql_content = file.read().strip()

    # Detectamos si es un bloque PL/SQL anónimo (suelen empezar por BEGIN o DECLARE)
    is_plsql = sql_content.upper().startswith(('BEGIN', 'DECLARE'))

    if is_plsql:
        # Si es PL/SQL, quitamos la barra '/' si existe al final, pero conservamos el 'END;'
        if sql_content.endswith('/'):
            sql_content = sql_content[:-1].strip()
    else:
        # Si es SQL estándar (INSERT, UPDATE, DROP), quitamos el ';' o la barra '/'
        if sql_content.endswith(';'):
            sql_content = sql_content[:-1]
        elif sql_content.endswith('/'):
            sql_content = sql_content[:-1]

    return sql_content

def calcular_hash_fichero(ruta_fichero: str) -> str:
    """
    Calcula la huella digital criptográfica (SHA-256) de un fichero físico en el disco duro.
    
    Lógica:
        Es la pieza clave de la IDEMPOTENCIA de la ETL. Antes de procesar un diccionario 
        (ej. Laboratorios.xml), se calcula su Hash y se compara con el log de la base de datos.
        Se utiliza lectura en bloques (chunks) de 4KB para evitar desbordamientos de memoria (RAM)
        si el archivo es gigantesco.
        
    Args:
        ruta_fichero (str): Ruta del fichero físico del que se quiere obtener la firma.
        
    Returns:
        str: Cadena hexadecimal de 64 caracteres con el Hash SHA-256.
    """
    sha256_hash = hashlib.sha256()
    with open(ruta_fichero, "rb") as f:
        # iter() con un 'sentinel' (b"") lee fragmentos hasta llegar al final del archivo
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest()

def existe_fichero(ruta_fichero: str) -> bool:
    """
    Verifica si un fichero físico existe en el disco duro.
    
    Args:
        ruta_fichero (str): Ruta absoluta o relativa al fichero.
        
    Returns:
        bool: True si el fichero existe y es un archivo, False en caso contrario.
    """
    return os.path.isfile(ruta_fichero)

def borrar_fichero(ruta_fichero: str, logger=None) -> bool:
    """
    Elimina un fichero del sistema de forma segura.
    
    Lógica:
        Comprueba primero si existe para evitar lanzar un FileNotFoundError.
        Captura posibles bloqueos del sistema operativo (archivo en uso).
        
    Args:
        ruta_fichero (str): Ruta del fichero a eliminar.
        logger (logging.Logger, opcional): Si se pasa un logger, registra el evento.
        
    Returns:
        bool: True si se borró con éxito (o no existía), False si hubo un error de SO.
    """
    if existe_fichero(ruta_fichero):
        try:
            os.remove(ruta_fichero)
            if logger:
                logger.info(f"Fichero eliminado con éxito: {ruta_fichero}")
            return True
        except OSError as e:
            if logger:
                logger.error(f"No se pudo borrar el fichero {ruta_fichero}. Motivo: {e.strerror}")
            return False
    return True # Si no existe, consideramos que el estado deseado (que no esté) se cumple.