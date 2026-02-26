# Usa una imagen oficial y ligera de Python como base
FROM python:3.11-slim

# Crea y establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requisitos primero para optimizar la construcción
COPY requirements.txt .

# Instala las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos los archivos de tu proyecto al contenedor
# (Personal.py, la carpeta pages/, la carpeta assets/, etc.)
COPY . .

# Expone el puerto por defecto de Streamlit
EXPOSE 8501

# El comando para arrancar la aplicación cuando se inicie el contenedor
# El --server.address=0.0.0.0 es crucial para que sea accesible desde fuera
CMD ["streamlit", "run", "Personal.py", "--server.port=8501", "--server.address=0.0.0.0"]