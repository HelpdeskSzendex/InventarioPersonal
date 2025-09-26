# Dockerfile

# Usamos una imagen oficial de Python como base
FROM python:3.11-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de requisitos para aprovechar el cache de Docker
COPY requirements.txt .

# Instalamos las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos de la aplicación al contenedor
COPY . .

# Exponemos el puerto que usa Streamlit
EXPOSE 8501

# El comando que se ejecutará para iniciar la aplicación
# El --server.address=0.0.0.0 es crucial para que funcione en la nube
CMD ["streamlit", "run", "Personal.py", "--server.port=8501", "--server.address=0.0.0.0"]