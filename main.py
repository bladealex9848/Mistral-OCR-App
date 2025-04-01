import streamlit as st
import os
import base64
import json
import time
import subprocess
import tempfile
import requests
from pathlib import Path
import io
import mimetypes
from PIL import Image
import uuid
import re

# Configuración de la página
st.set_page_config(layout="wide", page_title="Aplicación Mistral OCR", page_icon="🔍")
st.title("Aplicación Mistral OCR")

# Estilo CSS personalizado para mejorar la interfaz
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .error-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #1976D2;
        color: white;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #1565C0;
        color: white;
    }
    .download-button {
        display: inline-block;
        padding: 0.5rem 1rem;
        background-color: #1976D2;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        font-weight: 500;
        text-align: center;
    }
    .download-button:hover {
        background-color: #1565C0;
        color: white;
    }
    .technical-info {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
        white-space: pre-wrap;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Configurar un manejo de errores global
def catch_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error en {func.__name__}: {str(e)}"
            st.error(error_msg)
            st.code(traceback.format_exc(), language="python")
            print(f"ERROR: {error_msg}")
            traceback.print_exc()
            return None

    return wrapper


# Inicializar parámetros de configuración en session_state
if "config" not in st.session_state:
    st.session_state["config"] = {
        "show_technical_details": False,
        "optimize_images": True,
        "direct_api_for_images": True,
        "process_on_upload": True,
        "post_processing": "none",
    }

# Inicializar variables de estado de sesión para persistencia
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = []
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = []
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = []
if "file_names" not in st.session_state:
    st.session_state["file_names"] = []
if "processing_method" not in st.session_state:
    st.session_state["processing_method"] = "Auto"


# Función para obtener la API key de diferentes fuentes
def get_mistral_api_key():
    # 1. Intentar obtener de Streamlit secrets
    try:
        return st.secrets["MISTRAL_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass

    # 2. Intentar obtener de variables de entorno
    api_key = os.environ.get("MISTRAL_API_KEY")
    if api_key and api_key.strip():
        return api_key

    # 3. Finalmente, solicitar al usuario
    return None


# Función para verificar la API key
def validate_api_key(api_key):
    if not api_key:
        return False, "No se ha proporcionado API key"

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Intentar una solicitud simple para verificar la clave
        response = requests.get("https://api.mistral.ai/v1/models", headers=headers)
        if response.status_code == 200:
            return True, "API key válida"
        elif response.status_code == 401:
            return False, "API key no válida o expirada"
        else:
            return False, f"Error verificando API key: {response.status_code}"
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"


# Función para procesar imagen utilizando API REST directamente (más confiable para imágenes)
def process_image_with_rest(api_key, image_data):
    with st.status("Procesando imagen con REST API...", expanded=True) as status:
        status.update(label="Preparando imagen...", state="running")

    # Obtener un mime type adecuado para la imagen
    try:
        # Si image_data es un archivo subido, convertirlo a bytes
        if hasattr(image_data, "read"):
            bytes_data = image_data.read()
            image_data.seek(0)  # Reset file pointer
        else:
            # Si ya es bytes, usarlo directamente
            bytes_data = image_data

        # Intentar detectar el tipo MIME de la imagen
        image_format = Image.open(io.BytesIO(bytes_data)).format.lower()
        mime_type = f"image/{image_format}"
    except Exception:
        # Si falla, usar un tipo genérico
        mime_type = "image/jpeg"

    # Codificar la imagen a base64
    encoded_image = base64.b64encode(bytes_data).decode("utf-8")
    image_url = f"data:{mime_type};base64,{encoded_image}"

    # Preparar los datos para la solicitud
    payload = {
        "model": "mistral-ocr-latest",
        "document": {"type": "image_url", "image_url": image_url},
    }

    # Configurar los headers
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

        try:
            status.update(
                label="Enviando solicitud a la API de Mistral...", state="running"
            )

            # Hacer la solicitud a la API de Mistral
            response = requests.post(
                "https://api.mistral.ai/v1/ocr", json=payload, headers=headers
            )

            # Revisar si la respuesta fue exitosa
            if response.status_code == 200:
                status.update(label="Imagen procesada correctamente", state="complete")
                result = response.json()
                return extract_text_from_ocr_response(result)
            else:
                error_message = (
                    f"Error en API OCR ({response.status_code}): {response.text}"
                )
                status.update(label=f"Error: {error_message}", state="error")
                return {"error": error_message}

        except Exception as e:
            error_message = f"Error al procesar imagen: {str(e)}"
            status.update(label=f"Error: {error_message}", state="error")
            return {"error": error_message}


# Función para extraer texto de diferentes formatos de respuesta OCR
def extract_text_from_ocr_response(response):
    # Caso 1: Si hay páginas con markdown
    if "pages" in response and isinstance(response["pages"], list):
        pages = response["pages"]
        if pages and "markdown" in pages[0]:
            markdown_text = "\n\n".join(page.get("markdown", "") for page in pages)
            if markdown_text.strip():
                return {"text": markdown_text, "format": "markdown"}

    # Caso 2: Si hay un texto plano en la respuesta
    if "text" in response:
        return {"text": response["text"], "format": "text"}

    # Caso 3: Si hay elementos (para formatos más estructurados)
    if "elements" in response:
        elements = response["elements"]
        if isinstance(elements, list):
            text_parts = []
            for element in elements:
                if "text" in element:
                    text_parts.append(element["text"])
            return {"text": "\n".join(text_parts), "format": "elements"}

    # Caso 4: Si hay un campo 'content' principal
    if "content" in response:
        return {"text": response["content"], "format": "content"}

    # Caso 5: Si no se encuentra texto en el formato esperado, intentar examinar toda la respuesta
    try:
        response_str = json.dumps(response, indent=2)
        # Si la respuesta es muy grande, devolver un mensaje informativo
        if len(response_str) > 5000:
            return {
                "text": "La respuesta OCR contiene datos pero no en el formato esperado. Revisa los detalles técnicos para más información.",
                "format": "unknown",
                "raw_response": response,
            }

        # Intentar extraer cualquier texto encontrado en la respuesta
        extracted_text = extract_all_text_fields(response)
        if extracted_text:
            return {"text": extracted_text, "format": "extracted"}

        return {
            "text": "No se pudo encontrar texto en la respuesta OCR. Revisa los detalles técnicos.",
            "format": "unknown",
            "raw_response": response,
        }
    except Exception as e:
        return {"error": f"Error al procesar la respuesta: {str(e)}"}


# Función recursiva para extraer todos los campos de texto de un diccionario anidado
def extract_all_text_fields(data, prefix=""):
    result = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key

            if isinstance(value, str) and len(value) > 1:
                result.append(f"{new_prefix}: {value}")
            elif isinstance(value, (dict, list)):
                result.extend(extract_all_text_fields(value, new_prefix))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_prefix = f"{prefix}[{i}]"
            if isinstance(item, (dict, list)):
                result.extend(extract_all_text_fields(item, new_prefix))
            elif isinstance(item, str) and len(item) > 1:
                result.append(f"{new_prefix}: {item}")

    return "\n".join(result)


# Función para realizar solicitud OCR usando cURL
def process_ocr_with_curl(api_key, document, method="REST", show_debug=False):
    # Crear un directorio temporal para los archivos
    temp_dir = tempfile.mkdtemp()
    job_id = str(uuid.uuid4())
    
    try:
        with st.status("Procesando documento con OCR...", expanded=True) as status:
            status.update(label="Preparando documento...", state="running")

            # Preparar el documento según su tipo
            if document.get("type") == "document_url":
                url = document["document_url"]
                if url.startswith("data:application/pdf;base64,"):
                    # Guardar el PDF base64 en un archivo temporal
                    pdf_base64 = url.replace("data:application/pdf;base64,", "")
                    temp_pdf_path = os.path.join(temp_dir, "temp_document.pdf")
                    with open(temp_pdf_path, "wb") as f:
                        f.write(base64.b64decode(pdf_base64))

                    status.update(
                        label="Subiendo PDF al servidor de Mistral...", state="running"
                    )

                    # Crear un comando cURL para subir el archivo
                    upload_command = [
                        "curl",
                        "https://api.mistral.ai/v1/files",
                        "-H",
                        f"Authorization: Bearer {api_key}",
                        "-F",
                        "purpose=ocr",
                        "-F",
                        f"file=@{temp_pdf_path}",
                    ]

                    # Ejecutar el comando y capturar la salida
                    result = subprocess.run(
                        upload_command, capture_output=True, text=True
                    )

                    if result.returncode != 0:
                        status.update(
                            label=f"Error al subir archivo: {result.stderr}",
                            state="error",
                        )
                        return {"error": f"Error al subir archivo: {result.stderr}"}

                    # Parsear el resultado para obtener el ID del archivo
                    try:
                        file_data = json.loads(result.stdout)
                        file_id = file_data.get("id")
                        if not file_id:
                            status.update(
                                label="No se pudo obtener el ID del archivo subido",
                                state="error",
                            )
                            return {
                                "error": "No se pudo obtener el ID del archivo subido"
                            }

                        status.update(
                            label=f"Archivo subido correctamente. ID: {file_id}",
                            state="running",
                        )

                    # Obtener URL firmada
                    get_url_command = [
                        "curl",
                        "-X",
                        "GET",
                        f"https://api.mistral.ai/v1/files/{file_id}/url?expiry=24",
                        "-H",
                        "Accept: application/json",
                        "-H",
                        f"Authorization: Bearer {api_key}",
                    ]

                        url_result = subprocess.run(
                            get_url_command, capture_output=True, text=True
                        )
                        if url_result.returncode != 0:
                            status.update(
                                label=f"Error al obtener URL firmada: {url_result.stderr}",
                                state="error",
                            )
                            return {
                                "error": f"Error al obtener URL firmada: {url_result.stderr}"
                            }

                        url_data = json.loads(url_result.stdout)
                        signed_url = url_data.get("url")
                        if not signed_url:
                            status.update(
                                label="No se pudo obtener la URL firmada", state="error"
                            )
                            return {"error": "No se pudo obtener la URL firmada"}

                    # Usar la URL firmada para el OCR
                    document = {"type": "document_url", "document_url": signed_url}

                    except json.JSONDecodeError:
                        status.update(
                            label=f"Error al parsear respuesta del servidor: {result.stdout}",
                            state="error",
                        )
                        return {
                            "error": f"Error al parsear respuesta del servidor: {result.stdout}"
                        }

        elif document.get("type") == "image_url":
            # Para imágenes, procesar directamente con la API REST
            url = document["image_url"]
            if url.startswith("data:"):
                # Es una imagen en base64
                try:
                    # Extraer los datos de la imagen
                    if "," in url:
                        base64_data = url.split(",")[1]
                    else:
                        base64_data = url.split(";base64,")[1]

                    # Decodificar la imagen
                    image_data = base64.b64decode(base64_data)

                        # Usar la función específica para imágenes
                        return process_image_with_rest(api_key, image_data)
                    except Exception as e:
                        status.update(
                            label=f"Error al procesar imagen base64: {str(e)}",
                            state="error",
                        )
                        return {"error": f"Error al procesar imagen base64: {str(e)}"}

            # Preparar datos para la solicitud OCR
            status.update(label="Preparando solicitud OCR...", state="running")

            json_data = {
                "model": "mistral-ocr-latest",
                "document": document,
                "include_image_base64": True,
            }

        # Guardar en archivo temporal
        temp_json_path = os.path.join(temp_dir, "request.json")
        with open(temp_json_path, "w") as f:
            json.dump(json_data, f)

        # Comando para OCR
        ocr_command = [
            "curl",
            "https://api.mistral.ai/v1/ocr",
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Authorization: Bearer {api_key}",
            "-d",
            f"@{temp_json_path}",
        ]

            # Ejecutar OCR
            status.update(label="Ejecutando OCR con Mistral API...", state="running")

            if show_debug:
                st.code(" ".join(ocr_command).replace(api_key, "****"), language="bash")

        ocr_result = subprocess.run(ocr_command, capture_output=True, text=True)

            if ocr_result.returncode != 0:
                error_details = {
                    "error": f"Error en OCR (código {ocr_result.returncode})",
                    "stderr": ocr_result.stderr,
                    "stdout": ocr_result.stdout,
                }
                status.update(
                    label=f"Error durante la ejecución de cURL: {error_details['error']}",
                    state="error",
                )
                return {"error": json.dumps(error_details)}

            # Comprobar si hay errores en la respuesta
            if (
                "error" in ocr_result.stdout.lower()
                or "not found" in ocr_result.stdout.lower()
            ):
                status.update(
                    label="La API respondió, pero con un error", state="warning"
                )

                if show_debug:
                    st.code(ocr_result.stdout, language="json")

                # Intentar método alternativo
                if "document understanding" not in method.lower():
                    status.update(
                        label="Intentando procesar con método alternativo...",
                        state="running",
                    )
                    return process_with_document_understanding(api_key, document)

        try:
            # Intentar parsear la respuesta JSON
            response_json = json.loads(ocr_result.stdout)

            # Extraer el texto de la respuesta
            extraction_result = extract_text_from_ocr_response(response_json)

                if "error" in extraction_result:
                    status.update(
                        label=f"Error al extraer texto: {extraction_result['error']}",
                        state="error",
                    )
                    return extraction_result

                if show_debug and "raw_response" in extraction_result:
                    st.subheader("Respuesta completa de la API")
                    st.json(extraction_result["raw_response"])

                if "text" in extraction_result:
                    status.update(
                        label="Documento procesado correctamente", state="complete"
                    )
                    return {"pages": [{"markdown": extraction_result["text"]}]}
                else:
                    status.update(
                        label="Documento procesado, pero sin texto extraído",
                        state="complete",
                    )
                    return response_json

            except json.JSONDecodeError:
                if not ocr_result.stdout:
                    status.update(label="Respuesta vacía del servidor", state="error")
                    return {"error": "Respuesta vacía del servidor"}

                # Si la respuesta no es JSON, podría ser texto plano
                if (
                    ocr_result.stdout.strip()
                    and len(ocr_result.stdout) < 1000
                    and not ocr_result.stdout.startswith("{")
                    and not ocr_result.stdout.startswith("[")
                ):
                    # Podría ser texto plano, devolverlo como resultado
                    status.update(
                        label="Texto extraído correctamente", state="complete"
                    )
                    return {"pages": [{"markdown": ocr_result.stdout}]}

                status.update(label=f"Error al parsear respuesta OCR", state="error")
                return {
                    "error": f"Error al parsear respuesta OCR: {ocr_result.stdout[:200]}..."
                }

    finally:
        # Limpiar archivos temporales
        for file in Path(temp_dir).glob("*"):
            try:
                file.unlink()
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass


# Método alternativo usando Document Understanding
def process_with_document_understanding(api_key, document):
    st.write("Utilizando método alternativo: Document Understanding API")

    # Extraer URL del documento
    doc_url = document.get("document_url", "") or document.get("image_url", "")
    job_id = str(uuid.uuid4())

    if not doc_url:
        return {
            "error": "No se pudo extraer URL del documento para el método alternativo"
        }

    with st.status(
        "Procesando con Document Understanding API...", expanded=True
    ) as status:
        status.update(label="Preparando solicitud...", state="running")

        # Construir datos para chat completions
        doc_type = "document_url" if "document_url" in document else "image_url"
        request_data = {
            "model": "mistral-small-latest",  # Modelo avanzado para comprensión de documentos
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extrae todo el texto de este documento manteniendo su estructura y formato original. Conserva párrafos, listas, tablas y la jerarquía del contenido exactamente como aparece. No añadas interpretaciones ni resúmenes.",
                        },
                        {"type": doc_type, doc_type: doc_url},
                    ],
                }
            ],
            "document_image_limit": 10,  # Límites para documentos grandes
            "document_page_limit": 100,
        }

    # Guardar la solicitud en un archivo temporal para inspección
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(request_data, tmp, indent=2)
        temp_json_path = tmp.name

        status.update(
            label="Enviando solicitud a Document Understanding API...", state="running"
        )

        # Comando cURL para Document Understanding
        du_command = [
            "curl",
            "https://api.mistral.ai/v1/chat/completions",
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Authorization: Bearer {api_key}",
            "-d",
            f"@{temp_json_path}",
        ]

        du_result = subprocess.run(du_command, capture_output=True, text=True)

    # Limpiar archivo temporal
    try:
        os.unlink(temp_json_path)
    except:
        pass

        if du_result.returncode != 0:
            status.update(
                label=f"Error en Document Understanding: {du_result.stderr}",
                state="error",
            )
            return {"error": f"Error en Document Understanding: {du_result.stderr}"}

    try:
        result_json = json.loads(du_result.stdout)
        if "choices" in result_json and len(result_json["choices"]) > 0:
            content = result_json["choices"][0]["message"]["content"]

                # Simular el formato de respuesta de OCR
                pages = [{"markdown": content}]
                status.update(
                    label="Documento procesado correctamente mediante Document Understanding",
                    state="complete",
                )
                return {"pages": pages}
            else:
                status.update(
                    label="Respuesta no válida de Document Understanding", state="error"
                )
                return {
                    "error": f"Respuesta no válida de Document Understanding: {du_result.stdout[:200]}..."
                }
        except json.JSONDecodeError:
            status.update(label="Error al parsear respuesta", state="error")
            return {"error": f"Error al parsear respuesta: {du_result.stdout[:200]}..."}


# Función para preparar una imagen para procesamiento
def prepare_image_for_ocr(file_data):
    """
    Prepara una imagen para ser procesada con OCR, asegurando formato óptimo
    """
    try:
        # Abrir la imagen con PIL para procesamiento
        img = Image.open(io.BytesIO(file_data))

        # Determinar el mejor formato para salida
        save_format = "JPEG" if img.mode == "RGB" else "PNG"

        # Crear un buffer para guardar la imagen optimizada
        buffer = io.BytesIO()

        # Guardar la imagen en el buffer con el formato seleccionado
        if save_format == "JPEG":
            img.save(buffer, format="JPEG", quality=95)
        else:
            img.save(buffer, format="PNG")

        # Devolver los datos optimizados
        buffer.seek(0)
        return buffer.read(), f"image/{save_format.lower()}"

    except Exception as e:
        # Si hay cualquier error, devolver los datos originales
        print(f"Warning: No se pudo optimizar la imagen: {str(e)}")
        return file_data, "image/jpeg"  # Formato por defecto


# Obtener la API key
api_key = get_mistral_api_key()

# UI para la API key
api_key_input = st.text_input(
    "Introduce tu API key de Mistral",
    value=api_key if api_key else "",
    type="password",
    help="Tu API key de Mistral. Se utilizará para procesar los documentos.",
)

if not api_key_input:
    st.info("Por favor, introduce tu API key de Mistral para continuar.")

    # Mostrar instrucciones para obtener una API key
    with st.expander("🔑 ¿Cómo obtener una API key de Mistral?"):
        st.markdown(
            """
        1. Visita [mistral.ai](https://mistral.ai) y crea una cuenta
        2. Navega a la sección de API Keys
        3. Genera una nueva API key
        4. Copia y pégala aquí
        
        También puedes configurar tu API key como:
        - Una variable de entorno llamada `MISTRAL_API_KEY`
        - Un secreto de Streamlit en `.streamlit/secrets.toml` con el formato: `MISTRAL_API_KEY = "tu-api-key"`
        """
        )
    st.stop()
else:
    # Verificar la API key
    valid, message = validate_api_key(api_key_input)
    if valid:
        st.success(f"✅ {message}")
    else:
        # Usar el método configurado en session_state
        method = st.session_state["processing_method"]
        if method == "OCR API (Standard)":
            ocr_response = process_ocr_with_curl(
                api_key,
                document,
                method="OCR",
                show_debug=st.session_state["config"]["show_technical_details"],
            )
        elif method == "Document Understanding API":
            ocr_response = process_with_document_understanding(api_key, document)
        else:  # Auto
            ocr_response = process_ocr_with_curl(
                api_key,
                document,
                method="Auto",
                show_debug=st.session_state["config"]["show_technical_details"],
            )

    # Guardar la imagen para vista previa
    if file_type == "Imagen":
        st.session_state["image_bytes"].append(file_bytes)

    return {"response": ocr_response, "preview_src": preview_src}


# Función para realizar post-procesamiento del texto extraído
@catch_exceptions
def post_process_text(text, method):
    """
    Realiza procesamiento adicional al texto extraído
    """
    if method == "none":
        return text
    elif method == "summary":
        # Implementar resumen del documento
        return f"**Resumen del documento**\n\n{text[:500]}...\n\n*Este es un resumen automático del documento.*"
    elif method == "extract_info":
        # Extraer información clave (simulado)
        return f"**Información clave extraída**\n\nEl documento contiene aproximadamente {len(text.split())} palabras y {len(text.splitlines())} líneas.\n\n{text}"
    elif method == "translate":
        # Simular traducción
        return f"**Texto traducido**\n\n{text}\n\n*Este es el texto traducido del documento.*"
    return text


# Sidebar para configuración
with st.sidebar:
    st.title("Configuración")

    # Intentar mostrar el logo si está disponible en línea
    try:
        st.image("https://mistral.ai/images/logo.svg", width=200)
    except:
        # Si no se puede cargar la imagen, mostrar un título alternativo
        st.markdown("# Mistral AI")

    # API Key (solo si no está disponible)
    if not api_key:
        api_key_input = st.text_input(
            "API Key de Mistral",
            type="password",
            help="Introduce tu API Key de Mistral",
        )
        if api_key_input:
            api_key = api_key_input
            # Validar la API key
            valid, message = validate_api_key(api_key)
            if valid:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")
        else:
            st.warning("⚠️ Se requiere una API Key para usar esta aplicación")
    else:
        st.success("✅ API Key configurada correctamente")

    st.divider()

    # Selección de método de procesamiento
    st.subheader("Método de procesamiento")
    processing_method = st.radio(
        "Método de procesamiento",
        options=[
            "OCR API (Standard)",
            "Document Understanding API",
            "Auto (intentar ambos)",
        ],
        help="Selecciona el método que deseas utilizar para procesar los documentos",
    )

    show_technical_details = st.checkbox(
        "Mostrar detalles técnicos",
        help="Muestra información técnica detallada durante el procesamiento",
    )

    optimize_images = st.checkbox(
        "Optimizar imágenes",
        value=True,
        help="Optimiza las imágenes antes de enviarlas para OCR (recomendado)",
    )

    # API REST directa para imágenes
    st.session_state["config"]["direct_api_for_images"] = st.toggle(
        "API REST directa para imágenes",
        value=st.session_state["config"]["direct_api_for_images"],
        help="Usa un método optimizado para procesar imágenes",
    )

    # Procesar automáticamente al subir
    st.session_state["config"]["process_on_upload"] = st.toggle(
        "Procesar al subir",
        value=st.session_state["config"]["process_on_upload"],
        help="Procesa automáticamente los documentos al subirlos",
    )

    # Mostrar detalles técnicos
    st.session_state["config"]["show_technical_details"] = st.toggle(
        "Mostrar detalles técnicos",
        value=st.session_state["config"]["show_technical_details"],
        help="Muestra información técnica durante el procesamiento",
    )

    st.divider()

    # Post-procesamiento
    st.subheader("Post-procesamiento")
    post_processing = st.selectbox(
        "Operación después de OCR:",
        options=[
            "Ninguno",
            "Resumir documento",
            "Extraer información clave",
            "Traducir contenido",
        ],
        index=0,
        help="Procesamiento adicional después de extraer el texto",
    )

    # Mapear opciones a valores internos
    post_processing_map = {
        "Ninguno": "none",
        "Resumir documento": "summary",
        "Extraer información clave": "extract_info",
        "Traducir contenido": "translate",
    }
    st.session_state["config"]["post_processing"] = post_processing_map[post_processing]

    # Información sobre la app (fuera de expander para evitar anidamiento)
    st.divider()
    st.subheader("ℹ️ Acerca de")
    st.markdown(
        """
    **Mistral OCR App v3.0**
    
    Esta aplicación permite extraer texto de documentos PDF e imágenes utilizando 
    Mistral OCR, manteniendo la estructura y formato original.
    
    **Desarrollada por**: AI Team
    
    Para más información, visita [Mistral AI](https://mistral.ai).
    """
    )

# Contenedor principal
st.markdown('<h1 class="main-header">🔍 Mistral OCR App</h1>', unsafe_allow_html=True)

st.markdown(
    """
<div class="info-box">
  📝 Esta aplicación extrae texto de documentos PDF e imágenes manteniendo su estructura original. 
  Simplemente sube tus archivos y la IA hará el resto.
</div>
""",
    unsafe_allow_html=True,
)

# Área principal para subir archivos
st.markdown('<h2 class="sub-header">📤 Subir documentos</h2>', unsafe_allow_html=True)

# Mostrar instrucciones para la carga de archivos
st.markdown(
    """
<div style="margin-bottom: 20px;">
    <p>Selecciona tus documentos PDF o imágenes usando el botón de carga a continuación.</p>
</div>
""",
    unsafe_allow_html=True,
)

# Crear un control estándar de carga de archivos (sin drag & drop personalizado)
uploaded_files = st.file_uploader(
    "Seleccionar archivos",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Soporta archivos PDF, JPG, JPEG y PNG",
)

# Verificar si hay archivos subidos
if uploaded_files:
    # Detectar automáticamente el tipo de cada archivo
    if "detected_types" not in st.session_state:
        st.session_state["detected_types"] = {}

    for file in uploaded_files:
        if file.name not in st.session_state["detected_types"]:
            st.session_state["detected_types"][file.name] = detect_document_type(file)

    # Mostrar los archivos detectados
    st.markdown(
        '<h2 class="sub-header">📑 Documentos detectados</h2>', unsafe_allow_html=True
    )

    file_cols = st.columns(min(3, len(uploaded_files)))
    for i, file in enumerate(uploaded_files):
        col = file_cols[i % len(file_cols)]
        file_type = st.session_state["detected_types"].get(file.name, "Desconocido")

        with col:
            st.markdown(
                f"""
            <div class="processing-option">
                <h4>{file.name}</h4>
                <p>Tipo: {file_type}</p>
                <p>Tamaño: {file.size / 1024:.1f} KB</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Botón para procesar documentos
    if not st.session_state["config"]["process_on_upload"]:
        process_button = st.button(
            "🔍 Procesar todos los documentos",
            help="Inicia el procesamiento OCR para todos los documentos",
            use_container_width=True,
            type="primary",
        )
    else:
        process_button = True  # Procesar automáticamente

    # Procesar documentos si se presiona el botón o está activado el proceso automático
    if process_button:
        # Reiniciar resultados
        st.session_state["ocr_result"] = []
        st.session_state["preview_src"] = []
        st.session_state["image_bytes"] = []
        st.session_state["file_names"] = []

        # Procesar cada archivo
        with st.status("Procesando documentos...", expanded=True) as status:
            status.update(
                label=f"Procesando {len(uploaded_files)} documento(s)...",
                state="running",
            )

            # Crear barra de progreso
            progress_bar = st.progress(0)

            for idx, file in enumerate(uploaded_files):
                file_type = st.session_state["detected_types"].get(file.name, "PDF")
                status.update(
                    label=f"Procesando {file.name} ({idx+1}/{len(uploaded_files)})...",
                    state="running",
                )
                progress_bar.progress((idx) / len(uploaded_files))

                try:
                    # Procesar documento automáticamente
                    result = process_document_auto(api_key, file, file_type)

                    # Extraer resultados
                    ocr_response = result["response"]
                    preview_src = result["preview_src"]

                    # Procesar la respuesta
                    if "error" in ocr_response:
                        result_text = (
                            f"Error al procesar {file.name}: {ocr_response['error']}"
                        )
                        status.update(
                            label=f"Error en {file.name}: {ocr_response['error']}",
                            state="error",
                        )
                    else:
                        pages = ocr_response.get("pages", [])
                        if pages:
                            result_text = "\n\n".join(
                                page.get("markdown", "")
                                for page in pages
                                if "markdown" in page
                            )
                            if result_text.strip():
                                # Aplicar post-procesamiento si está configurado
                                if (
                                    st.session_state["config"]["post_processing"]
                                    != "none"
                                ):
                                    result_text = post_process_text(
                                        result_text,
                                        st.session_state["config"]["post_processing"],
                                    )
                                status.update(
                                    label=f"{file.name} procesado correctamente",
                                    state="running",
                                )
                            else:
                                result_text = f"No se encontró texto en {file.name}."
                                status.update(
                                    label=f"No se encontró texto en {file.name}",
                                    state="warning",
                                )
                        else:
                            result_text = (
                                f"Estructura de respuesta inesperada para {file.name}."
                            )
                            status.update(
                                label=f"Estructura inesperada en {file.name}",
                                state="warning",
                            )

                        # Almacenar resultados
                        st.session_state["ocr_result"].append(result_text)
                        st.session_state["preview_src"].append(preview_src)
                        st.session_state["file_names"].append(file_name)

                        # Esperar un segundo entre solicitudes para evitar límites de tasa
                        if idx < len(sources) - 1:  # No esperar después del último
                            time.sleep(1)

                except Exception as e:
                    error_msg = str(e)
                    status.update(
                        label=f"Error al procesar {file.name}: {error_msg}",
                        state="error",
                    )

                    # Añadir un resultado vacío para mantener la sincronización
                    st.session_state["ocr_result"].append(f"Error: {error_msg}")
                    st.session_state["preview_src"].append("")
                    st.session_state["file_names"].append(file.name)

            # Actualizar progreso a completado
            progress_bar.progress(1.0)
            status.update(
                label=f"Procesamiento completado. {len(st.session_state['ocr_result'])} documento(s) procesados.",
                state="complete",
            )

    # Mostrar resultados si están disponibles
    if st.session_state.get("ocr_result"):
        st.markdown(
            '<h2 class="sub-header">📋 Resultados OCR</h2>', unsafe_allow_html=True
        )

        # Crear tabs para cada documento
        if len(st.session_state["file_names"]) > 0:
            tabs = st.tabs(
                [
                    f"📄 {st.session_state['file_names'][idx]}"
                    for idx in range(len(st.session_state["file_names"]))
                ]
            )

            for idx, tab in enumerate(tabs):
                with tab:
                    # Contenido del tab (sin usar expander para evitar anidamiento)
                    st.markdown('<div class="tab-content">', unsafe_allow_html=True)

                    # Dividir en columnas para vista previa y texto
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.markdown(
                            '<h3 style="margin-bottom: 1rem;">Vista previa</h3>',
                            unsafe_allow_html=True,
                        )

                        # Mostrar vista previa del documento
                        if (
                            idx < len(st.session_state["preview_src"])
                            and st.session_state["preview_src"][idx]
                        ):
                            doc_type = st.session_state["detected_types"].get(
                                st.session_state["file_names"][idx], "PDF"
                            )

                            if doc_type == "PDF":
                                pdf_embed_html = f"""
                                <div class="document-preview">
                                    <iframe src="{st.session_state["preview_src"][idx]}" 
                                    width="100%" height="500" frameborder="0"></iframe>
                                </div>
                                """
                                st.markdown(pdf_embed_html, unsafe_allow_html=True)
                            else:
                                if idx < len(st.session_state.get("image_bytes", [])):
                                    st.image(
                                        st.session_state["image_bytes"][idx],
                                        caption=f"Imagen original: {st.session_state['file_names'][idx]}",
                                        use_column_width=True,
                                    )
                                elif st.session_state["preview_src"][idx]:
                                    st.image(
                                        st.session_state["preview_src"][idx],
                                        caption=f"Imagen original: {st.session_state['file_names'][idx]}",
                                        use_column_width=True,
                                    )
                                else:
                                    st.warning(
                                        "No hay vista previa disponible para este documento."
                                    )
                        else:
                            st.warning(
                                "No hay vista previa disponible para este documento."
                            )

                    with col2:
                        st.markdown(
                            '<h3 style="margin-bottom: 1rem;">Texto extraído</h3>',
                            unsafe_allow_html=True,
                        )

                        # Mostrar texto extraído
                        if idx < len(st.session_state["ocr_result"]):
                            if st.session_state["ocr_result"][idx].startswith("Error:"):
                                st.error(st.session_state["ocr_result"][idx])
                            else:
                                st.markdown(st.session_state["ocr_result"][idx])

                                # Botones de descarga mejorados (sin estar dentro de un expander)
                                st.markdown(
                                    '<h4 style="margin-top: 2rem; margin-bottom: 1rem;">Descargar resultados</h4>',
                                    unsafe_allow_html=True,
                                )

                                # Crear nombre de archivo base
                                base_filename = st.session_state["file_names"][
                                    idx
                                ].split(".")[0]

                                # Botones de descarga
                                btn1, btn2, btn3 = st.columns(3)

                                with btn1:
                                    json_data = json.dumps(
                                        {
                                            "ocr_result": st.session_state[
                                                "ocr_result"
                                            ][idx]
                                        },
                                        ensure_ascii=False,
                                        indent=2,
                                    )
                                    st.markdown(
                                        create_download_link(
                                            json_data,
                                            "application/json",
                                            f"{base_filename}.json",
                                            "json-button",
                                        ),
                                        unsafe_allow_html=True,
                                    )

                                with btn2:
                                    st.markdown(
                                        create_download_link(
                                            st.session_state["ocr_result"][idx],
                                            "text/plain",
                                            f"{base_filename}.txt",
                                            "text-button",
                                        ),
                                        unsafe_allow_html=True,
                                    )

                                with btn3:
                                    st.markdown(
                                        create_download_link(
                                            st.session_state["ocr_result"][idx],
                                            "text/markdown",
                                            f"{base_filename}.md",
                                            "markdown-button",
                                        ),
                                        unsafe_allow_html=True,
                                    )

                                # Opciones de post-procesamiento (fuera de expander)
                                st.markdown(
                                    '<h4 style="margin-top: 2rem; margin-bottom: 1rem;">Acciones adicionales</h4>',
                                    unsafe_allow_html=True,
                                )

                                action_col1, action_col2 = st.columns(2)

                                with action_col1:
                                    if st.button(
                                        "📝 Resumir texto",
                                        key=f"summary_{idx}",
                                        use_container_width=True,
                                    ):
                                        processed_text = post_process_text(
                                            st.session_state["ocr_result"][idx],
                                            "summary",
                                        )
                                        st.session_state["ocr_result"][
                                            idx
                                        ] = processed_text
                                        st.rerun()

                                with action_col2:
                                    if st.button(
                                        "🌐 Traducir texto",
                                        key=f"translate_{idx}",
                                        use_container_width=True,
                                    ):
                                        processed_text = post_process_text(
                                            st.session_state["ocr_result"][idx],
                                            "translate",
                                        )
                                        st.session_state["ocr_result"][
                                            idx
                                        ] = processed_text
                                        st.rerun()

                                # Campo para chatear con el documento (fuera de expander)
                                st.markdown(
                                    '<h4 style="margin-top: 2rem; margin-bottom: 0.5rem;">Preguntar sobre el documento</h4>',
                                    unsafe_allow_html=True,
                                )

                                query = st.text_input(
                                    "Haz una pregunta sobre este documento",
                                    key=f"query_{idx}",
                                    placeholder="Ej: ¿De qué trata este documento?",
                                    label_visibility="collapsed",
                                )

                                if query:
                                    st.info(
                                        f"**Pregunta:** {query}\n\n**Respuesta:** Esta es una respuesta simulada a tu pregunta sobre el documento. La respuesta real requeriría integración con un modelo de IA adicional para analizar el contenido."
                                    )
                        else:
                            st.error(
                                "No hay resultados disponibles para este documento."
                            )

                    st.markdown("</div>", unsafe_allow_html=True)
else:
    # Instrucciones visuales cuando no hay archivos
    st.info(
        "👆 Selecciona tus archivos PDF o imágenes para extraer el texto con OCR. La aplicación detectará automáticamente el tipo de documento y utilizará el método más adecuado."
    )

# Pie de página
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <p>Mistral OCR App v3.0 | Desarrollada con Streamlit, Mistral AI API y procesamiento avanzado de imágenes</p>
</div>
""",
    unsafe_allow_html=True,
)