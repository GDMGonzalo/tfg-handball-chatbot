# Estructura de carpetas
- App: Contiene la aplicación web con la arquitectura MVC
- model: Contiene el modelo Deep-EIoU, recibe los parámetros mediante una API en Flask
- postprocess: Contiene el algoritmo GTA, recibe los parámetros mediante una API en Flask

# Manual de instalación y ejecución

## Requisitos previos
Para la correcta ejecución de la aplicación se requiere la instalación de los siguientes componentes:

- Git: herramienta necesaria para clonar el repositorio del proyecto. Puede descargarse desde https://git-scm.com/downloads
- Conda: (Anaconda o Miniconda) utilizada para la gestión de entornos virtuales. Descargas disponibles en https://docs.conda.io/en/latest/miniconda.html y https://www.anaconda.com/download
- XAMPP: paquete que incluye MySQL/MariaDB y phpMyAdmin, requerido para la gestión de la base de datos. Disponible en https://www.apachefriends.org/es/index.html
- Drivers NVIDIA y CUDA: necesarios únicamente en caso de utilizar GPU con PyTorch. Disponibles en https://developer.nvidia.com/cuda-downloads

---

## Clonación del repositorio
En primer lugar, se clona el repositorio y se accede a la carpeta del proyecto:

git clone https://github.com/Ivanlpc/app-tfg
cd app-tfg

---

## Creación de entornos Conda
Se crean tres entornos virtuales, cada uno con una versión específica de Python:

conda create -n app python=3.10
conda create -n model python=3.7
conda create -n postprocess python=3.8

En sistemas Windows se deberán abrir tres instancias de Anaconda Prompt, mientras que en Linux bastará con tres terminales distintas. Posteriormente se activan los entornos:

- Terminal 1: conda activate app
- Terminal 2: conda activate model
- Terminal 3: conda activate postprocess

---

## Uso de GPU
En caso de disponer de una GPU compatible, se puede comprobar su disponibilidad ejecutando en PowerShell:

nvidia-smi

El comando muestra la versión de CUDA instalada. Según la documentación de PyTorch, se instalan los paquetes adecuados.

### Ejemplo con CUDA 12.8

- Terminal model:
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

- Terminal postprocess:
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

Si no se desea utilizar GPU, se procede a la instalación de PyTorch para CPU en ambas terminales:

pip install torch torchvision

---

## Instalación de dependencias
Las dependencias necesarias se instalan en cada entorno siguiendo los pasos descritos:

- Terminal app:
  cd app-tfg/app
  pip install -r requirements.txt

- Terminal model:
  cd app-tfg/model
  cd reid
  pip install -r requirements.txt
  pip install https://github.com/KaiyangZhou/deep-person-reid/archive/master.zip
  cd ..

- Terminal postprocess:
  cd app-tfg/postprocess
  pip install -r requirements
  pip install https://github.com/KaiyangZhou/deep-person-reid/archive/master.zip

---

## Carga de pesos del modelo
Los pesos de los modelos se encuentran en la carpeta de Google Drive disponible en el siguiente enlace:
https://drive.google.com/drive/folders/1euv4tgcilZfMnJgFKmCJ6UKcaZ7TRnjh?usp=sharing

Se ofrecen dos versiones:
- Modelo ReID entrenado sobre el dataset SportsMOT
- Modelo ReID entrenado con vídeos propios

Los archivos deben colocarse en las siguientes rutas:

- model/checkpoints/best_ckpt.pth.tar
- model/checkpoints/sports_model.pth.tar-60
- postprocess/reid_checkpoints/sports_model.pth.tar-60

---

## Base de datos
La base de datos utilizada es MySQL, incluida en el paquete XAMPP.

### Inicio de XAMPP
1. Abrir el Panel de Control de XAMPP
2. Iniciar el servicio MySQL
3. Opcionalmente, iniciar Apache para acceder a phpMyAdmin

### Acceso a phpMyAdmin
- Pulsar el botón Admin en la fila correspondiente a MySQL.
- También se puede acceder mediante navegador en la URL:
  http://localhost/phpmyadmin/

### Importación de la base de datos
1. En phpMyAdmin, acceder a la pestaña Importar.
2. Seleccionar el archivo restore.sql incluido en el proyecto.
3. Pulsar Continuar para ejecutar el script de creación de tablas.

---

## Ejecución de la aplicación
Finalmente, una vez instaladas las dependencias y configurada la base de datos, se ejecuta la aplicación. En cada una de las tres terminales abiertas (app, model y postprocess) se ejecuta:

python app.py



## Otra forma de ejecución (opcinal)
Si queremos ejecutar el proyecto sin realizar todos los pasos anteriores, podemos simplemente abrir una terminal con docker instalado y ejecutar el siguiente comando en la raíz del proyecto:

docker-compose up -d --build