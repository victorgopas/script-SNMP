import asyncio
import logging
from logging.handlers import RotatingFileHandler
import email
import re
import json
import os
from datetime import datetime, timezone
from aiosmtpd.controller import Controller
import socket


# ==========================================
# 0. CONFIGURACIÓN DE CONSOLA (Para ver qué pasa en pantalla)
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS ESTÁNDAR
# ==========================================
BASE_DIR = r"C:\VeeamMonitor"
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "veeam_structured.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# ==========================================
# 2. CONFIGURACIÓN DEL SISTEMA DE LOGS (ROTACIÓN PARA GRAFANA)
# ==========================================
log_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=10 * 1024 * 1024, 
    backupCount=5
)
log_handler.setFormatter(logging.Formatter('%(message)s'))

# Usamos un logger específico "VeeamLogger" solo para el archivo JSON
json_logger = logging.getLogger("VeeamLogger")
json_logger.setLevel(logging.INFO)
json_logger.addHandler(log_handler)
# Evitar que el texto JSON crudo ensucie la pantalla negra
json_logger.propagate = False 

# ==========================================
# 3. FUNCIÓN PARA GENERAR Y GUARDAR EL JSON
# ==========================================
def guardar_log_veeam(ip_origen, job_name, status, detalles):
    # Generar la hora exacta en formato UTC compatible con Grafana/Loki
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    log_data = {
        "timestamp": timestamp,
        "datasource": "veeam_receiver",
        "ip_origen": ip_origen,
        "job_name": job_name,
        "status": status,
        "detalles": detalles
    }
    
    # Convertir a JSON y mandarlo exclusivamente al archivo rotativo
    json_string = json.dumps(log_data)
    json_logger.info(json_string)
    
    # Mostrar un mensaje limpio en la consola
    logging.info(f"NUEVO LOG GUARDADO -> {job_name} [{status}]")

# ==========================================
# 4. SERVIDOR SMTP (RECEPTOR)
# ==========================================
class ReceptorCorreosVeeam:
    async def handle_DATA(self, server, session, envelope):
        ip_cliente = session.peer[0]
        
        # TO DO: Seguridad (Descomentar cuando quieras filtrar IPs)
        # IP_VEEAM_AUTORIZADA = "10.20.0.X"
        # if ip_cliente != IP_VEEAM_AUTORIZADA and ip_cliente != "127.0.0.1":
        #     return '554 Access denied'

        raw_email = envelope.content.decode('utf-8', errors='replace')
        mensaje = email.message_from_string(raw_email)
        
        cuerpo = ""
        if mensaje.is_multipart():
            for part in mensaje.walk():
                if part.get_content_type() == "text/plain":
                    cuerpo = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            cuerpo = mensaje.get_payload(decode=True).decode('utf-8', errors='ignore')

        if cuerpo:
            self.procesar_a_json(cuerpo, ip_cliente)
            
        return '250 Message accepted for delivery'

    def procesar_a_json(self, cuerpo_texto, ip_origen):
        # Extraer datos con Regex
        job_match = re.search(r'(?:Replication job|Backup job|Agent.*?):\s*\n\s*(.+)', cuerpo_texto, re.IGNORECASE)
        job_name = job_match.group(1).strip() if job_match else "Desconocido"

        status_match = re.search(r'\b(Success|Warning|Error|Failed)\b', cuerpo_texto, re.IGNORECASE)
        status = status_match.group(1).strip().upper() if status_match else "UNKNOWN"

        # Limpiar detalles
        detalles_limpios = " ".join(cuerpo_texto.split())[:500]

        # Delegar el guardado a la función centralizada
        guardar_log_veeam(ip_origen, job_name, status, detalles_limpios)

async def main():
    handler = ReceptorCorreosVeeam()
    PUERTO = 2525
    
    # TRUCO MÁGICO: Auto-detecta la IP privada real de este servidor
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # No llega a enviar datos, solo mira qué IP usa el PC para salir
        IP_LOCAL = s.getsockname()[0]
        s.close()
    except Exception:
        IP_LOCAL = "127.0.0.1" # Por si el servidor no tuviera red en ese momento
    
    controller = Controller(handler, hostname=IP_LOCAL, port=PUERTO)
    controller.start()
    logging.info(f"Servidor SMTP preparado para Grafana en {IP_LOCAL}:{PUERTO}...")
    logging.info(f"Ruta de logs: {LOG_FILE}")
    
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        controller.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Servidor detenido manualmente.")