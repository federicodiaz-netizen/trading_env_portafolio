# Actualizador de Portafolio y Datos de Mercado en Tiempo Real para Excel

Este proyecto proporciona un script de Python para conectarse a una plataforma de Home Broker, obtener datos de mercado en tiempo real para varios instrumentos financieros y mostrarlos, junto con su portafolio personal, en una hoja de cálculo de Excel.

Se recomienda tener como base de conocimiento el uso de la planila EPGB Python de Sabro

## Recursos

SE utiliza como base la planilla EPGB metodo Python de Sabro 
beacons.ai/sabrofrehley
Tutorial de la planilla:
https://youtu.be/IjrW_CALF2c?si=UsK_YwxyPNMmJsQh

y utiliza la libreria pyhomebroker https://github.com/crapher/pyhomebroker


## Características

-   Se conecta a su cuenta de broker utilizando `pyhomebroker`.
-   Transmite datos en tiempo real de acciones, CEDEARs, bonos, opciones y más.
-   Obtiene y muestra las tenencias de su portafolio personal.
-   Agrega a la planilla una hoja "Portafolio" donde se pondran los datos en timepo real
-   Agrega a la planilla una hoja "GGAL_beta_live" la cual se actualizaran los lotes en tenencia en tiempo real (esto esta pensado para el intraday o para lo momentaneo para evitar el tiempo en cargar la posicion en la planilla)
-   Mantiene las hojas originales de la planilla para poder armar seguir usando como se usaba antes la hoja "GGAL" para el armado del swing o posicion de ejercicio.
-   Altamente configurable para seleccionar qué instrumentos seguir, es necesario cargar en la hoja "Tickers" los que quieres seguir.
-   Para mi comodidad he sacado del terminal los valores que se mostraban antes (que era redundante ya que en el excel se ven los datos) y hace un conteo del tiempo en conexion desde que se prende el script. por lo cual no se va a sobrecargar el terminal.

## Prerrequisitos

-   Python 3.7+
-   Microsoft Excel instalado.
-   Una cuenta en un Home Broker compatible.

## Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/federicodiaz-netizen/trading_env_portafolio.git
    cd trading_env_portafolio
    ```

2.  **Instala las librerías de Python requeridas:**
    Se recomienda utilizar un entorno virtual.
    ```bash
    pip install pyhomebroker xlwings pandas python-dotenv pyhomebroker
    ```

3.  **Parchar la libreria pyhomebroker (solo la carpeta online):**
    en el contenido esta una carpeta llamada "online" esta carpeta debes reemplazar donde este instalada tu libreria de pyhomebroker.
    Esto es debido a que la version anterior de pyhomebroker esta desactualizada y no conecta al broker en la parte portafolio.

## Configuración

1.  **Crea un archivo `.env`** en el directorio raíz del proyecto. Este archivo almacenará tus credenciales sensibles de forma segura.

2.  **Añade tus credenciales del broker** al archivo `.env`. que no se encuentra en este repositorio por seguridad, pero debe ser un archivo con estos datos
    ```
    HB_BROKER_ID="TU BROKER ID"
    HB_DNI="TU DNI"
    HB_USER="TU USUARIO"
    HB_PASS="TU CONTRASENA"
    ```
    Reemplaza los valores de ejemplo con tus credenciales reales.

## Uso

2.  **Ejecuta el script** desde tu terminal de spider (anaconda): esto te abrira el excel automaticamente.


3.  Si la conexión es exitosa, verás el mensaje `OK: ACTUALIZANDO INFORMACION` en la terminal.

4.  Tus hojas de Excel `HomeBroker` y `Portafolio` comenzarán a poblarse con datos en tiempo real.

## Descargo de Responsabilidad

Esta herramienta está destinada únicamente a fines educativos y personales. No es un consejo financiero. la modificacion de la libreria esta en version de prueba, por lo cual realizarlo bajo su responsabilidad.
Esta version beta fue testeada con el broker Matriz Byma Id 284. el uso en otros brokers se ira testeando proximamente y se ira actualizando.
