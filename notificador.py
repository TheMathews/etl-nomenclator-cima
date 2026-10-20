"""
Módulo: monitor.py
Objetivo: Auditar la ejecución diaria de la ETL del Nomenclátor en modo "Silencioso".
          Solo envía correo si detecta anomalías o si no se ha ejecutado hoy.
          Plantillas externalizadas, parámetros gestionados desde config y
          contexto enriquecido mediante Telemetría del servidor.
"""

import os
from datetime import datetime
from module.config_loader import ConfigLoader
from module.oracle_client import OracleClient
from utils.logger import setup_logger
from module.smtp_client import SMTPSender
from module.telemetry import TelemetryCollector  # <-- Importamos tu librería

class MonitorETL:
    def __init__(self):
        self.logger = setup_logger('logs/monitor.log', logger_name="MONITOR")
        
        # --- RECOLECCIÓN DE TELEMETRÍA ---
        try:
            self.logger.info("Recolectando telemetría del servidor...")
            telemetry_result = TelemetryCollector().collect_all()
            self.telemetry = telemetry_result.get("data", {}) if telemetry_result.get("success") else {}
        except Exception as e:
            self.logger.warning(f"Aviso: Fallo en el módulo de telemetría: {e}")
            self.telemetry = {}

        try:
            loader = ConfigLoader()
            self.config = loader.load('config/config.json')
            self.credenciales = loader.load('config/credenciales.json')
            
            self.db_cfg = self.credenciales.get('BBDD', {})
            self.smtp_cfg = self.credenciales.get('SMTP', {})
            
            self.max_log_mb = self.config.get('max_log_mb', 5.0)
            self.template_path = self.config.get('template_monitor_html', 'templates/alerta_monitor.html')
            
            # --- CONTEXTO ENRIQUECIDO ---
            # Si la telemetría nos da el hostname lo usamos, si no, lo dejamos en "Desconocido"
            self.maquina_ejecucion = self.telemetry.get('hardware', {}).get('hostname', 'Desconocido')
            self.servidor_bbdd = self.db_cfg.get('servidor', 'Desconocido')
            
            destinatarios_raw = self.config.get('email_notificaciones')
            if not destinatarios_raw:
                raise ValueError("No se ha definido 'email_notificaciones' en config.json")
                
            if isinstance(destinatarios_raw, list):
                self.destinatario = ", ".join(destinatarios_raw)
            else:
                self.destinatario = destinatarios_raw
                
        except Exception as e:
            self.logger.error(f"Error cargando configuraciones en el Monitor: {str(e)}")
            raise

        self.db = OracleClient(cfg=self.db_cfg, app_name="MONITOR_CIMA", user_app="PYTHON_BATCH")
        self.mailer = SMTPSender(self.smtp_cfg)

    def obtener_resumen_hoy(self) -> dict:
        query_global = """
            SELECT id_ejecucion, estado, registros_insertados, error_log, fecha_inicio, fecha_fin
            FROM etl_nomenclator
            WHERE TRUNC(fecha_inicio) = TRUNC(SYSDATE)
            ORDER BY id_ejecucion DESC
        """
        resultado = self.db.execute_query_json(query_global)
        
        if not resultado['rows']:
            return None
            
        ultima_ejec = resultado['rows'][0]
        id_ejec = ultima_ejec['ID_EJECUCION']
        
        query_detalle = """
            SELECT nombre_fichero, estado, registros_procesados, registros_nuevos, 
                   registros_actualizados, registros_borrados, error_log
            FROM etl_nomenclator_ficheros_procesados
            WHERE id_ejecucion = :id_ejec
            ORDER BY nombre_fichero
        """
        detalle = self.db.execute_query_json(query_detalle, {"id_ejec": id_ejec})
        
        ultima_ejec['FICHEROS'] = detalle['rows']
        return ultima_ejec

    def evaluar_anomalias(self, datos: dict) -> tuple:
        alertas = []
        hay_error = False

        if datos['ESTADO'] != 'SUCCESS':
            hay_error = True
            alertas.append(f"CRÍTICO: La ETL terminó con estado global '{datos['ESTADO']}'.")
            if datos['ERROR_LOG']:
                alertas.append(f"Motivo: {datos['ERROR_LOG']}")

        if datos['REGISTROS_INSERTADOS'] == 0 and datos['ESTADO'] == 'SUCCESS':
            todos_omitidos = all(f['ESTADO'] == 'SKIPPED' for f in datos['FICHEROS'])
            if todos_omitidos:
                alertas.append("INFO: El ZIP de CIMA no presentaba cambios hoy (0 registros nuevos).")
            else:
                hay_error = True
                alertas.append("ALERTA: Se procesó la ETL pero se insertaron 0 registros en Staging. Posible fallo en la extracción XML.")

        for f in datos['FICHEROS']:
            if f['ESTADO'] == 'FAILED':
                hay_error = True
                alertas.append(f"ERROR EN FICHERO: {f['NOMBRE_FICHERO']} falló. Detalle: {f['ERROR_LOG']}")
                
        return hay_error, alertas

    def generar_cuerpo_html(self, datos: dict, alertas: list, aviso_log_html: str = "") -> str:
        """Lee la plantilla externa y reemplaza las etiquetas con los datos reales y de telemetría."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as file:
                html = file.read()
        except Exception as e:
            self.logger.error(f"Fallo al leer la plantilla HTML {self.template_path}: {e}")
            return f"<h2>ALERTA ETL</h2><p>No se pudo cargar la plantilla HTML. Revise los logs.</p>"

        color_estado = "#28a745" if datos.get('ESTADO') == 'SUCCESS' else "#dc3545"
        
        # 1. Construir el bloque de alertas
        alertas_html = ""
        if alertas:
            alertas_html = '<div style="background-color: #f8d7da; color: #721c24; padding: 15px; border-left: 5px solid #f5c6cb; margin-bottom: 20px;">'
            alertas_html += '<h3 style="margin-top: 0;">⚠️ Fallos Detectados:</h3><ul>'
            for a in alertas:
                alertas_html += f"<li>{a}</li>"
            alertas_html += '</ul></div>'

        # 2. Construir las filas de la tabla de ficheros
        ficheros_html = ""
        if 'FICHEROS' in datos:
            for f in datos['FICHEROS']:
                color_fila = "#f5c6cb" if f['ESTADO'] == 'FAILED' else "#ffffff"
                ficheros_html += f"""
                    <tr style="background-color: {color_fila};">
                        <td style="padding: 8px; border: 1px solid #ddd;">{f['NOMBRE_FICHERO']}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{f['ESTADO']}</td>
                    </tr>
                """

        # 3. Extraer datos de telemetría de forma segura
        hw = self.telemetry.get("hardware", {})
        usr = self.telemetry.get("user", {})

        # 4. Reemplazar las etiquetas en la plantilla
        html = html.replace("{SERVIDOR_BBDD}", str(self.servidor_bbdd))
        html = html.replace("{MAQUINA_EJECUCION}", str(self.maquina_ejecucion))
        html = html.replace("{FECHA_INICIO}", str(datos.get('FECHA_INICIO', 'N/A')))
        html = html.replace("{FECHA_FIN}", str(datos.get('FECHA_FIN', 'N/A')))
        html = html.replace("{ESTADO}", str(datos.get('ESTADO', 'N/A')))
        html = html.replace("{COLOR_ESTADO}", color_estado)
        html = html.replace("{ALERTAS_HTML}", alertas_html)
        html = html.replace("{FICHEROS_HTML}", ficheros_html)
        html = html.replace("{AVISO_LOG_HTML}", aviso_log_html)
        
        # Etiquetas nuevas de Telemetría
        html = html.replace("{OS_NAME}", str(hw.get("os_name", "Desconocido")))
        html = html.replace("{IP_LOCAL}", str(hw.get("local_ip", "Desconocida")))
        html = html.replace("{USUARIO}", str(usr.get("username", "Desconocido")))
        html = html.replace("{RAM_MB}", str(hw.get("memory_mb", "N/A")))
        html = html.replace("{CPU}", str(hw.get("processor", "Desconocido")))

        return html

    def procesar(self):
        self.logger.info("Iniciando monitorización (Modo silencioso)...")
        
        try:
            datos_hoy = self.obtener_resumen_hoy()
            ruta_log = self.config.get('log_file', 'logs/etl_cima.log')
            
            # CONTROL DE TAMAÑO DEL LOG
            adjunto_final = None
            aviso_log_html = ""
            
            if os.path.exists(ruta_log):
                tamanio_mb = os.path.getsize(ruta_log) / (1024 * 1024)
                
                if tamanio_mb > self.max_log_mb:
                    self.logger.warning(f"El log ({tamanio_mb:.2f} MB) supera los {self.max_log_mb} MB permitidos. Envío sin adjunto.")
                    aviso_log_html = f"""
                    <div style='background-color: #fff3cd; color: #856404; padding: 15px; border-left: 5px solid #ffeeba; margin-top: 20px;'>
                        <strong>⚠️ Aviso sobre el Log:</strong> El archivo físico pesa <b>{tamanio_mb:.2f} MB</b>, 
                        superando el límite de {self.max_log_mb} MB. Acceda a la máquina <b>{self.maquina_ejecucion}</b> 
                        para revisar <code>{ruta_log}</code>
                    </div>
                    """
                else:
                    adjunto_final = ruta_log

            # CASO 1: NO ARRANCÓ HOY
            if not datos_hoy:
                self.logger.warning("No hay ejecuciones hoy. Disparando correo de alerta.")
                datos_falsos = {"ESTADO": "NO EJECUTADO", "FICHEROS": []}
                alertas = ["El proceso Batch no ha arrancado en el día de hoy. Posible caída del planificador de tareas."]
                cuerpo_html = self.generar_cuerpo_html(datos_falsos, alertas, aviso_log_html)
                
                self.mailer.enviar_correo(
                    destinatario=self.destinatario, 
                    asunto="[CRÍTICO] ETL CIMA No Ejecutada Hoy", 
                    cuerpo_html=cuerpo_html,
                    ruta_adjunto=adjunto_final
                )
                return

            hay_error, alertas = self.evaluar_anomalias(datos_hoy)
            
            # CASO 2: HUBO ERRORES EN LA EJECUCIÓN
            if hay_error:
                cuerpo_html = self.generar_cuerpo_html(datos_hoy, alertas, aviso_log_html)
                self.logger.error("Se detectaron anomalías. Disparando correo de alerta.")
                asunto = f"[ERROR] ETL CIMA ({self.servidor_bbdd}) finalizada con anomalías - {datetime.now().strftime('%d/%m/%Y')}"
                
                self.mailer.enviar_correo(self.destinatario, asunto, cuerpo_html, adjunto_final)
                
            # CASO 3: TODO PERFECTO (SILENCIO)
            else:
                self.logger.info("Ejecución perfecta. No se detectaron anomalías, por lo tanto NO se envía correo.")
                
        except Exception as e:
            self.logger.error(f"Fallo en el propio monitor: {str(e)}")
            fallo_html = f"<h2>Fallo Crítico en el Script de Monitorización</h2><p>Servidor: {self.servidor_bbdd}<br>Máquina: {self.maquina_ejecucion}<br>Error: {str(e)}</p>"
            self.mailer.enviar_correo(self.destinatario, "[CRÍTICO] Fallo en Monitor ETL CIMA", fallo_html)
        finally:
            self.db.close()
            self.logger.info("Monitorización finalizada.")

if __name__ == '__main__':
    monitor = MonitorETL()
    monitor.procesar()