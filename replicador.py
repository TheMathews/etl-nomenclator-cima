"""
Módulo: replicador.py
Objetivo: Sincronizar (replicar) las tablas maestras cargadas por la ETL hacia 
          todos los demás esquemas de la base de datos Oracle.
Lógica:   Data-Driven: Primero consulta la tabla de auditoría (etl_nomenclator) 
          para confirmar que la ETL principal terminó con éxito HOY. Si es así, 
          extrae la lista de tablas a replicar leyendo el 'script_base' de config.json 
          y procede con la replicación masiva (datos, PKs, Índices y Comentarios).
"""

import os
from utils.logger import setup_logger
from module.config_loader import ConfigLoader
from module.oracle_client import OracleClient

class ReplicadorOracle:
    def __init__(self):
        """Inicializa el replicador usando el ConfigLoader unificado del proyecto."""
        # 1. Configurar Logger exclusivo y con nombre propio
        self.logger = setup_logger('logs/replicacion.log', logger_name="REPLICADOR")
        self.logger.info("==============================================")
        self.logger.info("Iniciando proceso de Replicación de Nomenclátor")
        
        try:
            # 2. Usar el ConfigLoader para leer la configuración
            loader = ConfigLoader()
            self.config = loader.load('config/config.json')
            self.db_cfg = loader.load('config/credenciales.json')
            
            # MAGIA DRY: Leemos dinámicamente las tablas usando el atributo 'script_base'
            config_tablas = self.config.get('tablas', [])
            self.tablas_a_replicar = [t.get('script_base') for t in config_tablas if t.get('script_base')]
            
            self.logger.info(f"Se han identificado {len(self.tablas_a_replicar)} tablas para replicar según config.json.")
            
            # Detectamos el usuario leyendo exactamente tu estructura JSON anidada
            bbdd_config = self.db_cfg.get('BBDD', {})
            self.owner_origen = bbdd_config.get('usuario', 'DESCONOCIDO').upper()
            
        except Exception as e:
            self.logger.error(f"Error crítico al cargar archivos JSON: {str(e)}")
            raise

        # 3. Inicializar Cliente Oracle
        self.logger.info(f"Conectando a Oracle (Esquema origen: {self.owner_origen})...")
        self.db = OracleClient(
            cfg=self.db_cfg, 
            app_name="REPLICA_CIMA", 
            user_app="PYTHON_BATCH"
        )

    def etl_lista_para_replicar(self) -> bool:
        """Verifica si la ÚLTIMA ETL terminó con estado SUCCESS en el día de hoy."""
        self.logger.info("Verificando estado de la ETL en el log de Oracle...")
        
        query = """
            SELECT estado, es_hoy FROM (
                SELECT estado, 
                       CASE WHEN TRUNC(fecha_inicio) = TRUNC(SYSDATE) THEN 1 ELSE 0 END as es_hoy
                FROM etl_nomenclator
                ORDER BY id_ejecucion DESC
            ) WHERE ROWNUM = 1
        """
        
        try:
            resultado = self.db.execute_query_json(query)
            
            if not resultado['rows']:
                self.logger.warning("No hay histórico de ejecuciones en la tabla etl_nomenclator.")
                return False
                
            ultima_ejecucion = resultado['rows'][0]
            estado = ultima_ejecucion['ESTADO']
            es_hoy = ultima_ejecucion['ES_HOY']
            
            if estado == 'SUCCESS' and es_hoy == 1:
                self.logger.info("Luz verde: La ETL principal finalizó con éxito en el día de hoy.")
                return True
            elif estado != 'SUCCESS':
                self.logger.warning(f"Luz roja: La última ETL tiene estado '{estado}'. Se aborta la replicación.")
                return False
            elif es_hoy == 0:
                self.logger.warning("Luz roja: La última ETL exitosa no es de hoy. Ejecute el main.py primero.")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al consultar el estado de la ETL: {str(e)}")
            return False

    def obtener_esquemas_destino(self, owner_origen: str) -> list:
        """Devuelve la lista de esquemas donde hay que replicar (omitiendo sistemas)."""
        query = """
            SELECT USERNAME AS OWNER
            FROM ALL_USERS
            WHERE USERNAME <> :current_user
            AND USERNAME NOT IN (
                'ANONYMOUS', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 'DBSFWUSER', 'DBSNMP',
                'DIP', 'DVF', 'DVSYS', 'GGSYS', 'GSMADMIN_INTERNAL', 'GSMCATUSER',
                'GSMROOTUSER', 'GSMUSER', 'LBACSYS', 'MDDATA', 'MDSYS', 'OJVMSYS',
                'OLAPSYS', 'ORACLE_OCM', 'ORDDATA', 'ORDPLUGINS', 'ORDSYS', 'OUTLN',
                'REMOTE_SCHEDULER_AGENT', 'SI_INFORMTN_SCHEMA', 'SYS', 'SYSBACKUP',
                'SYSDG', 'SYSKM', 'SYSRAC', 'SYSTEM', 'SYS$UMF', 'WMSYS', 'XDB', 'XS$NULL'
            )
            ORDER BY USERNAME
        """
        resultado = self.db.execute_query_json(query, {'current_user': owner_origen})
        return [row['OWNER'] for row in resultado['rows']]

    def obtener_estructura_tabla(self, tabla: str, owner: str) -> dict:
        """Extrae PKs, Índices y Comentarios (Tabla y Columnas) de la tabla origen."""
        estructura = {
            "pk_columns": [], 
            "indices": {},
            "table_comment": None,
            "column_comments": {}
        }
        
        # A. Primary Key
        query_pk = """
            SELECT cols.column_name
            FROM all_constraints cons
            JOIN all_cons_columns cols ON cons.constraint_name = cols.constraint_name AND cons.owner = cols.owner
            WHERE cons.constraint_type = 'P' AND cons.table_name = :table_name AND cons.owner = :owner
            ORDER BY cols.position
        """
        res_pk = self.db.execute_query_json(query_pk, {'table_name': tabla, 'owner': owner})
        estructura["pk_columns"] = [row['COLUMN_NAME'] for row in res_pk['rows']]

        # B. Índices
        query_idx = """
            SELECT i.index_name, c.column_name
            FROM all_indexes i
            JOIN all_ind_columns c ON i.index_name = c.index_name AND i.owner = c.index_owner
            WHERE i.table_name = :table_name AND i.owner = :owner
              AND i.index_name NOT IN (
                  SELECT constraint_name FROM all_constraints 
                  WHERE constraint_type = 'P' AND table_name = :table_name AND owner = :owner
              )
            ORDER BY i.index_name, c.column_position
        """
        res_idx = self.db.execute_query_json(query_idx, {'table_name': tabla, 'owner': owner})
        for row in res_idx['rows']:
            idx_name = row['INDEX_NAME']
            if idx_name not in estructura["indices"]:
                estructura["indices"][idx_name] = []
            estructura["indices"][idx_name].append(row['COLUMN_NAME'])
            
        # C. Comentario de la Tabla
        query_tab_comment = """
            SELECT comments FROM all_tab_comments
            WHERE table_name = :table_name AND owner = :owner
        """
        res_tc = self.db.execute_query_json(query_tab_comment, {'table_name': tabla, 'owner': owner})
        if res_tc['rows'] and res_tc['rows'][0]['COMMENTS']:
            estructura["table_comment"] = res_tc['rows'][0]['COMMENTS']

        # D. Comentarios de las Columnas
        query_col_comment = """
            SELECT column_name, comments FROM all_col_comments
            WHERE table_name = :table_name AND owner = :owner AND comments IS NOT NULL
        """
        res_cc = self.db.execute_query_json(query_col_comment, {'table_name': tabla, 'owner': owner})
        for row in res_cc['rows']:
            estructura["column_comments"][row['COLUMN_NAME']] = row['COMMENTS']
            
        return estructura

    def procesar(self):
        """Metodo orquestador principal de la replicación."""
        if not self.tablas_a_replicar:
            self.logger.warning("No se encontraron tablas configuradas ('script_base') en config.json. Abortando.")
            return

        if self.owner_origen == 'DESCONOCIDO' or not self.owner_origen:
            self.logger.error("No se pudo determinar el usuario de Oracle en credenciales.json. Verifica la clave 'usuario' dentro de 'BBDD'.")
            return

        esquemas_destino = self.obtener_esquemas_destino(self.owner_origen)
        self.logger.info(f"Esquemas destino encontrados: {len(esquemas_destino)}")

        try:
            for tabla in self.tablas_a_replicar:
                tabla = tabla.upper()
                self.logger.info(f"--- Procesando tabla origen: {self.owner_origen}.{tabla} ---")
                
                check_query = f"SELECT COUNT(*) as TOTAL FROM ALL_TABLES WHERE TABLE_NAME = :tabla AND OWNER = :owner"
                res_check = self.db.execute_query_json(check_query, {'tabla': tabla, 'owner': self.owner_origen})
                
                if res_check['rows'][0]['TOTAL'] == 0:
                    self.logger.error(f"Saltando {tabla}: No existe en el esquema origen.")
                    continue

                estructura = self.obtener_estructura_tabla(tabla, self.owner_origen)

                for owner_dest in esquemas_destino:
                    self.logger.info(f"  -> Replicando en esquema: {owner_dest}")
                    
                    check_dest = self.db.execute_query_json(check_query, {'tabla': tabla, 'owner': owner_dest})
                    if check_dest['rows'][0]['TOTAL'] > 0:
                        self.logger.info(f"     Eliminando versión antigua...")
                        try:
                            self.db.execute_dml(f"DROP TABLE {owner_dest}.{tabla} CASCADE CONSTRAINTS")
                        except Exception as drop_err:
                            self.logger.warning(f"     Aviso al hacer DROP: {str(drop_err)}")

                    self.logger.info(f"     Volcando datos...")
                    self.db.execute_dml(f"CREATE TABLE {owner_dest}.{tabla} AS SELECT * FROM {self.owner_origen}.{tabla}")

                    if estructura["pk_columns"]:
                        pk_cols = ", ".join(estructura["pk_columns"])
                        pk_name = f"PK_{owner_dest[:5]}_{tabla[:20]}" 
                        self.logger.info(f"     Restaurando Primary Key...")
                        self.db.execute_dml(f"ALTER TABLE {owner_dest}.{tabla} ADD CONSTRAINT {pk_name} PRIMARY KEY ({pk_cols})")

                    idx_contador = 1
                    for idx_name_origen, idx_cols_list in estructura["indices"].items():
                        idx_cols = ", ".join(idx_cols_list)
                        idx_name = f"IDX_{owner_dest[:5]}_{tabla[:18]}_{idx_contador}"
                        self.logger.info(f"     Restaurando Índice {idx_contador}...")
                        self.db.execute_dml(f"CREATE INDEX {owner_dest}.{idx_name} ON {owner_dest}.{tabla} ({idx_cols})")
                        idx_contador += 1
                        
                    # Restaurar Comentarios de Tabla
                    if estructura["table_comment"]:
                        # Escapamos comillas simples para evitar fallos de sintaxis SQL
                        safe_comment = estructura["table_comment"].replace("'", "''")
                        self.logger.info(f"     Restaurando Comentario de Tabla...")
                        self.db.execute_dml(f"COMMENT ON TABLE {owner_dest}.{tabla} IS '{safe_comment}'")
                        
                    # Restaurar Comentarios de Columnas
                    if estructura["column_comments"]:
                        self.logger.info(f"     Restaurando Comentarios de Columnas ({len(estructura['column_comments'])} detectados)...")
                        for col, comment in estructura["column_comments"].items():
                            safe_comment = comment.replace("'", "''")
                            self.db.execute_dml(f"COMMENT ON COLUMN {owner_dest}.{tabla}.{col} IS '{safe_comment}'")
                        
            self.logger.info("Proceso de Replicación global completado exitosamente.")

        except Exception as e:
            self.logger.error(f"Error crítico durante la replicación: {str(e)}")
        finally:
            self.db.close()


if __name__ == '__main__':
    replicador = ReplicadorOracle()
    
    if replicador.etl_lista_para_replicar():
        replicador.procesar()
        print("\n[OK] Replicación completada con éxito. Revisa logs/replicacion.log")
    else:
        print("\n[ABORTADO] La ETL principal no está completada hoy o terminó con error.")