# Receptor SMTP para Alertas de Veeam Backup 🚀

Este repositorio contiene el script y la configuración necesaria para interceptar las alertas por correo electrónico de **Veeam Backup & Replication**, transformarlas en registros estructurados (JSON) en tiempo real y enviarlas a **Grafana Cloud** utilizando **Grafana Alloy**.

El sistema funciona de forma desacoplada y automatizada: el script recibe el correo, extrae los datos limpios, los escribe en un log rotativo local y el agente de Grafana se encarga de empujarlos a la nube de manera segura.

---

## 📂 Contenido del Repositorio
* **`receptor_gmail.py`**: El script principal. Actúa como un servidor SMTP ligero que escucha en el puerto `2525`, auto-detecta la IP del servidor, procesa el texto con expresiones regulares (`Regex`) y genera el archivo log.
* **`README.md`**: Esta guía de despliegue desde cero.

---

## 📋 Requisitos Previos del Servidor
Antes de arrancar el sistema en el nuevo equipo, asegúrate de cumplir con lo siguiente:
1. **Python 3.11 o superior**: Instalado en el sistema. 
   * *Nota crítica:* Durante la instalación de Python, asegúrate de marcar la casilla **"Add python.exe to PATH"**.
2. **Grafana Alloy**: El agente oficial de Grafana instalado en la máquina.
3. **Permisos de Administrador**: Para instalar dependencias y reiniciar servicios de Windows.
4. **Regla de Firewall**: Permitir tráfico entrante en el puerto `2525` (o el puerto configurado) para que el servidor de Veeam pueda comunicarse con este script.

---

## 🛠️ Pasos para el Despliegue desde Cero

### Paso 1: Ubicación del Repositorio
Para que las rutas del sistema y de Grafana Alloy coincidan perfectamente sin configuraciones extrañas, **copia los archivos de este repositorio directamente en la siguiente ruta de la raíz**:
La estructura final en el disco duro debe verse exactamente así:
C:\
└── VeeamMonitor\
    ├── logs\
        └── veeam_structured.log  <-- Se creará solo al recibir el primer correo


🔐 Permisos de Carpeta: Haz clic derecho sobre la carpeta C:\VeeamMonitor -> Propiedades -> Seguridad -> Editar. Otorga permisos de Control Total o Modificación al grupo Todos (o al usuario Local Service), ya que Grafana Alloy necesitará permisos para leer el archivo de logs que generará el script.

### Paso 2: Instalar Dependencias de Python

Abre una terminal de Windows (CMD o PowerShell) como Administrador y ejecuta el siguiente comando para instalar la librería encargada de la gestión de correos asíncronos:
PowerShell

*pip install aiosmtpd*


### Paso 3: Configurar Grafana Alloy

1. Instala Alloy
    
2. Abre el archivo de configuración del agente de Grafana en la máquina, ubicado por defecto en:
    C:\Program Files\Grafana Alloy\config.alloy

3. Borra todo su contenido y pega el contenido del archivo de configuracion template:
       
4. Reemplaza <TU_URL_DE_LOKI>, <TU_USUARIO_USER_ID> y <TU_API_TOKEN_CONTRASEÑA> con tus credenciales reales de Grafana Cloud (puedes obtenerlas en tu perfil de grafana.com).

5. Guarda el archivo y reinicia el servicio desde una consola de PowerShell como administrador para aplicar los cambios:
PowerShell
    *Restart-Service alloy*

## 🚀 Ejecución y Verificación

1. Arrancar el Receptor SMTP

Para iniciar el servicio, abre una terminal en la carpeta del proyecto y ejecuta:

*python receptor_gmail.py* 

El script auto-detectará la IP de la tarjeta de red de la máquina y mostrará el mensaje:
[INFO] Servidor SMTP preparado para Grafana en X.X.X.X:2525...

2. Simular una Alerta de Veeam (Prueba de Fuego)

Sin necesidad de abrir Veeam, puedes comprobar que todo el circuito funciona abriendo otra ventana de PowerShell y enviando un correo de prueba falso. Copia y pega este bloque (cambiando la IP por la que detectó tu script en el punto anterior):

$cuerpo = @"
Backup job: TRABAJO-DESPLIEGUE-OK
Success
1 of 1 tasks completed successfully. Data read: 120GB.
"@

Send-MailMessage -From "veeam@empresa.local" -To "grafana@empresa.local" -Subject "Veeam Alert" -Body $cuerpo -SmtpServer "TU_IP_DETECTADA" -Port 2525
