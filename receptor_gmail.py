import asyncio
import logging
import email
import re
import json
import os
from datetime import datetime, timezone
from aiosmtpd.controller import Controller

# Log interno de la consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')


# TO DO: seguridad
#IP_VEEAM_AUTORIZADA = "10.20.0.X" 


# Este será el archivo que vigilará Promtail o Logstash
ARCHIVO_LOG_JSON = "veeam_structured.log"

class ReceptorCorreosVeeam:
    async def handle_DATA(self, server, session, envelope):
        ip_cliente = session.peer[0]
        
        #if IP_VEEAM_AUTORIZADA != "10.20.0.X" and ip_cliente != IP_VEEAM_AUTORIZADA and ip_cliente != "127.0.0.1":
            #return '554 Access denied'

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

        # Guardar todo el cuerpo del correo de forma segura en una sola línea JSON
        detalles_limpios = " ".join(cuerpo_texto.split())[:500]  # Limitamos a los primeros 500 caracteres

        # Estructura JSON perfecta para Grafana Loki / ELK
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "datasource": "veeam_receiver",
            "ip_origen": ip_origen,
            "job_name": job_name,
            "status": status,
            "detalles": detalles_limpios
        }

        # Guardar en el archivo (Modo 'Append', una línea por JSON)
        with open(ARCHIVO_LOG_JSON, mode='a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")

        logging.info(f"NUEVO LOG JSON GENERADO -> {job_name} [{status}]")

async def main():
    handler = ReceptorCorreosVeeam()
    IP_LOCAL = "10.10.30.45" 
    PUERTO = 2525
    
    controller = Controller(handler, hostname=IP_LOCAL, port=PUERTO)
    controller.start()
    logging.info(f"Servidor SMTP preparado para Grafana en {IP_LOCAL}:{PUERTO}...")
    
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