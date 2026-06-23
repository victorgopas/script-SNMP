import asyncio
import logging
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv

# 1. Configurar el archivo de log local
logging.basicConfig(
    filename='veeam_traps.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Salida por consola en vivo
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

IP_RECEPTOR = '0.0.0.0'
PUERTO_RECEPTOR = 162
COMMUNITY_STRING = 'MonitoreoBackupsIriego' 

# 2. Función que procesa las alertas cuando llegan
def cbFun(snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
    logging.info("--- Nueva Alerta SNMP Recibida ---")
    
    payload = {}
    for name, val in varBinds:
        oid = name.prettyPrint()
        value = val.prettyPrint()
        payload[oid] = value
        
    log_line = "Detalles: "
    for oid, val in payload.items():
        if "vbr" in oid or "VEEAM" in oid or any(x in val.lower() for x in ["success", "fail", "warning"]):
            log_line += f"[{oid.split('.')[-1]}: {val}] "
            
    logging.info(f"DATA_VEEAM -> {log_line if log_line != 'Detalles: ' else payload}")

# 3. Función principal asíncrona
async def main():
    logging.info(f"Iniciando receptor SNMP en {IP_RECEPTOR}:{PUERTO_RECEPTOR}...")
    logging.info(f"Comunidad esperada: {COMMUNITY_STRING}")
    
    snmpEngine = engine.SnmpEngine()

    # CORRECCIÓN DE MÉTODOS Y DOMINIOS PARA PYSNMP RECIENTE
    # Usamos open_server_mode (snake_case) y udp.DOMAIN_NAME_S como identificador estándar de dominio
    transport = udp.UdpAsyncioTransport().open_server_mode((IP_RECEPTOR, PUERTO_RECEPTOR))
    
    # El ID de dominio estándar para UDP sincrónico/asíncrono en la API core de pysnmp
    udp_domain_id = (1, 3, 6, 1, 6, 1, 1) # Identificador OID universal para SNMP sobre UDP
    
    config.add_transport(
        snmpEngine,
        udp_domain_id,
        transport
    )

    # Configurar la comunidad de seguridad (Sintaxis moderna)
    config.add_v1_system(snmpEngine, 'veeam-area', COMMUNITY_STRING)

    # Registrar el receptor de notificaciones
    ntfrcv.NotificationReceiver(snmpEngine, cbFun)

    logging.info("Receptor listo y escuchando traps de Veeam... (Presiona Ctrl+C para salir)")
    
    # Mantener el script vivo asíncronamente
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Servidor SNMP detenido manualmente.")
    except Exception as e:
        logging.error(f"Error crítico en el hilo de ejecución: {e}")