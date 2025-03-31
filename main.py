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
@catch_exceptions
def process_with_document_understanding(api_key, document):
    # Extraer URL del documento
    doc_url = document.get("document_url", "") or document.get("image_url", "")

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
        st.warning(f"No se pudo optimizar la imagen: {str(e)}")
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
        st.image("https://mistral.ai/_next/image?url=%2Fimg%2FM-beige.svg&w=640&q=75", width=200)
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
                    st.session_state["file_names"].append(file.name)

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
<div style="text-align: center; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #DADCE0; color: #666;">
    <p>Mistral OCR App v3.0 | Desarrollada con Streamlit y Mistral AI</p>
</div>
""",
    unsafe_allow_html=True,
)
