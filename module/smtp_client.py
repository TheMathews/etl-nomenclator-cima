"""
module.smtp_client
==================
Módulo para el envío de correos electrónicos mediante SMTP con soporte SSL/TLS.
Permite el envío de notificaciones e informes en formato HTML, con soporte para adjuntos.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from utils.logger import get_logger

logger = get_logger("SMTPClient")

class SMTPSender:
    """Cliente para envío de correos electrónicos a través del puerto 465 (SSL Implícito)."""

    def __init__(self, config_smtp: dict):
        self.cfg = config_smtp

    def enviar_correo(self, destinatario: str, asunto: str, cuerpo_html: str, ruta_adjunto: str = None) -> dict:
        """Envía un correo en formato HTML, opcionalmente con un archivo adjunto."""
        logger.info(f"Preparando envío de correo a: {destinatario}")
        
        msg = MIMEMultipart()
        msg['From'] = self.cfg.get("sender_email", self.cfg.get("user"))
        msg['To'] = destinatario
        msg['Subject'] = asunto

        # 1. Adjuntamos el cuerpo HTML
        msg.attach(MIMEText(cuerpo_html, 'html'))

        # 2. Procesamos el archivo adjunto si se ha proporcionado uno
        if ruta_adjunto and os.path.exists(ruta_adjunto):
            try:
                with open(ruta_adjunto, "rb") as adjunto:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(adjunto.read())
                
                # Codificamos en Base64 para que viaje seguro por email
                encoders.encode_base64(part)
                
                # Extraemos solo el nombre del archivo, no toda la ruta de carpetas
                nombre_archivo = os.path.basename(ruta_adjunto)
                part.add_header("Content-Disposition", f"attachment; filename={nombre_archivo}")
                
                msg.attach(part)
                logger.info(f"Archivo adjunto añadido: {nombre_archivo}")
            except Exception as e:
                logger.error(f"Error al adjuntar archivo {ruta_adjunto}: {e}")
                # Podrías decidir abortar aquí, pero lo mejor es intentar enviarlo al menos sin adjunto

        # 3. Envío al servidor
        try:
            server = smtplib.SMTP_SSL(self.cfg.get("host"), self.cfg.get("port"))
            server.login(self.cfg.get("user"), self.cfg.get("password"))
            server.sendmail(msg['From'], destinatario, msg.as_string())
            server.quit()
            
            logger.info("Correo enviado con éxito.")
            return {"success": True, "error": None}
            
        except Exception as e:
            logger.error(f"Fallo al enviar correo a {destinatario}: {e}")
            return {"success": False, "error": str(e)}