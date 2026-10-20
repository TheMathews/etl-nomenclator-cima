"""
Módulo: json_processor.py
Objetivo: Actuar como el motor de Transformación Intermedia (Transform) antes de la carga.
Lógica:   Recibe el flujo de datos "en bruto" extraído del XML y lo prepara para Oracle.
          Sus responsabilidades incluyen:
          1. Sanitizar generadores residuales creados por la evaluación perezosa (lazy) del XML.
          2. Generar una huella digital (Hash SHA-256) inmutable para cada registro.
          3. Agrupar los registros en lotes (chunks) para volcados masivos (bulk_insert).
          4. Traducir tipos de datos de Python (Booleanos, Diccionarios) a tipos 
             soportados nativamente por Oracle (Number, CLOB/JSON String).
"""

import json
import hashlib
import sys
import types # <--- Importante para detectar generadores
from typing import Generator, Dict, Any

class JsonProcessor:
    """
    Procesador y adaptador de estructuras de datos (Diccionarios Python) a formato Relacional.
    
    Attributes:
        logger (Logger): Instancia del sistema de trazas para documentar el proceso.
    """
    
    def __init__(self, logger):
        """
        Inicializa el procesador JSON.
        
        Args:
            logger (Logger): Objeto de log configurado en el orquestador principal.
        """
        self.logger = logger

    def sanitizar_registro(self, obj: Any) -> Any:
        """
        Recorre recursivamente un objeto para purgar generadores pendientes.
        
        Lógica:
            La librería 'xmlschema' en modo lazy a veces no evalúa listas complejas 
            inmediatamente, sino que inserta un 'Generador' dentro del diccionario. 
            Si intentamos hacer json.dumps() de un generador, el programa crashea. 
            Este método fuerza la evaluación de esos generadores convirtiéndolos 
            en listas estáticas serializables.
            
        Args:
            obj (Any): Cualquier estructura de datos (dict, list, string, generator...).
            
        Returns:
            Any: La misma estructura pero con todos sus generadores anidados resueltos.
        """
        if isinstance(obj, types.GeneratorType):
            return [self.sanitizar_registro(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: self.sanitizar_registro(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.sanitizar_registro(i) for i in obj]
        else:
            return obj

    def generar_hash_registro(self, registro: Dict[str, Any]) -> str:
        """
        Genera un Hash SHA-256 determinista del registro.
        
        Args:
            registro (Dict[str, Any]): El diccionario del medicamento o diccionario base,
                                       previamente sanitizado.
                                       
        Returns:
            str: Hash hexadecimal (ej. 'a1b2c3...').
        """
        # sort_keys=True es vital para que {"a":1, "b":2} y {"b":2, "a":1} den el mismo Hash.
        dict_str = json.dumps(registro, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(dict_str.encode('utf-8')).hexdigest()

    def estimar_tamano_mb(self, bytes_size: int) -> float:
        """
        Convierte bytes a Megabytes para el log de monitorización.
        
        Args:
            bytes_size (int): Tamaño en bytes.
            
        Returns:
            float: Tamaño en Megabytes redondeado a 2 decimales.
        """
        return round(bytes_size / (1024 * 1024), 2)

    def perfilar_y_enriquecer_stream(self, stream_generator: Generator) -> Generator:
        """
        Intercepta el flujo de datos del XML para enriquecer cada registro "al vuelo".
        
        Lógica:
            Al comportarse como un generador (yield), no rompe la cadena de streaming perezoso.
            Recibe 1 registro -> Lo limpia -> Le añade el Hash -> Lo envía -> Pide el siguiente.
            
        Args:
            stream_generator (Generator): El flujo de datos original proveniente de xml_handler.
            
        Yields:
            Dict[str, Any]: El registro sanitizado y con la clave nueva 'HASH_REGISTRO'.
        """
        contador = 0
        tamano_total_bytes = 0
        
        self.logger.info("Iniciando perfilado del Stream JSON...")

        for item in stream_generator:
            # xmlschema a veces devuelve una tupla (path, dict) en lugar de solo el dict
            if isinstance(item, tuple) and len(item) == 2:
                _, registro = item
            else:
                registro = item

            # 1. SANITIZAR EL REGISTRO ANTES DE NADA
            registro = self.sanitizar_registro(registro)

            contador += 1
            tamano_total_bytes += sys.getsizeof(str(registro))
            
            # Ahora el JSON.dumps interno no fallará gracias a la sanitización previa
            hash_fila = self.generar_hash_registro(registro)
            registro['HASH_REGISTRO'] = hash_fila
            
            # Imprimimos únicamente el primer registro como muestra para depuración
            if contador == 1:
                self.logger.info("=== ESTRUCTURA DEL PRIMER REGISTRO ===")
                self.logger.info(f"\n{json.dumps(registro, indent=4, ensure_ascii=False)[:1000]}...\n")
                self.logger.info("======================================")

            yield registro

        tamano_mb = self.estimar_tamano_mb(tamano_total_bytes)
        self.logger.info(f"Perfilado completado -> Total registros: {contador} | Tamaño estimado en RAM: {tamano_mb} MB")

    def agrupar_en_lotes(self, stream_generator: Generator, tamano_lote: int = 1000) -> Generator:
        """
        Agrupa el flujo continuo de registros en listas (lotes/chunks) de tamaño fijo.
        
        Lógica:
            Insertar en Oracle fila a fila es extremadamente lento. Agruparlos en 
            lotes de 1000 o 2000 permite usar 'executemany' (bulk insert), multiplicando 
            el rendimiento de carga por 100 sin saturar la RAM.
            
        Args:
            stream_generator (Generator): Flujo de registros enriquecidos.
            tamano_lote (int): Cantidad de registros por lote (Default: 1000).
            
        Yields:
            List[Dict]: Una lista que contiene 'tamano_lote' diccionarios.
        """
        lote = []
        for registro in stream_generator:
            lote.append(registro)
            if len(lote) == tamano_lote:
                yield lote
                lote = []
        # Si al final quedan registros sueltos (ej. 340 registros que no llegan a 1000), los emite.
        if lote:
            yield lote

    def preparar_registro_para_staging(self, registro: dict, campos_clob: list, mapa_campos: dict) -> dict:
        """
        Adapta estrictamente los tipos de datos de Python a las limitaciones de Oracle.
        
        Lógica:
            1. Traduce las claves usando el 'mapa_campos' del config.json.
            2. Oracle crashea (DPY-3002) si recibe un Dict o List de Python. Si el valor es complejo,
               se serializa a un String JSON para que Oracle lo guarde en una columna CLOB.
            3. Oracle no tiene tipo Booleano nativo real, se convierte True/False a 1/0.
            4. Se convierten strings vacíos ("") a None (NULL) para evitar fallos de tipo (ej. fechas vacías).
            
        Args:
            registro (dict): El registro a formatear.
            campos_clob (list): Lista de campos que se espera que sean nodos complejos (Informativo, 
                                la validación real se hace por tipo de dato).
            mapa_campos (dict): Diccionario de traducción de nombres de columnas.
            
        Returns:
            dict: Registro perfectamente alineado para ser inyectado en una sentencia INSERT de Oracle.
        """
        registro_adaptado = {}
        
        for clave_origen, valor in registro.items():
            # Traducimos la clave. Si no está en el mapa, se usa la original en minúsculas.
            clave_destino = mapa_campos.get(clave_origen, clave_origen).lower()
            
            # Sanitización de datos para compatibilidad con oracledb
            if isinstance(valor, (dict, list)):
                valor = json.dumps(valor, ensure_ascii=False, default=str)
            elif isinstance(valor, bool):
                valor = 1 if valor else 0
            elif valor == "":
                valor = None
                
            registro_adaptado[clave_destino] = valor
            
        return registro_adaptado