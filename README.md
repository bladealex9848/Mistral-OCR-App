# Mistral OCR App

La **Mistral OCR App** es una aplicación web basada en Streamlit que utiliza la [API OCR de Mistral](https://docs.mistral.ai/reference/) para extraer texto de documentos PDF e imágenes. Los usuarios pueden proporcionar una URL o cargar un archivo local. La aplicación detecta automáticamente el tipo de archivo, muestra el documento original (o imagen) en una vista previa junto con los resultados OCR extraídos y ofrece una opción de descarga sencilla, todo sin necesidad de recargar la página.

### 🚀 ¡Prueba la Mistral OCR App en vivo!

🔗 **Demo en vivo:** [Mistral OCR App](https://mistral-ocr-app.streamlit.app/)

¡Experimenta el poder de **Mistral OCR** en acción! Carga PDFs o imágenes y extrae texto sin problemas con esta **aplicación OCR interactiva basada en Streamlit**.

![Mistral OCR App Demo](demo.png)

## Características

- **Detección Automática del Tipo de Archivo:** La aplicación identifica automáticamente si el archivo cargado es un PDF o una imagen.
- **Múltiples Métodos de Entrada:** Elige entre la entrada de URL o la carga de archivos locales.
- **Vista Previa en Tiempo Real:** Muestra el archivo original (a través de un iframe para PDFs o usando `st.image` para imágenes).
- **Extracción OCR:** Obtén los resultados OCR presentados en un diseño limpio de dos columnas.
- **Resultados Descargables:** Descarga la salida OCR en formato JSON, TXT o Markdown.
- **Opciones de Procesamiento Avanzadas:** Ofrece diferentes métodos de procesamiento (API OCR Estándar, API Document Understanding, Auto) y optimización de imágenes.
- **Interfaz Interactiva:** Construida con Streamlit para una experiencia de usuario fluida e interactiva.

## Instalación

### Requisitos Previos

- Python 3.8 o superior (recomendado)
- [Streamlit](https://streamlit.io/)
- [Pillow](https://pypi.org/project/Pillow/)
- [Requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [opencv-python-headless](https://pypi.org/project/opencv-python-headless/)

### Pasos

1. **Clona el Repositorio de origen:**

   ```bash
   git clone [https://github.com/AIAnytime/Mistral-OCR-App.git](https://github.com/AIAnytime/Mistral-OCR-App.git)
   cd Mistral-OCR-App
   ```

2. **Crea y Activa un Entorno Virtual (Opcional pero Recomendado):**

   En macOS/Linux:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

   En Windows:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Instala las Dependencias Requeridas:**

   Asegúrate de tener un archivo `requirements.txt` con el siguiente contenido:

   ```plaintext
   streamlit>=1.32.0
   pillow>=10.0.0
   requests>=2.31.0
   python-dotenv>=1.0.1
   opencv-python-headless>=4.9.0.80
   ```

   Luego, instálalas:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configura tu Clave de API de Mistral:**

   La aplicación requiere una clave de API de Mistral. Puedes configurarla de una de las siguientes maneras (orden de prioridad):

   - **Secretos de Streamlit:** Crea un archivo `.streamlit/secrets.toml` en el directorio de tu proyecto (o en el directorio desde donde ejecutas la aplicación) y agrega:

     ```toml
     MISTRAL_API_KEY = "tu_clave_api_aqui"
     ```

   - **Variable de Entorno:** Exporta tu clave de API como una variable de entorno:

     - En macOS/Linux:
       ```bash
       export MISTRAL_API_KEY=tu_clave_api_aqui
       ```

     - En Windows (Símbolo del sistema):
       ```bash
       set MISTRAL_API_KEY=tu_clave_api_aqui
       ```

## Uso

Para ejecutar la aplicación, utiliza el siguiente comando:

```bash
streamlit run main.py
```

### Cómo Funciona

1. **Configuración de la Clave de API:**
   Asegúrate de que tu clave de API de Mistral esté configurada como se describe en la sección de Instalación.

2. **Selección de la Fuente:**
   Elige si deseas procesar un documento a través de una **URL** o cargando un **Archivo local**.

3. **Entrada del Documento:**
   - Si seleccionaste **URL**, introduce la URL del archivo PDF o de imagen.
   - Si seleccionaste **Archivo local**, carga tu archivo PDF o de imagen. La aplicación detectará automáticamente el tipo de archivo.

4. **Procesamiento:**
   Haz clic en el botón **Procesar documentos** para enviar el documento a la API OCR de Mistral. La aplicación entonces:
   - Muestra una vista previa del documento en la columna izquierda.
   - Muestra los resultados OCR extraídos en la columna derecha.
   - Proporciona enlaces de descarga para la salida OCR en formatos JSON, TXT y Markdown.

5. **Descarga:**
   Haz clic en el botón de descarga deseado para guardar el resultado OCR en tu computadora.

## Descripción del Código

- **main.py:**
  El archivo principal de la aplicación Streamlit que contiene la lógica para:
  - Elementos de la interfaz de usuario para la entrada de la clave de API, la selección de la fuente (URL o carga de archivos).
  - Detección automática del tipo de archivo cargado (PDF o imagen).
  - Preparación del documento (lectura de bytes del archivo, codificación a base64 si es necesario).
  - Llamada a la API OCR de Mistral utilizando `requests` y `subprocess` (con cURL para mayor robustez).
  - Manejo de diferentes métodos de procesamiento de la API (OCR Estándar, Document Understanding).
  - Mostrar la vista previa del documento utilizando los elementos apropiados de Streamlit (`st.iframe` para PDFs, `st.image` para imágenes).
  - Presentar los resultados OCR extraídos en un `st.text_area`.
  - Generar enlaces de descarga para la salida OCR en varios formatos (JSON, TXT, MD).
  - Proporcionar opciones avanzadas como la optimización de imágenes y la visualización de detalles técnicos.

- **README.md:**
  Este archivo, que proporciona instrucciones detalladas y documentación para el proyecto.

- **requirements.txt:**
  Una lista de los paquetes de Python requeridos con versiones específicas para garantizar la consistencia.

## Contribuciones

¡Las contribuciones son bienvenidas! Si tienes sugerencias o encuentras problemas, no dudes en:

- Abrir un problema en el repositorio.
- Enviar una solicitud de extracción con mejoras o correcciones de errores.

## Licencia

Este proyecto está licenciado bajo la [Licencia MIT](LICENSE).

## Agradecimientos

- [Streamlit](https://streamlit.io/) por facilitar el desarrollo de aplicaciones web interactivas.
- [Mistral AI](https://mistral.ai) por su potente API OCR.
- Los desarrolladores de las bibliotecas de Python utilizadas en este proyecto.

## Contacto

Para cualquier pregunta o soporte, abre un problema en este repositorio o contacta a [sonu@aianytime.net].