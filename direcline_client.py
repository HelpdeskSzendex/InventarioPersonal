import requests
import xml.etree.ElementTree as ET
from datetime import datetime

class DireclineClient:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        # Headers necesarios para la petición SOAP [cite: 25]
        self.headers = {'Content-Type': 'text/xml; charset=utf-8'}

    def _get_guid(self):
        """
        Método 1: ValidarUsuario [cite: 32]
        Obtiene el token de sesión (GUID) necesario para el resto de operaciones.
        """
        # Estructura XML para el login según documentación [cite: 39-42]
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <ValidarUsuario xmlns="http://www.direcline.com/">
              <Nombre>{self.username}</Nombre>
              <Password>{self.password}</Password>
            </ValidarUsuario>
          </soap:Body>
        </soap:Envelope>"""
        
        try:
            response = requests.post(self.url, data=soap_body, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                # Parseamos la respuesta para extraer el GUID [cite: 41]
                root = ET.fromstring(response.text)
                
                # Buscamos el GUID recursivamente (con y sin namespace por seguridad)
                guid = root.find(".//{http://www.direcline.com/}GUID")
                if guid is None: 
                    guid = root.find(".//GUID")
                
                return guid.text if guid is not None else None
            else:
                print(f"Error HTTP al conectar con Direcline (Login): {response.status_code}")
                return None
        except Exception as e:
            print(f"Excepción en Login Direcline: {e}")
            return None

    def guardar_mensajero(self, id_interno, datos):
        """
        Método 5: GuardarMensajero [cite: 180]
        Sirve para Alta y Modificación. Rellena datos obligatorios con valores por defecto.
        """
        # 1. Obtener sesión
        guid = self._get_guid()
        if not guid:
            return False, "No se pudo conectar con Direcline (Fallo en ValidarUsuario/GUID)."

        # 2. Preparación de datos
        # Direcline tiene campos obligatorios marcados como 'Si' en la documentación.
        # Si tu formulario de Streamlit no los pide, debemos enviar valores por defecto.
        
        codigo = str(id_interno) # Usamos el ID de Supabase como código
        nombre = datos.get('nombre_apellido', 'Sin Nombre')
        
        # Limpiamos posibles nulos
        movil = datos.get('movil') if datos.get('movil') else ""
        email = datos.get('email_personal') if datos.get('email_personal') else ""
        
        # Corrección del error que tenías: Definimos la variable antes de usarla
        vehiculo_val = 'Si' if datos.get('vehiculo_empresa') == 'Si' else ''
        
        # Fecha obligatoria 
        fecha_alta = datetime.now().strftime("%Y-%m-%d")

        # 3. Construcción del XML Interno (CDATA)
        # Basado en la estructura de ejemplo del PDF [cite: 194-217]
        inner_xml = f"""
        <RAIZ>
            <GUID>{guid}</GUID>
            <mensajero>
                <codigo>{codigo}</codigo>
                <nombre>{nombre}</nombre>
                <tipoDireccion>C/</tipoDireccion>
                <direccion>Direccion Pendiente</direccion>
                <numeroDireccion>.</numeroDireccion>
                <pisoDireccion>.</pisoDireccion>
                <poblacion>Barcelona</poblacion>
                <pais>ES</pais>
                <codigoPostal>08000</codigoPostal>
                <telefono>{movil}</telefono>
                <movil>{movil}</movil>
                <eMail>{email}</eMail>
                <fechaAlta>{fecha_alta}</fechaAlta>
                <vehiculo>{vehiculo_val}</vehiculo>
            </mensajero>
        </RAIZ>
        """
        
        # 4. Construcción del Envelope SOAP
        # El XML de datos va dentro de <Valor> como CDATA 
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <GuardarMensajero xmlns="http://www.direcline.com/">
              <Valor><![CDATA[{inner_xml}]]></Valor>
            </GuardarMensajero>
          </soap:Body>
        </soap:Envelope>"""

        try:
            response = requests.post(self.url, data=soap_envelope.encode('utf-8'), headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                # Verificación de éxito: Si devuelve <CODIGO> todo fue bien [cite: 230]
                if "<CODIGO>" in response.text or "&lt;CODIGO&gt;" in response.text:
                    return True, "Sincronizado correctamente."
                else:
                    # Si falla, intentamos devolver una pista del error (Suele venir en tags <ERROR>) [cite: 1919]
                    return False, f"Direcline rechazó los datos. Respuesta: {response.text[:200]}..."
            else:
                return False, f"Error HTTP {response.status_code} al guardar."
        except Exception as e:
            return False, f"Excepción de conexión: {str(e)}"