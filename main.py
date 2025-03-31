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
import traceback
from PIL import Image
import uuid
import re

# Configuración de la página con tema personalizado
st.set_page_config(
    layout="wide",
    page_title="Mistral OCR App",
    page_icon="🔍",
    initial_sidebar_state="expanded",
)

# Colores personalizados para un diseño más profesional
PRIMARY_COLOR = "#1E88E5"  # Azul principal
SECONDARY_COLOR = "#4CAF50"  # Verde para éxito
ACCENT_COLOR = "#FFC107"  # Amarillo para advertencias
ERROR_COLOR = "#E53935"  # Rojo para errores
NEUTRAL_DARK = "#263238"  # Fondo oscuro
NEUTRAL_LIGHT = "#ECEFF1"  # Fondo claro
TEXT_LIGHT = "#FFFFFF"  # Texto claro
TEXT_DARK = "#212121"  # Texto oscuro

# Estilos CSS mejorados para una interfaz más moderna
st.markdown(
    f"""
<style>
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {PRIMARY_COLOR};
        font-weight: 600;
    }}
    .main-header {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-align: center;
    }}
    .sub-header {{
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid {PRIMARY_COLOR};
        padding-bottom: 0.5rem;
    }}
    .info-box {{
        background-color: {NEUTRAL_LIGHT};
        border-left: 4px solid {PRIMARY_COLOR};
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }}
    .success-box {{
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 4px solid {SECONDARY_COLOR};
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }}
    .error-box {{
        background-color: rgba(229, 57, 53, 0.1);
        border-left: 4px solid {ERROR_COLOR};
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }}
    .download-button {{
        display: inline-block;
        padding: 0.75rem 1.5rem;
        background-color: {PRIMARY_COLOR};
        color: {TEXT_LIGHT} !important;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 500;
        text-align: center;
        margin: 0.5rem 0;
        width: 100%;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    .download-button:hover {{
        background-color: #1565C0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }}
    .json-button {{
        background-color: #FF9800;
        color: {TEXT_DARK} !important;
    }}
    .json-button:hover {{
        background-color: #F57C00;
    }}
    .text-button {{
        background-color: {SECONDARY_COLOR};
    }}
    .text-button:hover {{
        background-color: #388E3C;
    }}
    .markdown-button {{
        background-color: #7E57C2;
    }}
    .markdown-button:hover {{
        background-color: #673AB7;
    }}
    .file-uploader {{
        border: 2px dashed {PRIMARY_COLOR};
        border-radius: 10px;
        padding: 2rem 1rem;
        text-align: center;
        background-color: rgba(30, 136, 229, 0.05);
    }}
    .result-container {{
        border: 1px solid #DADCE0;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .tab-content {{
        padding: 1rem;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        background-color: #F8F9FA;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {PRIMARY_COLOR};
        color: white;
    }}
    .document-preview {{
        border: 1px solid #DADCE0;
        border-radius: 8px;
        overflow: hidden;
    }}
    .technical-info {{
        font-family: monospace;
        background-color: #2b2b2b;
        color: #e6e6e6;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        white-space: pre-wrap;
        overflow-x: auto;
    }}
    .processing-option {{
        background-color: white;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    .processing-option:hover {{
        border-color: {PRIMARY_COLOR};
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    .processing-option.selected {{
        border-color: {PRIMARY_COLOR};
        border-width: 2px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    .sidebar-info {{
        background-color: rgba(30, 136, 229, 0.05);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }}
    
    /* Estilos para los indicadores de progreso animados */
    @keyframes pulse {{
        0% {{ opacity: 0.6; }}
        50% {{ opacity: 1; }}
        100% {{ opacity: 0.6; }}
    }}
    .processing-indicator {{
        display: flex;
        align-items: center;
        padding: 1rem;
        border-radius: 8px;
        background-color: rgba(30, 136, 229, 0.1);
        animation: pulse 1.5s infinite ease-in-out;
    }}
    .processing-indicator .icon {{
        margin-right: 0.5rem;
        color: {PRIMARY_COLOR};
    }}
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
            # Evitamos expanders o status anidados aquí
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
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
if "status_messages" not in st.session_state:
    st.session_state["status_messages"] = {}
if "current_tab" not in st.session_state:
    st.session_state["current_tab"] = "OCR"


# Función segura para actualizar mensajes de estado
def update_status(job_id, label, state="running"):
    st.session_state["status_messages"][job_id] = {
        "label": label,
        "state": state,
        "timestamp": time.time()
    }


# Función para limpiar mensajes de estado antiguos
def clean_old_status_messages(max_age=3600):  # 1 hora por defecto
    current_time = time.time()
    keys_to_remove = []
    
    for job_id, status_info in st.session_state["status_messages"].items():
        if current_time - status_info.get("timestamp", 0) > max_age:
            keys_to_remove.append(job_id)
    
    for job_id in keys_to_remove:
        del st.session_state["status_messages"][job_id]


# Función para mostrar mensajes de estado actuales
def display_status_messages():
    # Primero limpiamos mensajes antiguos
    clean_old_status_messages()
    
    # Luego mostramos los mensajes activos
    for job_id, status_info in st.session_state["status_messages"].items():
        label = status_info.get("label", "Procesando...")
        state = status_info.get("state", "running")
        
        if state == "running":
            st.info(f"⏳ {label}")
        elif state == "complete":
            st.success(f"✅ {label}")
        elif state == "error":
            st.error(f"❌ {label}")
        elif state == "warning":
            st.warning(f"⚠️ {label}")


# Función para obtener la API key de diferentes fuentes
@catch_exceptions
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


# Verificar la API key
api_key = get_mistral_api_key()


# Función para verificar la API key
@catch_exceptions
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


# Función para procesar imagen utilizando API REST directamente
@catch_exceptions
def process_image_with_rest(api_key, image_data):
    job_id = str(uuid.uuid4())
    update_status(job_id, "Procesando imagen con REST API...", "running")

    try:
        update_status(job_id, "Preparando imagen...", "running")

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
        except Exception as e:
            print(f"Error al detectar formato de imagen: {str(e)}")
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        update_status(job_id, "Enviando solicitud a la API de Mistral...", "running")

        # Hacer la solicitud a la API de Mistral
        response = requests.post(
            "https://api.mistral.ai/v1/ocr", json=payload, headers=headers
        )

        # Revisar si la respuesta fue exitosa
        if response.status_code == 200:
            update_status(job_id, "Imagen procesada correctamente", "complete")
            result = response.json()
            return extract_text_from_ocr_response(result)
        else:
            error_message = f"Error en API OCR ({response.status_code}): {response.text}"
            update_status(job_id, f"Error: {error_message}", "error")
            return {"error": error_message}

    except Exception as e:
        error_message = f"Error al procesar imagen: {str(e)}"
        update_status(job_id, f"Error: {error_message}", "error")
        return {"error": error_message}


# Función para extraer texto de diferentes formatos de respuesta OCR
@catch_exceptions
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
@catch_exceptions
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
@catch_exceptions
def process_ocr_with_curl(api_key, document, method="REST", show_debug=False):
    # Crear un directorio temporal para los archivos
    temp_dir = tempfile.mkdtemp()
    job_id = str(uuid.uuid4())
    
    try:
        # Registramos el inicio del procesamiento
        update_status(job_id, "Procesando documento con OCR...", "running")

        # Preparar el documento según su tipo
        if document.get("type") == "document_url":
            url = document["document_url"]
            if url.startswith("data:application/pdf;base64,"):
                # Guardar el PDF base64 en un archivo temporal
                pdf_base64 = url.replace("data:application/pdf;base64,", "")
                temp_pdf_path = os.path.join(temp_dir, "temp_document.pdf")
                with open(temp_pdf_path, "wb") as f:
                    f.write(base64.b64decode(pdf_base64))

                update_status(job_id, "Subiendo PDF al servidor de Mistral...", "running")

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
                    update_status(job_id, f"Error al subir archivo: {result.stderr}", "error")
                    return {"error": f"Error al subir archivo: {result.stderr}"}

                # Parsear el resultado para obtener el ID del archivo
                try:
                    file_data = json.loads(result.stdout)
                    file_id = file_data.get("id")
                    if not file_id:
                        update_status(job_id, "No se pudo obtener el ID del archivo subido", "error")
                        return {
                            "error": "No se pudo obtener el ID del archivo subido"
                        }

                    update_status(job_id, f"Archivo subido correctamente. ID: {file_id}", "running")

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
                        update_status(job_id, f"Error al obtener URL firmada: {url_result.stderr}", "error")
                        return {
                            "error": f"Error al obtener URL firmada: {url_result.stderr}"
                        }

                    url_data = json.loads(url_result.stdout)
                    signed_url = url_data.get("url")
                    if not signed_url:
                        update_status(job_id, "No se pudo obtener la URL firmada", "error")
                        return {"error": "No se pudo obtener la URL firmada"}

                    # Usar la URL firmada para el OCR
                    document = {"type": "document_url", "document_url": signed_url}

                except json.JSONDecodeError:
                    update_status(job_id, f"Error al parsear respuesta del servidor: {result.stdout}", "error")
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
                    update_status(job_id, f"Error al procesar imagen base64: {str(e)}", "error")
                    return {"error": f"Error al procesar imagen base64: {str(e)}"}

        # Preparar datos para la solicitud OCR
        update_status(job_id, "Preparando solicitud OCR...", "running")

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
        update_status(job_id, "Ejecutando OCR con Mistral API...", "running")

        if show_debug:
            # Mostramos el comando curl para debug (ocultando la API key)
            debug_command = " ".join(ocr_command).replace(api_key, "****")
            print(f"DEBUG: Comando OCR: {debug_command}")

        ocr_result = subprocess.run(ocr_command, capture_output=True, text=True)

        if ocr_result.returncode != 0:
            error_details = {
                "error": f"Error en OCR (código {ocr_result.returncode})",
                "stderr": ocr_result.stderr,
                "stdout": ocr_result.stdout,
            }
            update_status(job_id, f"Error durante la ejecución de cURL: {error_details['error']}", "error")
            return {"error": json.dumps(error_details)}

        # Comprobar si hay errores en la respuesta
        if (
            "error" in ocr_result.stdout.lower()
            or "not found" in ocr_result.stdout.lower()
        ):
            update_status(job_id, "La API respondió, pero con un error", "warning")

            if show_debug:
                print(f"DEBUG: Respuesta de error OCR: {ocr_result.stdout}")

            # Intentar método alternativo
            if "document understanding" not in method.lower():
                update_status(job_id, "Intentando procesar con método alternativo...", "running")
                return process_with_document_understanding(api_key, document)

        try:
            # Intentar parsear la respuesta JSON
            response_json = json.loads(ocr_result.stdout)

            # Extraer el texto de la respuesta
            extraction_result = extract_text_from_ocr_response(response_json)

            if "error" in extraction_result:
                update_status(job_id, f"Error al extraer texto: {extraction_result['error']}", "error")
                return extraction_result

            if show_debug and "raw_response" in extraction_result:
                print("DEBUG: Respuesta completa:")
                print(json.dumps(extraction_result["raw_response"], indent=2))

            if "text" in extraction_result:
                update_status(job_id, "Documento procesado correctamente", "complete")
                return {"pages": [{"markdown": extraction_result["text"]}]}
            else:
                update_status(job_id, "Documento procesado, pero sin texto extraído", "complete")
                return response_json

        except json.JSONDecodeError:
            if not ocr_result.stdout:
                update_status(job_id, "Respuesta vacía del servidor", "error")
                return {"error": "Respuesta vacía del servidor"}

            # Si la respuesta no es JSON, podría ser texto plano
            if (
                ocr_result.stdout.strip()
                and len(ocr_result.stdout) < 1000
                and not ocr_result.stdout.startswith("{")
                and not ocr_result.stdout.startswith("[")
            ):
                # Podría ser texto plano, devolverlo como resultado
                update_status(job_id, "Texto extraído correctamente", "complete")
                return {"pages": [{"markdown": ocr_result.stdout}]}

            update_status(job_id, f"Error al parsear respuesta OCR", "error")
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
@catch_exceptions
def process_with_document_understanding(api_key, document):
    # Extraer URL del documento
    doc_url = document.get("document_url", "") or document.get("image_url", "")
    job_id = str(uuid.uuid4())

    if not doc_url:
        return {
            "error": "No se pudo extraer URL del documento para el método alternativo"
        }

    update_status(job_id, "Procesando con Document Understanding API...", "running")

    try:
        update_status(job_id, "Preparando solicitud...", "running")

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
                        {"type": doc_type, doc_type: doc_url
                    }
                ]
            }
        ],
        "document_image_limit": 10,  # Límites para documentos grandes
        "document_page_limit": 100,        
    }
    except:
        pass

    # Guardar la solicitud en un archivo temporal para inspección
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(request_data, tmp, indent=2)
        temp_json_path = tmp.name

    update_status(job_id, "Enviando solicitud a Document Understanding API...", "running")

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
        update_status(job_id, f"Error en Document Understanding: {du_result.stderr}", "error")
        return {"error": f"Error en Document Understanding: {du_result.stderr}"}

    try:
        result_json = json.loads(du_result.stdout)
        if "choices" in result_json and len(result_json["choices"]) > 0:
            content = result_json["choices"][0]["message"]["content"]

            # Simular el formato de respuesta de OCR
            pages = [{"markdown": content}]
            update_status(
                job_id, "Documento procesado correctamente mediante Document Understanding", "complete"
            )
            return {"pages": pages}
        else:
            update_status(job_id, "Respuesta no válida de Document Understanding", "error")
            return {
                "error": f"Respuesta no válida de Document Understanding: {du_result.stdout[:200]}..."
            }
    except json.JSONDecodeError:
        update_status(job_id, "Error al parsear respuesta", "error")
        return {"error": f"Error al parsear respuesta: {du_result.stdout[:200]}..."}


# Función para preparar una imagen para procesamiento
@catch_exceptions
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


# Función para detección automática del tipo de documento
@catch_exceptions
def detect_document_type(file):
    """
    Detecta automáticamente si un archivo es un PDF o una imagen
    """
    if hasattr(file, "type"):
        mime_type = file.type
        if mime_type.startswith("application/pdf"):
            return "PDF"
        elif mime_type.startswith("image/"):
            return "Imagen"

    # Detectar por extensión del nombre del archivo
    if hasattr(file, "name"):
        name = file.name.lower()
        if name.endswith(".pdf"):
            return "PDF"
        elif name.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")):
            return "Imagen"

    # Si no se puede determinar, intentar abrir como imagen
    try:
        Image.open(file)
        file.seek(0)  # Restaurar el puntero del archivo
        return "Imagen"
    except:
        file.seek(0)  # Restaurar el puntero del archivo
        # Asumir PDF por defecto
        return "PDF"


# Función para crear enlaces de descarga más atractivos
def create_download_link(data, filetype, filename, button_class=""):
    """
    Crea un enlace de descarga con estilo mejorado
    """
    b64 = base64.b64encode(data.encode()).decode()
    href = f'<a href="data:{filetype};base64,{b64}" download="{filename}" class="download-button {button_class}">Descargar {filename}</a>'
    return href


# Función para procesar un documento automáticamente
@catch_exceptions
def process_document_auto(api_key, file, file_type):
    """
    Procesa un documento automáticamente eligiendo el método más adecuado
    """
    file_bytes = file.read()
    file.seek(0)  # Restaurar el puntero del archivo

    # Preparar el documento según su tipo
    if file_type == "PDF":
        encoded_pdf = base64.b64encode(file_bytes).decode("utf-8")
        document = {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{encoded_pdf}",
        }
        preview_src = f"data:application/pdf;base64,{encoded_pdf}"
    else:  # Imagen
        # Optimizar la imagen si está habilitado
        if st.session_state["config"]["optimize_images"]:
            file_bytes, mime_type = prepare_image_for_ocr(file_bytes)
        else:
            mime_type = file.type

        # Codificar en base64 para enviar a la API
        encoded_image = base64.b64encode(file_bytes).decode("utf-8")

        # Preparar el documento con la imagen
        document = {
            "type": "image_url",
            "image_url": f"data:{mime_type};base64,{encoded_image}",
        }
        preview_src = f"data:{mime_type};base64,{encoded_image}"

    # Usar el método más adecuado según configuración
    if file_type == "Imagen" and st.session_state["config"]["direct_api_for_images"]:
        ocr_response = process_image_with_rest(api_key, file_bytes)
        # Convertir la respuesta al formato esperado por el resto del código
        if "text" in ocr_response:
            ocr_response = {"pages": [{"markdown": ocr_response["text"]}]}
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
    if method == "none" or not text:
        return text
    elif method == "summary":
        # Implementar resumen del documento
        summary_text = "**Resumen del documento**\n\n"
        
        # Extraer párrafos significativos
        paragraphs = [p for p in text.split("\n\n") if len(p) > 20]
        
        # Calcular longitud promedio de párrafos para hacer un resumen proporcionado
        avg_length = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
        summary_length = min(500, int(avg_length * 0.3 * len(paragraphs)))
        
        # Crear un resumen basado en el inicio del documento
        if len(paragraphs) > 0:
            first_part = paragraphs[0][:min(len(paragraphs[0]), 200)]
            summary_text += f"{first_part}...\n\n"
        
        # Añadir información estadística
        word_count = len(text.split())
        line_count = len(text.splitlines())
        char_count = len(text)
        
        summary_text += f"*Este documento contiene aproximadamente {word_count} palabras, "
        summary_text += f"{line_count} líneas y {char_count} caracteres.*"
        
        return summary_text
        
    elif method == "extract_info":
        # Implementar extracción de información clave
        info_text = "**Información clave extraída**\n\n"
        
        # Detectar posibles fechas en el texto usando regex
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s+de\s+[a-zA-Záéíóúü]+\s+de\s+\d{2,4}\b'
        dates = re.findall(date_pattern, text)
        
        # Detectar posibles nombres propios (simplificado)
        name_pattern = r'\b[A-Z][a-záéíóúü]+\s+[A-Z][a-záéíóúü]+\b'
        names = re.findall(name_pattern, text)
        
        # Detectar posibles números de referencia/expediente
        ref_pattern = r'\b[A-Z0-9]{5,}\b|\b\d{2,}-\d{2,}\b'
        references = re.findall(ref_pattern, text)
        
        # Añadir la información encontrada
        if dates:
            info_text += "**Posibles fechas encontradas:**\n"
            info_text += ", ".join(dates[:5])  # Limitar a 5 para no sobrecargar
            info_text += "\n\n"
            
        if names:
            info_text += "**Posibles nombres encontrados:**\n"
            info_text += ", ".join(set(names[:5]))  # Eliminar duplicados y limitar a 5
            info_text += "\n\n"
            
        if references:
            info_text += "**Posibles referencias o expedientes:**\n"
            info_text += ", ".join(set(references[:5]))
            info_text += "\n\n"
        
        # Añadir estadísticas del documento
        word_count = len(text.split())
        info_text += f"**Estadísticas del documento:**\n"
        info_text += f"- {word_count} palabras\n"
        info_text += f"- {len(text.splitlines())} líneas\n"
        
        # Añadir los primeros párrafos como contexto
        info_text += "\n**Extracto del documento:**\n\n"
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if paragraphs:
            info_text += paragraphs[0][:300] + "...\n\n"
        
        return info_text + "\n\n" + text
        
    elif method == "translate":
        # En lugar de una traducción real (que requeriría una API adicional),
        # proporcionamos una plantilla para simular la traducción
        translate_text = "**Texto original:**\n\n"
        translate_text += text[:min(len(text), 300)]  # Primeros 300 caracteres
        translate_text += "...\n\n"
        translate_text += "**Nota sobre traducción:**\n\n"
        translate_text += "Para una traducción completa del texto, puedes utilizar servicios como Google Translate, "
        translate_text += "DeepL o contratar servicios profesionales de traducción."
        translate_text += "\n\n*Para traducir el texto completo, copia y pega el contenido en: "
        translate_text += "[Google Translate](https://translate.google.com/) o [DeepL](https://www.deepl.com/translator)*"
        
        # Devolver la plantilla + texto original
        return translate_text + "\n\n**Texto original completo:**\n\n" + text
        
    return text


# Función para preparar texto para interfaz de vigilancia judicial
@catch_exceptions
def prepare_vigilancia_judicial(text):
    """
    Prepara el texto para ser utilizado en la solicitud de vigilancia judicial
    """
    # Plantilla para la solicitud
    template = """
# Solicitud de Vigilancia Judicial Administrativa

## 1. Datos del Solicitante:

- **Nombre completo:** [NOMBRE_SOLICITANTE]
- **Identificación:** [TIPO_ID] [NUMERO_ID]
- **Calidad en que actúa:** [CALIDAD] (Apoderado, Parte, etc.)
- **Dirección:** [DIRECCION]
- **Correo electrónico:** [EMAIL]
- **Teléfono de contacto:** [TELEFONO]

## 2. Datos del Proceso:

- **Despacho Judicial:** [DESPACHO]
- **Radicado:** [RADICADO]
- **Tipo de proceso:** [TIPO_PROCESO]
- **Partes:** [PARTES]

## 3. Motivo de la Solicitud:

[MOTIVO_SOLICITUD]

## 4. Hechos:

[HECHOS]

## 5. Petición:

De conformidad con lo dispuesto en el artículo 101 de la Ley 270 de 1996, reglamentado mediante el Acuerdo No. PSAA11-8716 de 2011 del Consejo Superior de la Judicatura y la Circular PCSJC17-43 de 2017, solicito respetuosamente al Honorable Consejo Seccional de la Judicatura que tramite la presente solicitud de Vigilancia Judicial Administrativa.

## 6. Anexos:

[ANEXOS]

## 7. Notificaciones:

Recibiré notificaciones en la dirección y correo electrónico indicados en los datos del solicitante.

Atentamente,


[NOMBRE_SOLICITANTE]
[TIPO_ID] [NUMERO_ID]
    """
    
    # Si hay texto extraído, intentar extraer información relevante
    if text and len(text) > 0:
        # Intentar extraer nombres
        name_pattern = r'\b[A-Z][a-záéíóúü]+\s+[A-Z][a-záéíóúü]+\s+[A-Z][a-záéíóúü]+\b|\b[A-Z][a-záéíóúü]+\s+[A-Z][a-záéíóúü]+\b'
        names = re.findall(name_pattern, text)
        
        # Intentar extraer números de documentos
        id_pattern = r'\b\d{6,10}\b'
        ids = re.findall(id_pattern, text)
        
        # Intentar extraer radicados típicos
        radicado_pattern = r'\b\d{2,}-\d{2,}-\d{2,}-\d{3,}\b|\b\d{4,}-\d{2,}\b'
        radicados = re.findall(radicado_pattern, text)
        
        # Intentar extraer correos electrónicos
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Reemplazar en la plantilla si se encontró información
        if names:
            template = template.replace("[NOMBRE_SOLICITANTE]", names[0])
        if ids:
            template = template.replace("[NUMERO_ID]", ids[0])
            template = template.replace("[TIPO_ID]", "C.C.")
        if radicados:
            template = template.replace("[RADICADO]", radicados[0])
        if emails:
            template = template.replace("[EMAIL]", emails[0])
        
        # Extraer un posible motivo de la solicitud (primeros párrafos)
        paragraphs = [p for p in text.split("\n\n") if len(p) > 20]
        if paragraphs:
            motivo = paragraphs[0][:300]
            template = template.replace("[MOTIVO_SOLICITUD]", motivo)
            
            # Si hay más párrafos, usarlos como hechos
            if len(paragraphs) > 1:
                hechos = "\n\n".join(paragraphs[1:3])  # Tomar 2 párrafos para los hechos
                template = template.replace("[HECHOS]", hechos)
    
    # Reemplazar todos los campos restantes que no se pudieron extraer con marcadores
    template = template.replace("[NOMBRE_SOLICITANTE]", "[Ingrese nombre del solicitante]")
    template = template.replace("[TIPO_ID]", "[Tipo de identificación]")
    template = template.replace("[NUMERO_ID]", "[Número de identificación]")
    template = template.replace("[CALIDAD]", "[Calidad en que actúa]")
    template = template.replace("[DIRECCION]", "[Dirección para notificaciones]")
    template = template.replace("[EMAIL]", "[Correo electrónico]")
    template = template.replace("[TELEFONO]", "[Teléfono de contacto]")
    template = template.replace("[DESPACHO]", "[Nombre del despacho judicial]")
    template = template.replace("[RADICADO]", "[Número de radicado]")
    template = template.replace("[TIPO_PROCESO]", "[Tipo de proceso]")
    template = template.replace("[PARTES]", "[Nombres de las partes]")
    template = template.replace("[MOTIVO_SOLICITUD]", "[Explique brevemente por qué solicita la vigilancia judicial]")
    template = template.replace("[HECHOS]", "[Describa cronológicamente los hechos relevantes]")
    template = template.replace("[ANEXOS]", "[Liste los documentos anexos]")
    
    return template


# Función para realizar el control de legalidad de una solicitud
@catch_exceptions
def control_legalidad_solicitud(text):
    """
    Realiza un control de legalidad sobre una solicitud de vigilancia judicial
    """
    # Plantilla para el control de legalidad
    template = """
# Control de Legalidad - Solicitud de Vigilancia Judicial Administrativa

## Análisis de requisitos (Acuerdo No. PSAA11-8716)

| Criterio | Descripción | Aplicación al Caso | Observaciones |
|----------|-------------|-------------------|---------------|
| **Competencia territorial** | La solicitud debe dirigirse al Consejo Seccional con jurisdicción sobre el territorio donde se encuentra el despacho judicial. | [COMPETENCIA_CUMPLE] | [COMPETENCIA_OBS] |
| **Legitimación** | Debe ser presentada por quien acredite interés legítimo, sea parte, apoderado o interviniente en el proceso. | [LEGITIMACION_CUMPLE] | [LEGITIMACION_OBS] |
| **Identificación de las partes** | La solicitud debe identificar claramente las partes del proceso. | [PARTES_CUMPLE] | [PARTES_OBS] |
| **Identificación del proceso** | Debe contener información clara sobre el despacho judicial y número de radicado. | [PROCESO_CUMPLE] | [PROCESO_OBS] |
| **Descripción de la situación** | La solicitud debe describir de manera clara y precisa la situación que se considera irregular. | [DESCRIPCION_CUMPLE] | [DESCRIPCION_OBS] |
| **Relación con la administración de justicia** | Los hechos deben estar relacionados con la administración de justicia y no ser asuntos jurisdiccionales. | [ADMIN_JUSTICIA_CUMPLE] | [ADMIN_JUSTICIA_OBS] |
| **Anexos y pruebas** | Se deben aportar las pruebas que sustentan la solicitud. | [ANEXOS_CUMPLE] | [ANEXOS_OBS] |

## Resumen de la solicitud

[RESUMEN_SOLICITUD]

## Problema

[PROBLEMA]

## Recomendación

[RECOMENDACION]
    """
    
    # Valores por defecto
    cumple_text = "⚠️ No se puede determinar"
    no_cumple_text = "❌ No cumple"
    si_cumple_text = "✅ Cumple"
    
    # Analizamos el texto proporcionado para identificar elementos clave
    competencia_cumple = cumple_text
    competencia_obs = "No hay información suficiente para determinar la competencia territorial."
    
    legitimacion_cumple = cumple_text
    legitimacion_obs = "No se identifica claramente la calidad en que actúa el solicitante."
    
    partes_cumple = cumple_text
    partes_obs = "No hay identificación clara de todas las partes del proceso."
    
    proceso_cumple = cumple_text
    proceso_obs = "No se identifica claramente el despacho judicial o el número de radicado."
    
    descripcion_cumple = cumple_text
    descripcion_obs = "No hay una descripción clara de la situación considerada irregular."
    
    admin_justicia_cumple = cumple_text
    admin_justicia_obs = "No se puede determinar si los hechos son de naturaleza administrativa o jurisdiccional."
    
    anexos_cumple = no_cumple_text
    anexos_obs = "No se mencionan anexos o pruebas que sustenten la solicitud."
    
    # Resumen y problema por defecto
    resumen = "No hay información suficiente para realizar un resumen detallado de la solicitud."
    problema = "Con la información proporcionada no es posible identificar claramente el problema central de la solicitud."
    
    # Si hay texto, intentamos extraer información relevante
    if text and len(text) > 100:
        # Buscar información sobre radicado
        radicado_pattern = r'\b\d{2,}-\d{2,}-\d{2,}-\d{3,}\b|\b\d{4,}-\d{2,}\b'
        radicados = re.findall(radicado_pattern, text)
        
        if radicados:
            proceso_cumple = si_cumple_text
            proceso_obs = f"Se identifica el radicado: {radicados[0]}"
        
        # Buscar menciones a despachos judiciales
        despacho_pattern = r'[Jj]uzgado\s+\w+|[Cc]onsejo\s+\w+|[Tt]ribunal\s+\w+'
        despachos = re.findall(despacho_pattern, text)
        
        if despachos:
            if proceso_cumple != si_cumple_text:
                proceso_cumple = si_cumple_text
                proceso_obs = f"Se identifica el despacho: {despachos[0]}"
            else:
                proceso_obs += f" y el despacho: {despachos[0]}"
        
        # Buscar información sobre anexos
        anexos_pattern = r'[Aa]nexo[s]?|[Aa]djunto[s]?|[Pp]rueba[s]?'
        anexos_match = re.search(anexos_pattern, text)
        
        if anexos_match:
            anexos_cumple = si_cumple_text
            anexos_obs = "Se mencionan anexos o pruebas en la solicitud."
        
        # Extraer un posible problema/resumen (primeros párrafos)
        paragraphs = [p for p in text.split("\n\n") if len(p) > 20]
        if paragraphs:
            resumen = paragraphs[0]
            
            if len(paragraphs) > 1:
                problema = "\n\n".join(paragraphs[1:2])
                
            # Verificar si hay una descripción clara
            if len(resumen) > 100:
                descripcion_cumple = si_cumple_text
                descripcion_obs = "La solicitud contiene una descripción de la situación."
    
    # Reemplazar en la plantilla
    template = template.replace("[COMPETENCIA_CUMPLE]", competencia_cumple)
    template = template.replace("[COMPETENCIA_OBS]", competencia_obs)
    template = template.replace("[LEGITIMACION_CUMPLE]", legitimacion_cumple)
    template = template.replace("[LEGITIMACION_OBS]", legitimacion_obs)
    template = template.replace("[PARTES_CUMPLE]", partes_cumple)
    template = template.replace("[PARTES_OBS]", partes_obs)
    template = template.replace("[PROCESO_CUMPLE]", proceso_cumple)
    template = template.replace("[PROCESO_OBS]", proceso_obs)
    template = template.replace("[DESCRIPCION_CUMPLE]", descripcion_cumple)
    template = template.replace("[DESCRIPCION_OBS]", descripcion_obs)
    template = template.replace("[ADMIN_JUSTICIA_CUMPLE]", admin_justicia_cumple)
    template = template.replace("[ADMIN_JUSTICIA_OBS]", admin_justicia_obs)
    template = template.replace("[ANEXOS_CUMPLE]", anexos_cumple)
    template = template.replace("[ANEXOS_OBS]", anexos_obs)
    template = template.replace("[RESUMEN_SOLICITUD]", resumen)
    template = template.replace("[PROBLEMA]", problema)
    
    # Recomendación basada en el análisis
    recomendacion = ""
    
    if competencia_cumple == no_cumple_text or legitimacion_cumple == no_cumple_text:
        recomendacion = "Se recomienda **RECHAZAR** la solicitud por incumplimiento de requisitos esenciales."
    elif proceso_cumple == no_cumple_text or descripcion_cumple == no_cumple_text:
        recomendacion = "Se recomienda **DEVOLVER** la solicitud para que se complemente con la información faltante."
    elif admin_justicia_cumple == no_cumple_text:
        recomendacion = "Se recomienda **RECHAZAR** la solicitud por tratarse de asuntos jurisdiccionales fuera del alcance de la vigilancia administrativa."
    elif cumple_text in [competencia_cumple, legitimacion_cumple, proceso_cumple, descripcion_cumple, admin_justicia_cumple]:
        recomendacion = "Se requiere **INFORMACIÓN ADICIONAL** para determinar la procedencia de la solicitud."
    else:
        recomendacion = "Se recomienda **ADMITIR** la solicitud y dar trámite a la vigilancia judicial administrativa."
    
    template = template.replace("[RECOMENDACION]", recomendacion)
    
    return template


# Sidebar para configuración
with st.sidebar:
    st.title("Configuración")

    # Intentar mostrar el logo si está disponible en línea
    try:
        st.image("assets/logo.png", width=200)  # Asegúrate de que el archivo esté en la carpeta 'assets'
    except:
        # Si no se puede cargar la imagen, intentar mostrar un ícono SVG
        try:
            st.markdown(
                """
                <svg viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" fill-rule="evenodd" clip-rule="evenodd" stroke-linejoin="round" stroke-miterlimit="2" width="200">
                    <path d="M189.08 303.228H94.587l.044-94.446h94.497l-.048 94.446z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M283.528 397.674h-94.493l.044-94.446h94.496l-.047 94.446z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M283.575 303.228H189.08l.046-94.446h94.496l-.047 94.446z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M378.07 303.228h-94.495l.044-94.446h94.498l-.047 94.446z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M189.128 208.779H94.633l.044-94.448h94.498l-.047 94.448z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M378.115 208.779h-94.494l.045-94.448h94.496l-.047 94.448z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M94.587 303.227H.093l.044-96.017h94.496l-.046 96.017z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M94.633 208.779H.138l.046-94.448H94.68l-.047 94.448z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M94.68 115.902H.185L.23 19.885h94.498l-.047 96.017zM472.657 114.331h-94.495l.044-94.446h94.497l-.046 94.446zM94.54 399.244H.046l.044-97.588h94.497l-.047 97.588z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M94.495 492.123H0l.044-94.446H94.54l-.045 94.446zM472.563 303.228H378.07l.044-94.446h94.496l-.047 94.446zM472.61 208.779h-94.495l.044-94.448h94.498l-.047 94.448z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M472.517 397.674h-94.494l.044-94.446h94.497l-.047 94.446z" fill="#1c1c1b" fill-rule="nonzero"/>
                    <path d="M472.47 492.121h-94.493l.044-96.017h94.496l-.047 96.017z" fill="#1c1c1b" fill-rule="nonzero"/>
                </svg>
                """,
                unsafe_allow_html=True,
            )
        except:
            # Si no se puede cargar el ícono SVG, mostrar un título alternativo
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

    # Selección de modo de aplicación
    st.subheader("Modo de aplicación")
    app_mode = st.radio(
        "Selecciona el modo de la aplicación:",
        options=[
            "OCR y Extracción de Texto",
            "Vigilancia Judicial Administrativa",
            "Generación de Documentos",
        ],
    )
    st.session_state["current_tab"] = app_mode

    st.divider()

    # Selección de método de procesamiento
    st.subheader("Método de procesamiento")
    processing_method = st.radio(
        "Selecciona el método para procesar documentos:",
        options=[
            "Auto (recomendado)",
            "OCR API (Standard)",
            "Document Understanding API",
        ],
        index=0,
        help="Auto intentará el mejor método según el tipo de documento",
    )
    st.session_state["processing_method"] = processing_method

    st.divider()

    # Opciones de procesamiento
    st.subheader("Opciones avanzadas")

    # Optimización de imágenes
    st.session_state["config"]["optimize_images"] = st.toggle(
        "Optimizar imágenes",
        value=st.session_state["config"]["optimize_images"],
        help="Mejora la calidad de las imágenes antes de procesarlas",
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

# Función para mostrar la pestaña de OCR y extracción de texto
def show_ocr_tab():
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

    # Crear un control estándar de carga de archivos
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

            # Procesando documentos - mostrar indicador de progreso sin usar st.status
            st.info(f"⏳ Procesando {len(uploaded_files)} documento(s)...")
            
            # Crear barra de progreso
            progress_bar = st.progress(0)

            for idx, file in enumerate(uploaded_files):
                file_type = st.session_state["detected_types"].get(file.name, "PDF")
                progress_text = f"⏳ Procesando {file.name} ({idx+1}/{len(uploaded_files)})..."
                st.markdown(f"<div>{progress_text}</div>", unsafe_allow_html=True)
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
                        st.error(f"Error en {file.name}: {ocr_response['error']}")
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
                                st.success(f"{file.name} procesado correctamente")
                            else:
                                result_text = f"No se encontró texto en {file.name}."
                                st.warning(f"No se encontró texto en {file.name}")
                        else:
                            result_text = (
                                f"Estructura de respuesta inesperada para {file.name}."
                            )
                            st.warning(f"Estructura inesperada en {file.name}")

                    # Almacenar resultados
                    st.session_state["ocr_result"].append(result_text)
                    st.session_state["preview_src"].append(preview_src)
                    st.session_state["file_names"].append(file.name)

                except Exception as e:
                    error_msg = str(e)
                    st.error(f"Error al procesar {file.name}: {error_msg}")

                    # Añadir un resultado vacío para mantener la sincronización
                    st.session_state["ocr_result"].append(f"Error: {error_msg}")
                    st.session_state["preview_src"].append("")
                    st.session_state["file_names"].append(file.name)

            # Actualizar progreso a completado
            progress_bar.progress(1.0)
            st.success(f"✅ Procesamiento completado. {len(st.session_state['ocr_result'])} documento(s) procesados.")

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
                        # Contenido del tab
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

                                    # Botones de descarga mejorados
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

                                    # Opciones de post-procesamiento
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
                                            "🔍 Extraer información",
                                            key=f"extract_{idx}",
                                            use_container_width=True,
                                        ):
                                            processed_text = post_process_text(
                                                st.session_state["ocr_result"][idx],
                                                "extract_info",
                                            )
                                            st.session_state["ocr_result"][
                                                idx
                                            ] = processed_text
                                            st.rerun()

                                    # Opciones específicas de vigilancia judicial
                                    st.markdown(
                                        '<h4 style="margin-top: 2rem; margin-bottom: 1rem;">Vigilancia Judicial</h4>',
                                        unsafe_allow_html=True,
                                    )

                                    action_col3, action_col4 = st.columns(2)

                                    with action_col3:
                                        if st.button(
                                            "⚖️ Crear solicitud de vigilancia",
                                            key=f"vigilancia_{idx}",
                                            use_container_width=True,
                                        ):
                                            solicitud = prepare_vigilancia_judicial(
                                                st.session_state["ocr_result"][idx]
                                            )
                                            st.session_state["ocr_result"][
                                                idx
                                            ] = solicitud
                                            st.rerun()

                                    with action_col4:
                                        if st.button(
                                            "🧐 Control de legalidad",
                                            key=f"control_{idx}",
                                            use_container_width=True,
                                        ):
                                            control = control_legalidad_solicitud(
                                                st.session_state["ocr_result"][idx]
                                            )
                                            st.session_state["ocr_result"][
                                                idx
                                            ] = control
                                            st.rerun()
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


# Función para mostrar la pestaña de vigilancia judicial administrativa
def show_vigilancia_tab():
    st.markdown('<h2 class="sub-header">⚖️ Vigilancia Judicial Administrativa</h2>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div class="info-box">
            <h3>Acerca de la Vigilancia Judicial Administrativa</h3>
            <p>La Vigilancia Judicial Administrativa es una herramienta legal establecida en el artículo 101 de la Ley 270 de 1996 
            y regulada por el Acuerdo No. PSAA11-8716 de 2011 del Consejo Superior de la Judicatura.</p>
            <p>Permite a las partes o intervinientes en un proceso judicial solicitar la supervisión administrativa 
            cuando se presentan irregularidades en la gestión de los procesos judiciales.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Pestañas para las diferentes funciones
    vigilancia_tabs = st.tabs([
        "🔍 Control de Legalidad", 
        "📝 Crear Solicitud", 
        "❓ Información"
    ])
    
    # Pestaña de Control de Legalidad
    with vigilancia_tabs[0]:
        st.subheader("Control de Legalidad de Solicitud")
        
        # Opciones para cargar texto
        source_option = st.radio(
            "Selecciona la fuente del texto a analizar:",
            options=["Cargar documento", "Ingresar texto manualmente"]
        )
        
        if source_option == "Cargar documento":
            uploaded_file = st.file_uploader(
                "Selecciona un documento de solicitud",
                type=["pdf", "jpg", "jpeg", "png", "txt"],
                help="Soporta archivos PDF, imágenes y texto"
            )
            
            if uploaded_file:
                # Determinar tipo de archivo
                if uploaded_file.name.lower().endswith(".txt"):
                    # Es un archivo de texto
                    text_content = uploaded_file.read().decode("utf-8")
                    st.success(f"Archivo {uploaded_file.name} cargado correctamente")
                else:
                    # Es un PDF o imagen, procesar con OCR
                    file_type = detect_document_type(uploaded_file)
                    st.info(f"⏳ Procesando {uploaded_file.name} como {file_type}...")
                    
                    try:
                        result = process_document_auto(api_key, uploaded_file, file_type)
                        ocr_response = result["response"]
                        
                        if "error" in ocr_response:
                            st.error(f"Error al procesar documento: {ocr_response['error']}")
                            text_content = ""
                        else:
                            pages = ocr_response.get("pages", [])
                            if pages:
                                text_content = "\n\n".join(
                                    page.get("markdown", "") for page in pages if "markdown" in page
                                )
                                if text_content.strip():
                                    st.success(f"Documento procesado correctamente")
                                else:
                                    st.warning("No se encontró texto en el documento")
                                    text_content = ""
                            else:
                                st.warning("Estructura de respuesta OCR inesperada")
                                text_content = ""
                    except Exception as e:
                        st.error(f"Error al procesar documento: {str(e)}")
                        text_content = ""
                
                if text_content:
                    # Mostrar previsualización del texto extraído
                    with st.expander("Ver texto extraído", expanded=True):
                        st.markdown(text_content[:1000] + ("..." if len(text_content) > 1000 else ""))
                    
                    # Procesar el control de legalidad
                    if st.button("Realizar Control de Legalidad", use_container_width=True, type="primary"):
                        control_result = control_legalidad_solicitud(text_content)
                        st.markdown(control_result)
        else:
            # Entrada manual de texto
            manual_text = st.text_area(
                "Ingresa el texto de la solicitud de vigilancia judicial",
                height=300,
                help="Copia y pega el contenido de la solicitud"
            )
            
            if manual_text and st.button("Realizar Control de Legalidad", use_container_width=True, type="primary"):
                control_result = control_legalidad_solicitud(manual_text)
                st.markdown(control_result)
    
    # Pestaña de Crear Solicitud
    with vigilancia_tabs[1]:
        st.subheader("Creación de Solicitud de Vigilancia Judicial")
        
        # Formulario para la creación de solicitud
        with st.form("solicitud_form"):
            # Datos del solicitante
            st.markdown("### Datos del Solicitante")
            solicitante_nombre = st.text_input("Nombre completo del solicitante")
            
            col1, col2 = st.columns(2)
            with col1:
                solicitante_tipo_id = st.selectbox(
                    "Tipo de identificación",
                    options=["C.C.", "T.I.", "C.E.", "Pasaporte", "NIT"]
                )
            with col2:
                solicitante_id = st.text_input("Número de identificación")
            
            solicitante_calidad = st.selectbox(
                "Calidad en que actúa",
                options=["Parte demandante", "Parte demandada", "Apoderado", "Tercero interviniente", "Otro"]
            )
            
            solicitante_direccion = st.text_input("Dirección para notificaciones")
            
            col3, col4 = st.columns(2)
            with col3:
                solicitante_email = st.text_input("Correo electrónico")
            with col4:
                solicitante_telefono = st.text_input("Teléfono de contacto")
            
            # Datos del proceso
            st.markdown("### Datos del Proceso")
            proceso_despacho = st.text_input("Despacho judicial")
            proceso_radicado = st.text_input("Número de radicado")
            proceso_tipo = st.text_input("Tipo de proceso")
            proceso_partes = st.text_area("Partes del proceso", height=100)
            
            # Motivo y hechos
            st.markdown("### Motivo y Hechos")
            motivo = st.text_area("Motivo de la solicitud", height=150)
            hechos = st.text_area("Hechos relevantes", height=200)
            
            # Anexos
            anexos = st.text_area("Anexos", height=100)
            
            # Botón de envío
            submitted = st.form_submit_button("Generar Solicitud", use_container_width=True)
        
        if submitted:
            # Crear la solicitud a partir de los datos del formulario
            solicitud_text = f"""
# Solicitud de Vigilancia Judicial Administrativa

## 1. Datos del Solicitante:

- **Nombre completo:** {solicitante_nombre}
- **Identificación:** {solicitante_tipo_id} {solicitante_id}
- **Calidad en que actúa:** {solicitante_calidad}
- **Dirección:** {solicitante_direccion}
- **Correo electrónico:** {solicitante_email}
- **Teléfono de contacto:** {solicitante_telefono}

## 2. Datos del Proceso:

- **Despacho Judicial:** {proceso_despacho}
- **Radicado:** {proceso_radicado}
- **Tipo de proceso:** {proceso_tipo}
- **Partes:** 
{proceso_partes}

## 3. Motivo de la Solicitud:

{motivo}

## 4. Hechos:

{hechos}

## 5. Petición:

De conformidad con lo dispuesto en el artículo 101 de la Ley 270 de 1996, reglamentado mediante el Acuerdo No. PSAA11-8716 de 2011 del Consejo Superior de la Judicatura y la Circular PCSJC17-43 de 2017, solicito respetuosamente al Honorable Consejo Seccional de la Judicatura que tramite la presente solicitud de Vigilancia Judicial Administrativa.

## 6. Anexos:

{anexos}

## 7. Notificaciones:

Recibiré notificaciones en la dirección y correo electrónico indicados en los datos del solicitante.

Atentamente,


{solicitante_nombre}
{solicitante_tipo_id} {solicitante_id}
            """
            
            st.markdown(solicitud_text)
            
            # Opciones de descarga
            st.subheader("Descargar Solicitud")
            col_d1, col_d2, col_d3 = st.columns(3)
            
            with col_d1:
                st.markdown(
                    create_download_link(
                        solicitud_text,
                        "text/markdown",
                        "Solicitud_Vigilancia_Judicial.md",
                        "markdown-button",
                    ),
                    unsafe_allow_html=True,
                )
            
            with col_d2:
                st.markdown(
                    create_download_link(
                        solicitud_text,
                        "text/plain",
                        "Solicitud_Vigilancia_Judicial.txt",
                        "text-button",
                    ),
                    unsafe_allow_html=True,
                )
            
            with col_d3:
                # Convertir a JSON para descarga
                json_data = json.dumps(
                    {
                        "solicitud": "Vigilancia Judicial Administrativa",
                        "solicitante": {
                            "nombre": solicitante_nombre,
                            "identificacion": f"{solicitante_tipo_id} {solicitante_id}",
                            "calidad": solicitante_calidad,
                            "contacto": {
                                "direccion": solicitante_direccion,
                                "email": solicitante_email,
                                "telefono": solicitante_telefono
                            }
                        },
                        "proceso": {
                            "despacho": proceso_despacho,
                            "radicado": proceso_radicado,
                            "tipo": proceso_tipo,
                            "partes": proceso_partes
                        },
                        "contenido": {
                            "motivo": motivo,
                            "hechos": hechos,
                            "anexos": anexos
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                
                st.markdown(
                    create_download_link(
                        json_data,
                        "application/json",
                        "Solicitud_Vigilancia_Judicial.json",
                        "json-button",
                    ),
                    unsafe_allow_html=True,
                )
    
    # Pestaña de Información
    with vigilancia_tabs[2]:
        st.subheader("Información sobre Vigilancia Judicial Administrativa")
        
        st.markdown(
            """
            ### ¿Qué es la Vigilancia Judicial Administrativa?

            La Vigilancia Judicial Administrativa es una herramienta legal que permite a las partes o intervinientes 
            en un proceso judicial solicitar la supervisión administrativa cuando se presentan irregularidades 
            en la gestión de los procesos judiciales.

            ### Marco Normativo

            - **Artículo 101 de la Ley 270 de 1996**: Establece la competencia de los Consejos Seccionales 
            de la Judicatura para ejercer el control del rendimiento y gestión de los despachos judiciales.
            
            - **Acuerdo No. PSAA11-8716 de 2011**: Reglamenta el ejercicio de la función de control por parte 
            de los Consejos Seccionales de la Judicatura.
            
            - **Circular PCSJC17-43 de 2017**: Establece directrices adicionales para el trámite de solicitudes 
            de vigilancia judicial administrativa.

            ### ¿Cuándo procede?

            La vigilancia judicial administrativa procede en casos como:

            - Demoras injustificadas en el trámite de los procesos
            - Incumplimiento de términos judiciales
            - Irregularidades administrativas en el manejo de expedientes
            - Problemas en la gestión administrativa de los despachos judiciales

            ### ¿Qué NO incluye?

            Es importante tener en cuenta que la vigilancia judicial administrativa:

            - **NO** puede interferir con decisiones jurisdiccionales (sentencias, autos, etc.)
            - **NO** reemplaza los recursos legales dentro del proceso
            - **NO** constituye una instancia adicional del proceso
            - **NO** se utiliza para cuestionar el criterio jurídico del juez

            ### Requisitos de la solicitud

            Para que la solicitud sea admitida debe cumplir con los siguientes requisitos:

            1. Identificación clara del solicitante y su interés legítimo en el proceso
            2. Información precisa del proceso judicial (despacho, radicado, tipo)
            3. Descripción clara de la situación administrativa irregular
            4. Aporte de pruebas que sustenten la solicitud
            
            ### Procedimiento

            1. Presentación de la solicitud ante el Consejo Seccional de la Judicatura
            2. Admisión, inadmisión o rechazo de la solicitud
            3. En caso de admisión, solicitud de informes al Despacho Judicial
            4. Análisis de la situación y adopción de medidas administrativas
            5. Seguimiento al cumplimiento de las medidas adoptadas
            
            ### Resultados posibles

            - Exhorto al cumplimiento de términos judiciales
            - Adopción de medidas de descongestión
            - Medidas administrativas para mejorar la gestión
            - Remisión a autoridades disciplinarias (cuando sea procedente)
            """
        )


# Función para mostrar la pestaña de generación de documentos
def show_documents_tab():
    st.markdown('<h2 class="sub-header">📝 Generación de Documentos</h2>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div class="info-box">
            <p>Esta sección te permite generar documentos legales y administrativos a partir de plantillas predefinidas o texto extraído de otros documentos.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Pestañas para diferentes tipos de documentos
    document_tabs = st.tabs([
        "📋 Solicitudes Administrativas", 
        "📑 Documentos Legales", 
        "📄 Plantillas Personalizadas"
    ])
    
    # Pestaña de Solicitudes Administrativas
    with document_tabs[0]:
        st.subheader("Generación de Solicitudes Administrativas")
        
        # Selección del tipo de solicitud
        solicitud_tipo = st.selectbox(
            "Selecciona el tipo de solicitud a generar:",
            options=[
                "Vigilancia Judicial Administrativa",
                "Derecho de Petición",
                "Solicitud de Desarchivo",
                "Solicitud de Copias",
                "Solicitud de Impulso Procesal"
            ]
        )
        
        # En función del tipo seleccionado, mostrar el formulario correspondiente
        if solicitud_tipo == "Vigilancia Judicial Administrativa":
            # Este caso ya está implementado en la pestaña de Vigilancia Judicial
            st.info("La generación de solicitudes de Vigilancia Judicial Administrativa está disponible en la pestaña 'Vigilancia Judicial Administrativa' → 'Crear Solicitud'.")
            
            if st.button("Ir a Vigilancia Judicial Administrativa"):
                st.session_state["current_tab"] = "Vigilancia Judicial Administrativa"
                st.rerun()
        
        elif solicitud_tipo == "Derecho de Petición":
            with st.form("peticion_form"):
                st.markdown("### Datos del Solicitante")
                peticion_nombre = st.text_input("Nombre completo")
                peticion_id = st.text_input("Número de identificación")
                peticion_direccion = st.text_input("Dirección para notificaciones")
                peticion_email = st.text_input("Correo electrónico")
                peticion_telefono = st.text_input("Teléfono de contacto")
                
                st.markdown("### Datos del Destinatario")
                peticion_destinatario = st.text_input("Entidad o funcionario destinatario")
                peticion_cargo = st.text_input("Cargo (si aplica)")
                peticion_entidad = st.text_input("Entidad")
                
                st.markdown("### Contenido de la Petición")
                peticion_asunto = st.text_input("Asunto")
                peticion_hechos = st.text_area("Hechos", height=150)
                peticion_peticiones = st.text_area("Peticiones concretas", height=150)
                peticion_fundamentos = st.text_area("Fundamentos de derecho", height=100)
                peticion_anexos = st.text_area("Anexos", height=50)
                
                submitted = st.form_submit_button("Generar Derecho de Petición", use_container_width=True)
            
            if submitted:
                # Generar el documento de Derecho de Petición
                peticion_text = f"""
# DERECHO DE PETICIÓN

**{peticion_destinatario}**  
**{peticion_cargo}**  
**{peticion_entidad}**  
E.S.D.

## Ref: {peticion_asunto}

Yo, **{peticion_nombre}**, identificado(a) con cédula de ciudadanía No. {peticion_id}, actuando en nombre propio, con fundamento en el artículo 23 de la Constitución Política de Colombia y la Ley 1755 de 2015, me permito presentar ante usted el siguiente Derecho de Petición:

### HECHOS

{peticion_hechos}

### PETICIONES

{peticion_peticiones}

### FUNDAMENTOS DE DERECHO

{peticion_fundamentos}

### ANEXOS

{peticion_anexos}

### NOTIFICACIONES

Recibiré notificaciones en la siguiente dirección:

- Dirección física: {peticion_direccion}
- Correo electrónico: {peticion_email}
- Teléfono: {peticion_telefono}

Cordialmente,


**{peticion_nombre}**  
C.C. {peticion_id}
                """
                
                st.markdown(peticion_text)
                
                # Opciones de descarga
                st.subheader("Descargar Documento")
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.markdown(
                        create_download_link(
                            peticion_text,
                            "text/markdown",
                            "Derecho_de_Peticion.md",
                            "markdown-button",
                        ),
                        unsafe_allow_html=True,
                    )
                
                with col_d2:
                    st.markdown(
                        create_download_link(
                            peticion_text,
                            "text/plain",
                            "Derecho_de_Peticion.txt",
                            "text-button",
                        ),
                        unsafe_allow_html=True,
                    )
        
        else:
            st.info("Esta funcionalidad estará disponible próximamente.")
    
    # Pestaña de Documentos Legales
    with document_tabs[1]:
        st.subheader("Generación de Documentos Legales")
        
        # Selección del tipo de documento
        documento_tipo = st.selectbox(
            "Selecciona el tipo de documento legal a generar:",
            options=[
                "Poder General",
                "Poder Especial",
                "Contrato de Arrendamiento",
                "Contrato de Prestación de Servicios",
                "Recurso de Reposición",
                "Tutela"
            ]
        )
        
        st.info("Esta funcionalidad estará disponible próximamente.")
    
    # Pestaña de Plantillas Personalizadas
    with document_tabs[2]:
        st.subheader("Plantillas Personalizadas")
        
        st.markdown(
            """
            En esta sección puedes crear tus propias plantillas personalizadas o utilizar documentos 
            previamente procesados con OCR como base para nuevos documentos.
            """
        )
        
        # Opciones para usar texto previo o nuevo
        source_option = st.radio(
            "Selecciona la fuente para crear la plantilla:",
            options=["Usar texto de OCR previo", "Crear plantilla desde cero"]
        )
        
        if source_option == "Usar texto de OCR previo":
            # Mostrar resultados previos de OCR si existen
            if st.session_state.get("ocr_result") and len(st.session_state["ocr_result"]) > 0:
                # Permitir al usuario seleccionar qué resultado usar
                ocr_options = [f"{st.session_state['file_names'][i]} ({len(st.session_state['ocr_result'][i])} caracteres)" 
                              for i in range(len(st.session_state["ocr_result"]))]
                
                selected_ocr = st.selectbox(
                    "Selecciona el texto extraído que deseas usar:",
                    options=ocr_options
                )
                
                # Obtener el índice del texto seleccionado
                selected_idx = ocr_options.index(selected_ocr)
                
                # Mostrar el texto seleccionado en un editor
                template_text = st.text_area(
                    "Edita el texto según necesites para tu plantilla:",
                    value=st.session_state["ocr_result"][selected_idx],
                    height=300
                )
                
                if st.button("Guardar como plantilla", use_container_width=True):
                    # Aquí se podría implementar la lógica para guardar plantillas
                    st.success("Plantilla guardada correctamente")
            else:
                st.warning("No hay resultados previos de OCR disponibles. Primero procesa algún documento en la pestaña 'OCR y Extracción de Texto'.")
        else:
            # Crear plantilla desde cero
            template_name = st.text_input("Nombre de la plantilla:")
            template_content = st.text_area(
                "Contenido de la plantilla (puedes usar marcadores como [NOMBRE], [FECHA], etc.):",
                height=300
            )
            
            if st.button("Guardar plantilla", use_container_width=True):
                # Aquí se podría implementar la lógica para guardar plantillas
                st.success(f"Plantilla '{template_name}' guardada correctamente")


# Contenedor principal
st.markdown('<h1 class="main-header">🔍 Mistral OCR App</h1>', unsafe_allow_html=True)

st.markdown(
    """
<div class="info-box">
  📝 Esta aplicación extrae texto de documentos PDF e imágenes manteniendo su estructura original. 
  Simplemente sube tus archivos y la IA hará el resto. También incluye funcionalidades para Vigilancia Judicial Administrativa 
  y generación de documentos.
</div>
""",
    unsafe_allow_html=True,
)

# Mostrar mensajes de estado actuales
display_status_messages()

# Área principal basada en la pestaña seleccionada
if st.session_state["current_tab"] == "OCR y Extracción de Texto":
    show_ocr_tab()
elif st.session_state["current_tab"] == "Vigilancia Judicial Administrativa":
    show_vigilancia_tab()
elif st.session_state["current_tab"] == "Generación de Documentos":
    show_documents_tab()

# Pie de página
st.markdown(
    """
<div style="text-align: center; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #DADCE0; color: #666;">
    <p>Mistral OCR App v3.0 | Desarrollada con Streamlit y Mistral AI</p>
</div>
""",
    unsafe_allow_html=True,
)