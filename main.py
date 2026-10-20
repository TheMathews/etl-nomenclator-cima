"""
Módulo: main.py
Objetivo: Orquestador principal del proceso ETL/ELT del Nomenclátor de CIMA.
Lógica:   Implementa un patrón ELT (Extract, Load, Transform) Data-Driven con Idempotencia Lógica:
          1. Extract (Python): Descarga el ZIP y extrae XMLs masivos por streaming.
          2. Logical Check (Python): Compara el Hash Lógico (JSON) para evitar cargas innecesarias.
          3. Load (Python -> Oracle): Adapta los tipos de datos y hace un volcado 
             masivo (bulk_insert) ciego hacia tablas temporales (Staging).
          4. Transform (Oracle SQL): Lanza scripts SQL para que la base de datos 
             haga el cruce pesado (Nuevos, Modificados, Bajas, Reactivaciones).
"""

import os
import shutil
import hashlib
import json
from datetime import datetime
from utils.logger import setup_logger
from utils.file_utils import calcular_hash_fichero, leer_script_sql
from module.config_loader import ConfigLoader
from module.extractor import download_cima_zip
from module.oracle_client import OracleClient
from module.zip_handler import ZipHandler
from module.xml_handler import XmlHandler
from module.json_processor import JsonProcessor

class CimaETL:
    """
    Controlador principal de la carga del Nomenclátor.
    Gestiona el ciclo de vida completo: Inicialización, Extracción, Carga, 
    Transformación, Auditoría y Limpieza.
    """
    def __init__(self):
        """Inicializa los componentes leyendo la configuración y conectando a base de datos."""
        loader = ConfigLoader()
        self.config = loader.load('config/config.json')
        self.credenciales = loader.load('config/credenciales.json')
        
        self.logger = setup_logger(self.config.get('log_file', 'logs/etl_cima.log'))
        self.url = self.config.get('url_cima')
        self.temp_dir = self.config.get('path_temp', 'temp/')
        self.user_agent = self.config.get('user_agent', 'Mozilla/5.0') # Nuevo parámetro

        self.db = OracleClient(
            cfg=self.credenciales, 
            app_name="ETL_CIMA", 
            user_app="PYTHON_BATCH"
        )
        self.logger.info(f"Inicializando cliente Oracle v{self.db.__version__} ({self.db.__build_date__}) y manejadores...")

        self.xml_handler = XmlHandler(self.logger, self.user_agent, self.temp_dir)
        self.json_processor = JsonProcessor(self.logger)

    def calcular_hash_logico(self, datos_lista, clave_primaria):
        """Calcula un hash SHA-256 basado en el contenido lógico del XML (ignora espacios y metadatos)."""
        if not datos_lista:
            return None
        datos_ordenados = sorted(datos_lista, key=lambda x: str(x.get(clave_primaria, '')))
        datos_limpios = [{k: v for k, v in d.items() if k != "HASH_REGISTRO"} for d in datos_ordenados]
        json_str = json.dumps(datos_limpios, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    # ==========================================
    # MÉTODOS DE AUDITORÍA Y CABECERA BBDD
    # ==========================================
    def check_if_zip_processed(self, file_hash: str) -> bool:
        """Verifica si el ZIP actual ya fue cargado con éxito previamente (Idempotencia Global)."""
        query = "SELECT estado FROM etl_nomenclator WHERE fichero_hash = :hash AND estado = 'SUCCESS'"
        result = self.db.execute_query(query, {"hash": file_hash})
        if not result["success"]:
            raise Exception(f"Fallo al consultar la BD: {result.get('error')}")
        return result["rowcount"] > 0

    def iniciar_ejecucion(self, file_hash: str) -> int:
        """Registra el inicio de una nueva ejecución global y devuelve su ID."""
        query_insert = "INSERT INTO etl_nomenclator (fichero_hash, estado) VALUES (:hash, 'PROCESSING')"
        self.db.execute_dml(query_insert, {"hash": file_hash})
        query_id = "SELECT MAX(id_ejecucion) AS id FROM etl_nomenclator WHERE fichero_hash = :hash"
        res = self.db.execute_query_json(query_id, {"hash": file_hash})
        return res["rows"][0]["ID"]

    def finalizar_ejecucion(self, id_ejecucion: int, estado: str, registros: int = 0, error_msg: str = None, fecha_datos: str = None):
        """Cierra la ejecución global actualizando sus métricas finales y estado."""
        query = """
        UPDATE etl_nomenclator 
        SET estado = :estado, registros_insertados = :registros, 
            error_log = :error_msg, fecha_fin = CURRENT_TIMESTAMP, fecha_datos = :fecha_datos
        WHERE id_ejecucion = :id
        """
        self.db.execute_dml(query, {
            "estado": estado, "registros": registros, 
            "error_msg": error_msg, "fecha_datos": fecha_datos, "id": id_ejecucion
        })

    def check_if_file_processed(self, nombre_fichero: str, marca_control: str, hash_logico: str = None) -> bool:
        """Verifica si un fichero XML específico ya ha sido cargado sin cambios (Idempotencia Parcial)."""
        query = """
        SELECT estado FROM etl_nomenclator_ficheros_procesados 
        WHERE nombre_fichero = :nombre 
        AND (marca_control = :marca OR hash_logico = :hash_l)
        AND estado = 'SUCCESS'
        """
        result = self.db.execute_query(query, {
            "nombre": nombre_fichero, "marca": marca_control, "hash_l": hash_logico
        })
        return result["rowcount"] > 0

    def log_fichero(self, id_ejecucion: int, nombre_fichero: str, marca: str, hash_l: str, tipo_marca: str, estado: str, 
                    registros: int = 0, nuevos: int = 0, actualizados: int = 0, borrados: int = 0, reactivados: int = 0, error_msg: str = None):
        """Registra en BD el resultado detallado de las transformaciones relacionales de un XML concreto."""
        query = """
        INSERT INTO etl_nomenclator_ficheros_procesados 
        (id_ejecucion, nombre_fichero, marca_control, hash_logico, tipo_control, estado, 
         registros_procesados, registros_nuevos, registros_actualizados, registros_borrados, registros_reactivados, error_log) 
        VALUES (:id_ejec, :nombre, :marca, :hash_l, :tipo, :estado, 
                :registros, :nuevos, :actualizados, :borrados, :reactivados, :error_msg)
        """
        self.db.execute_dml(query, {
            "id_ejec": id_ejecucion, "nombre": nombre_fichero, "marca": marca, "hash_l": hash_l,
            "tipo": tipo_marca, "estado": estado, "registros": registros, 
            "nuevos": nuevos, "actualizados": actualizados, 
            "borrados": borrados, "reactivados": reactivados, "error_msg": error_msg
        })
    # ==========================================

    def obtener_columnas_staging(self, tabla_staging: str) -> list:
        """Consulta dinámicamente al diccionario de Oracle las columnas que tiene la tabla temporal."""
        query = f"SELECT lower(column_name) AS col FROM user_tab_columns WHERE table_name = '{tabla_staging.upper()}'"
        res = self.db.execute_query_json(query)
        todas_columnas = [r['COL'] for r in res['rows']]
        excluir = ['fcreacion', 'fmodificacion', 'fborrado', 'ucreacion', 'umodificacion', 'uborrado']
        return [c for c in todas_columnas if c not in excluir]

    def generar_query_insert_seguro(self, tabla_staging: str, columnas_validas: list) -> str:
        """Construye un INSERT statement de Oracle usando Bind Variables por seguridad y rendimiento."""
        columnas_str = ", ".join(columnas_validas)
        binds_str = ", ".join([f":{col}" for col in columnas_validas])
        return f"INSERT INTO {tabla_staging} ({columnas_str}) VALUES ({binds_str})"

    def ejecutar_script_sql(self, script_name: str) -> int:
        """Lee un archivo .sql del proyecto y lo ejecuta en Oracle devolviendo filas afectadas."""
        ruta_script = os.path.join('sql', script_name)
        query = leer_script_sql(ruta_script)
        resultado = self.db.execute_dml(query)
        return resultado.get("rowcount", 0)

    def run(self):
        """
        Flujo de ejecución principal de la ETL.
        Orquesta la descarga, iteración sobre configuraciones, volcados masivos e invocaciones SQL.
        """
        self.logger.info("========================================")
        self.logger.info("Iniciando proceso ETL CIMA (Motor ELT Oracle con Idempotencia Lógica)...")
        id_ejecucion = None
        
        try:
            # 1. EXTRACCIÓN GLOBAL
            zip_path, zip_hash = download_cima_zip(self.url, self.temp_dir, self.logger, self.user_agent)
            if self.check_if_zip_processed(zip_hash):
                self.logger.warning(f"El ZIP no tiene modificaciones. Abortando ETL.")
                return 

            id_ejecucion = self.iniciar_ejecucion(zip_hash)

            # 2. VALIDACIÓN DEL ZIP
            zip_manager = ZipHandler(zip_path)
            config_tablas = self.config.get('tablas', [])
            ficheros_esperados = [t['fichero_xml'] for t in config_tablas]
            
            faltantes, nuevos_zip = zip_manager.compare_with_expected(ficheros_esperados)
            if faltantes:
                raise Exception(f"Faltan ficheros vitales en el ZIP: {faltantes}")

            zip_manager.extract_files(self.temp_dir, ficheros_esperados)

            total_registros_insertados = 0
            fecha_global_prescripcion = None

            # 3. PROCESAMIENTO GENÉRICO POR CADA TABLA CONFIGURADA
            for tabla_cfg in config_tablas:
                archivo = tabla_cfg['fichero_xml']
                script_base = tabla_cfg['script_base']
                tabla_staging = tabla_cfg['tabla_staging']
                campos_clob = tabla_cfg.get('campos_clob', [])
                mapa_campos = tabla_cfg.get('mapa_campos', {})
                
                clave_primaria_xml = next((k for k, v in mapa_campos.items() if v == "id"), None)
                ruta_completa = os.path.join(self.temp_dir, archivo)
                
                # A. Marcas de Control (Idempotencia)
                if archivo == "Prescripcion.xml":
                    marca = self.xml_handler.obtener_fecha_prescripcion(ruta_completa)
                    tipo_marca = "FECHA"
                    fecha_global_prescripcion = marca 
                else:
                    marca = calcular_hash_fichero(ruta_completa)
                    tipo_marca = "HASH"
                
                # B. Perfilado y cálculo de Hash Lógico en memoria
                self.logger.info(f"Analizando contenido lógico de {archivo}...")
                xml_result = self.xml_handler.convertir_xml_a_stream_json(ruta_completa)
                stream_enriquecido = self.json_processor.perfilar_y_enriquecer_stream(xml_result["stream"])
                datos_lista = list(stream_enriquecido)
                
                hash_logico = self.calcular_hash_logico(datos_lista, clave_primaria_xml or 'id')
                self.logger.info(f"Hash Lógico calculado para {archivo}: {hash_logico}")

                if self.check_if_file_processed(archivo, marca, hash_logico):
                    self.logger.info(f"Omitiendo {archivo}: Contenido idéntico detectado.")
                    self.log_fichero(id_ejecucion, archivo, marca, hash_logico, tipo_marca, "SKIPPED")
                    continue

                self.logger.info(f"Procesando {archivo} -> Staging: {tabla_staging}")
                try:
                    # C1. CREAR STAGING
                    self.logger.info(f"[{script_base}] 1. Creando tabla Staging ({tabla_staging})...")
                    self.ejecutar_script_sql(f"{script_base}_STAGING_CREATE.sql")
                    
                    # C2. VOLCADO MASIVO A STAGING (Load)
                    self.logger.info(f"[{script_base}] 2. Volcando datos masivos a Oracle...")
                    columnas_validas = self.obtener_columnas_staging(tabla_staging)
                    query_insert = self.generar_query_insert_seguro(tabla_staging, columnas_validas)
                    
                    lotes = [datos_lista[i:i + 2000] for i in range(0, len(datos_lista), 2000)]
                    registros_procesados = 0

                    for lote in lotes:
                        lote_adaptado = []
                        for r in lote:
                            r_procesado = self.json_processor.preparar_registro_para_staging(r, campos_clob, mapa_campos)
                            
                            # Alineamiento Estricto: Solo pasamos a Oracle columnas que existan en BD
                            r_alineado = {}
                            for col in columnas_validas:
                                valor = r_procesado.get(col, None)
                                # Conversión forzada a NULL si es string vacío
                                if valor == "":
                                    valor = None
                                
                                # Binding nativo de fechas para evitar error ORA-01861 en Oracle
                                if isinstance(valor, str) and len(valor) == 10 and valor.count('-') == 2:
                                    try:
                                        valor = datetime.strptime(valor, "%Y-%m-%d").date()
                                    except ValueError:
                                        pass 
                                        
                                r_alineado[col] = valor
                                
                            lote_adaptado.append(r_alineado)
                        
                        self.db.bulk_insert(query_insert, lote_adaptado)
                        registros_procesados += len(lote)
                    
                    self.logger.info(f"Volcado completado -> Insertados TMP: {registros_procesados}")

                    # C3. EJECUCIÓN DE LÓGICA RELACIONAL (Transform en Base de Datos)
                    self.logger.info(f"[{script_base}] 3. Insertando nuevos registros en tabla final...")
                    nuevos = self.ejecutar_script_sql(f"{script_base}_INSERT.sql")

                    self.logger.info(f"[{script_base}] 4. Procesando bajas lógicas...")
                    borrados = self.ejecutar_script_sql(f"{script_base}_DROP_LOGIC.sql") 

                    self.logger.info(f"[{script_base}] 5. Reactivando registros antiguos...")
                    reactivados = self.ejecutar_script_sql(f"{script_base}_REVERTIR.sql")

                    self.logger.info(f"[{script_base}] 6. Actualizando registros modificados...")
                    actualizados = self.ejecutar_script_sql(f"{script_base}_UPDATE.sql")

                    self.logger.info(f"[{script_base}] 7. Limpiando tabla Staging...")
                    self.ejecutar_script_sql(f"{script_base}_STAGING_DROP.sql")
                    
                    self.logger.info(f"Resumen {script_base}: {nuevos} Nuevos | {actualizados} Modificados | {borrados} Borrados | {reactivados} Reactivados")

                    total_registros_insertados += registros_procesados
                    
                    # Cierre transaccional del fichero
                    self.log_fichero(
                        id_ejecucion, archivo, marca, hash_logico, tipo_marca, "SUCCESS", 
                        registros=registros_procesados, nuevos=nuevos, actualizados=actualizados,
                        borrados=borrados, reactivados=reactivados
                    )
                
                except Exception as ex_file:
                    self.logger.error(f"Error procesando {archivo}: {str(ex_file)}")
                    self.log_fichero(
                        id_ejecucion, archivo, marca, hash_logico, tipo_marca, "FAILED", 
                        registros=0, nuevos=0, actualizados=0, borrados=0, reactivados=0, 
                        error_msg=str(ex_file)
                    )
                    raise Exception(f"La carga del fichero {archivo} ha fallado.")

            # 4. CIERRE GLOBAL
            self.finalizar_ejecucion(id_ejecucion, "SUCCESS", total_registros_insertados, fecha_datos=fecha_global_prescripcion)

        except Exception as e:
            self.logger.error(f"Error crítico en la ETL: {str(e)}")
            if id_ejecucion:
                self.finalizar_ejecucion(id_ejecucion, "FAILED", error_msg=str(e))
        finally:
            # Limpieza del disco duro
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.db.close()

if __name__ == "__main__":
    etl = CimaETL()
    etl.run()