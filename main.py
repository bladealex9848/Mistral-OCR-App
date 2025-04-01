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
import traceback
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MistralOCR")

# Versión de la aplicación
APP_VERSION = "4.1"

# Configuración inicial de la página
st.set_page_config(
    layout="wide",
    page_title="Aplicación Mistral OCR",
    page_icon="🔍",
    initial_sidebar_state="collapsed",  # Menú lateral contraído por defecto
)

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
        margin: 0.25rem 0;
        width: 100%;
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

    /* Mejoras para visualización en dispositivos móviles */
    @media (max-width: 768px) {
        .stButton>button {
            width: 100%;
            margin: 5px 0;
        }
        .st-emotion-cache-16txtl3 {
            padding: 1rem 0.5rem;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# Inicializar variables de estado de sesión para persistencia
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = []
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = []
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = []
if "file_names" not in st.session_state:
    st.session_state["file_names"] = []
if "processing_complete" not in st.session_state:
    st.session_state["processing_complete"] = False
if "show_technical_details" not in st.session_state:
    st.session_state["show_technical_details"] = False

# ====================== FUNCIONES UTILITARIAS ======================


def get_mistral_api_key():
    """
    Obtiene la API key de Mistral de diferentes fuentes.
    Orden de prioridad: 1. Streamlit secrets, 2. Variables de entorno
    """
    try:
        # 1. Intentar obtener de Streamlit secrets
        return st.secrets["MISTRAL_API_KEY"]
    except (KeyError, FileNotFoundError):
        # 2. Intentar obtener de variables de entorno
        api_key = os.environ.get("MISTRAL_API_KEY")
        if api_key and api_key.strip():
            return api_key

    # 3. No se encontró API key
    return None


def validate_api_key(api_key):
    """
    Verifica la validez de la API key.
    """
    if not api_key:
        return False, "No se ha proporcionado API key"

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Intentar una solicitud simple para verificar la clave con timeout para evitar bloqueos
        response = requests.get(
            "https://api.mistral.ai/v1/models", headers=headers, timeout=10
        )

        if response.status_code == 200:
            return True, "API key válida"
        elif response.status_code == 401:
            return False, "API key no válida o expirada"
        else:
            return False, f"Error verificando API key: código {response.status_code}"
    except requests.exceptions.ConnectionError:
        return (
            False,
            "Error de conexión al verificar la API key. Comprueba tu conexión a internet.",
        )
    except requests.exceptions.Timeout:
        return (
            False,
            "Timeout al verificar la API key. El servidor está tardando demasiado en responder.",
        )
    except Exception as e:
        logger.error(f"Error inesperado al validar API key: {str(e)}")
        return False, f"Error al validar API key: {str(e)}"


def prepare_image_for_ocr(file_data):
    """
    Prepara una imagen para ser procesada con OCR, asegurando formato óptimo.
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
        logger.warning(f"No se pudo optimizar la imagen: {str(e)}")
        return file_data, "image/jpeg"  # Formato por defecto


def extract_text_from_ocr_response(response):
    """
    Extrae texto de diferentes formatos de respuesta OCR.
    """
    try:
        # Caso 1: Si hay páginas con markdown
        if "pages" in response and isinstance(response["pages"], list):
            pages = response["pages"]
            if pages and "markdown" in pages[0]:
                markdown_text = "\n\n".join(
                    page.get("markdown", "") for page in pages if "markdown" in page
                )
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
        logger.error(f"Error al extraer texto de la respuesta OCR: {str(e)}")
        return {"error": f"Error al procesar la respuesta: {str(e)}"}


def extract_all_text_fields(data, prefix=""):
    """
    Función recursiva para extraer todos los campos de texto de un diccionario anidado.
    """
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


def create_download_link(data, filetype, filename):
    """
    Crea un enlace de descarga para los resultados.
    """
    try:
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:{filetype};base64,{b64}" download="{filename}" class="download-button">Descargar {filename}</a>'
        return href
    except Exception as e:
        logger.error(f"Error al crear enlace de descarga: {str(e)}")
        return f'<span style="color: red;">Error al crear enlace de descarga: {str(e)}</span>'


# ====================== FUNCIONES DE PROCESAMIENTO OCR ======================


def process_image_with_rest(api_key, image_data):
    """
    Procesa una imagen utilizando API REST directamente (más confiable para imágenes).
    """
    with st.status("Procesando imagen con REST API...", expanded=True) as status:
        try:
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
                status.update(label=f"Imagen detectada como {mime_type}")
            except Exception as e:
                logger.warning(f"Error al detectar formato de imagen: {str(e)}")
                # Si falla, usar un tipo genérico
                mime_type = "image/jpeg"
                bytes_data = (
                    image_data if not hasattr(image_data, "read") else image_data.read()
                )

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

            status.update(label="Enviando imagen a la API...")

            # Hacer la solicitud a la API de Mistral con timeout
            response = requests.post(
                "https://api.mistral.ai/v1/ocr",
                json=payload,
                headers=headers,
                timeout=60,  # 60 segundos de timeout para imágenes grandes
            )

            # Revisar si la respuesta fue exitosa
            if response.status_code == 200:
                result = response.json()
                status.update(label="Imagen procesada correctamente", state="complete")
                return extract_text_from_ocr_response(result)
            else:
                error_message = (
                    f"Error en API OCR (código {response.status_code}): {response.text}"
                )
                logger.error(error_message)
                status.update(label="Error al procesar la imagen", state="error")
                return {"error": error_message}

        except requests.exceptions.Timeout:
            error_message = (
                "Timeout al procesar la imagen. La operación tomó demasiado tiempo."
            )
            logger.error(error_message)
            status.update(label="Timeout al procesar la imagen", state="error")
            return {"error": error_message}

        except requests.exceptions.ConnectionError:
            error_message = "Error de conexión al procesar la imagen. Comprueba tu conexión a internet."
            logger.error(error_message)
            status.update(label="Error de conexión", state="error")
            return {"error": error_message}

        except Exception as e:
            error_message = f"Error al procesar imagen: {str(e)}"
            logger.error(f"{error_message}\n{traceback.format_exc()}")
            status.update(label=f"Error: {str(e)}", state="error")
            return {"error": error_message}


def process_ocr_with_curl(api_key, document, method="REST", show_debug=False):
    """
    Realiza solicitud OCR usando cURL para mayor compatibilidad y control.
    """
    # Crear un directorio temporal para los archivos
    temp_dir = None
    temp_files = []

    with st.status("Iniciando procesamiento OCR...", expanded=True) as status:
        try:
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Directorio temporal creado: {temp_dir}")

            # Preparar el documento según su tipo
            if document.get("type") == "document_url":
                url = document["document_url"]
                if url.startswith("data:application/pdf;base64,"):
                    # Guardar el PDF base64 en un archivo temporal
                    try:
                        status.update(label="Preparando archivo PDF...")
                        pdf_base64 = url.replace("data:application/pdf;base64,", "")
                        temp_pdf_path = os.path.join(temp_dir, "temp_document.pdf")
                        temp_files.append(temp_pdf_path)

                        with open(temp_pdf_path, "wb") as f:
                            f.write(base64.b64decode(pdf_base64))

                        logger.info(f"PDF guardado temporalmente en: {temp_pdf_path}")

                        # Crear un comando cURL para subir el archivo
                        upload_command = [
                            "curl",
                            "--fail",  # Fallar si hay error HTTP
                            "--silent",  # Silenciar progreso
                            "--show-error",  # Mostrar errores
                            "--connect-timeout",
                            "30",  # Timeout de conexión
                            "--max-time",
                            "120",  # Timeout total
                            "https://api.mistral.ai/v1/files",
                            "-H",
                            f"Authorization: Bearer {api_key}",
                            "-F",
                            "purpose=ocr",
                            "-F",
                            f"file=@{temp_pdf_path}",
                        ]

                        # Ejecutar el comando y capturar la salida
                        status.update(label="Subiendo PDF al servidor de Mistral...")
                        result = subprocess.run(
                            upload_command, capture_output=True, text=True
                        )

                        if result.returncode != 0:
                            error_msg = f"Error al subir archivo (código {result.returncode}): {result.stderr}"
                            logger.error(error_msg)
                            status.update(label="Error al subir archivo", state="error")
                            return {"error": error_msg}

                        # Parsear el resultado para obtener el ID del archivo
                        file_data = json.loads(result.stdout)
                        file_id = file_data.get("id")
                        if not file_id:
                            status.update(
                                label="Error: No se pudo obtener ID del archivo",
                                state="error",
                            )
                            return {
                                "error": "No se pudo obtener el ID del archivo subido"
                            }

                        logger.info(f"Archivo subido exitosamente. ID: {file_id}")
                        status.update(label=f"Archivo subido. ID: {file_id}")

                        # Obtener URL firmada
                        get_url_command = [
                            "curl",
                            "--fail",
                            "--silent",
                            "--show-error",
                            "--connect-timeout",
                            "30",
                            "--max-time",
                            "60",
                            "-X",
                            "GET",
                            f"https://api.mistral.ai/v1/files/{file_id}/url?expiry=24",
                            "-H",
                            "Accept: application/json",
                            "-H",
                            f"Authorization: Bearer {api_key}",
                        ]

                        status.update(label="Obteniendo URL firmada...")
                        url_result = subprocess.run(
                            get_url_command, capture_output=True, text=True
                        )

                        if url_result.returncode != 0:
                            error_msg = f"Error al obtener URL firmada (código {url_result.returncode}): {url_result.stderr}"
                            logger.error(error_msg)
                            status.update(
                                label="Error al obtener URL firmada", state="error"
                            )
                            return {"error": error_msg}

                        url_data = json.loads(url_result.stdout)
                        signed_url = url_data.get("url")
                        if not signed_url:
                            status.update(
                                label="Error: No se pudo obtener URL firmada",
                                state="error",
                            )
                            return {"error": "No se pudo obtener la URL firmada"}

                        # Usar la URL firmada para el OCR
                        document = {"type": "document_url", "document_url": signed_url}
                        logger.info("URL firmada obtenida correctamente para OCR")
                        status.update(label="URL firmada obtenida correctamente")

                    except json.JSONDecodeError as e:
                        error_msg = f"Error al parsear respuesta del servidor: {str(e)}"
                        logger.error(error_msg)
                        status.update(
                            label="Error: Formato de respuesta incorrecto",
                            state="error",
                        )
                        return {"error": error_msg}
                    except Exception as e:
                        error_msg = f"Error al procesar PDF: {str(e)}"
                        logger.error(f"{error_msg}\n{traceback.format_exc()}")
                        status.update(
                            label=f"Error al procesar PDF: {str(e)}", state="error"
                        )
                        return {"error": error_msg}

            elif document.get("type") == "image_url":
                # Para imágenes, procesar directamente con la API REST
                url = document["image_url"]
                if url.startswith("data:"):
                    # Es una imagen en base64
                    try:
                        status.update(label="Procesando imagen...")
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
                        error_msg = f"Error al procesar imagen base64: {str(e)}"
                        logger.error(f"{error_msg}\n{traceback.format_exc()}")
                        status.update(
                            label=f"Error al procesar imagen: {str(e)}", state="error"
                        )
                        return {"error": error_msg}

            # Preparar datos para la solicitud OCR
            json_data = {
                "model": "mistral-ocr-latest",
                "document": document,
                "include_image_base64": True,
            }

            # Guardar en archivo temporal
            temp_json_path = os.path.join(temp_dir, "request.json")
            temp_files.append(temp_json_path)

            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            # Comando para OCR con mejores prácticas
            ocr_command = [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "30",
                "--max-time",
                "180",  # 3 minutos para documentos grandes
                "https://api.mistral.ai/v1/ocr",
                "-H",
                "Content-Type: application/json",
                "-H",
                f"Authorization: Bearer {api_key}",
                "-d",
                f"@{temp_json_path}",
            ]

            # Ejecutar OCR
            status.update(label="Ejecutando OCR con cURL...")
            if show_debug:
                # Mostrar comando sin API key
                safe_command = " ".join(ocr_command).replace(api_key, "****")
                st.code(safe_command, language="bash")

            logger.info("Ejecutando OCR con cURL")
            ocr_result = subprocess.run(ocr_command, capture_output=True, text=True)

            if ocr_result.returncode != 0:
                error_details = {
                    "error": f"Error en OCR (código {ocr_result.returncode})",
                    "stderr": ocr_result.stderr,
                    "stdout": ocr_result.stdout,
                }
                logger.error(
                    f"Error durante la ejecución de cURL: {error_details['error']}"
                )
                status.update(label=f"Error: {error_details['error']}", state="error")
                return {"error": json.dumps(error_details)}

            # Comprobar si hay errores en la respuesta
            if (
                "error" in ocr_result.stdout.lower()
                or "not found" in ocr_result.stdout.lower()
            ):
                status.update(
                    label="API respondió con error, intentando método alternativo...",
                    state="running",
                )

                if show_debug:
                    st.code(ocr_result.stdout, language="json")

                # Intentar método alternativo
                if "document understanding" not in method.lower():
                    st.info(
                        "Intentando procesar con el método Document Understanding..."
                    )
                    return process_with_document_understanding(api_key, document)

            try:
                # Intentar parsear la respuesta JSON
                response_json = json.loads(ocr_result.stdout)
                status.update(label="Procesando respuesta OCR...")

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
                        label="Texto extraído correctamente", state="complete"
                    )
                    return {"pages": [{"markdown": extraction_result["text"]}]}
                else:
                    status.update(
                        label="Texto extraído con formato inesperado", state="complete"
                    )
                    return response_json

            except json.JSONDecodeError:
                logger.warning(
                    f"Error al parsear JSON de respuesta OCR: {ocr_result.stdout[:200]}..."
                )

                status.update(label="Procesando respuesta no-JSON...")

                if not ocr_result.stdout.strip():
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
                        label="Texto extraído en formato plano", state="complete"
                    )
                    return {"pages": [{"markdown": ocr_result.stdout}]}

                status.update(label="Error al parsear respuesta OCR", state="error")
                return {
                    "error": f"Error al parsear respuesta OCR: {ocr_result.stdout[:200]}..."
                }

        except Exception as e:
            error_msg = f"Error durante el procesamiento OCR: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            status.update(label=f"Error inesperado: {str(e)}", state="error")
            return {"error": error_msg}

        finally:
            # Limpiar archivos temporales de manera segura
            if temp_files:
                for file_path in temp_files:
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                            logger.debug(f"Archivo temporal eliminado: {file_path}")
                    except Exception as e:
                        logger.warning(
                            f"No se pudo eliminar archivo temporal {file_path}: {str(e)}"
                        )

            # Limpiar directorio temporal
            if temp_dir and os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                    logger.debug(f"Directorio temporal eliminado: {temp_dir}")
                except Exception as e:
                    logger.warning(
                        f"No se pudo eliminar directorio temporal {temp_dir}: {str(e)}"
                    )


def process_with_document_understanding(api_key, document):
    """
    Método alternativo usando Document Understanding para extracción de texto.
    """
    temp_json_path = None

    with st.status(
        "Utilizando método alternativo: Document Understanding API...", expanded=True
    ) as status:
        try:
            # Extraer URL del documento
            doc_url = document.get("document_url", "") or document.get("image_url", "")

            if not doc_url:
                status.update(
                    label="Error: No se pudo extraer URL del documento", state="error"
                )
                return {
                    "error": "No se pudo extraer URL del documento para el método alternativo"
                }

            # Construir datos para chat completions
            doc_type = "document_url" if "document_url" in document else "image_url"
            request_data = {
                "model": "mistral-large-latest",  # Modelo avanzado para comprensión de documentos
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

            # Guardar la solicitud en un archivo temporal
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump(request_data, tmp, ensure_ascii=False, indent=2)
                temp_json_path = tmp.name

            # Comando cURL para Document Understanding con mejor manejo de errores
            du_command = [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "30",
                "--max-time",
                "300",  # 5 minutos para documentos complejos
                "https://api.mistral.ai/v1/chat/completions",
                "-H",
                "Content-Type: application/json",
                "-H",
                f"Authorization: Bearer {api_key}",
                "-d",
                f"@{temp_json_path}",
            ]

            status.update(label="Procesando con Document Understanding API...")
            logger.info("Ejecutando Document Understanding con cURL")
            du_result = subprocess.run(du_command, capture_output=True, text=True)

            # Verificar resultado
            if du_result.returncode != 0:
                error_msg = f"Error en Document Understanding (código {du_result.returncode}): {du_result.stderr}"
                logger.error(error_msg)
                status.update(label="Error en Document Understanding", state="error")
                return {"error": error_msg}

            try:
                result_json = json.loads(du_result.stdout)
                if "choices" in result_json and len(result_json["choices"]) > 0:
                    content = result_json["choices"][0]["message"]["content"]

                    # Simular el formato de respuesta de OCR
                    pages = [{"markdown": content}]
                    status.update(
                        label="Texto extraído correctamente", state="complete"
                    )
                    return {"pages": pages}
                else:
                    error_msg = "Respuesta no válida de Document Understanding"
                    logger.error(f"{error_msg}: {du_result.stdout[:200]}...")
                    status.update(label=error_msg, state="error")
                    return {"error": error_msg}
            except json.JSONDecodeError:
                error_msg = "Error al parsear respuesta JSON de Document Understanding"
                logger.error(f"{error_msg}: {du_result.stdout[:200]}...")
                status.update(label=error_msg, state="error")
                return {"error": error_msg}

        except Exception as e:
            error_msg = (
                f"Error durante el procesamiento con Document Understanding: {str(e)}"
            )
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            status.update(label=f"Error: {str(e)}", state="error")
            return {"error": error_msg}

        finally:
            # Limpiar archivo temporal
            if temp_json_path and os.path.exists(temp_json_path):
                try:
                    os.unlink(temp_json_path)
                    logger.debug(f"Archivo temporal eliminado: {temp_json_path}")
                except Exception as e:
                    logger.warning(
                        f"No se pudo eliminar archivo temporal {temp_json_path}: {str(e)}"
                    )


# ====================== FUNCIÓN PRINCIPAL DE PROCESAMIENTO ======================


def process_document(
    api_key,
    source,
    idx,
    total,
    source_type,
    processing_method,
    show_debug,
    optimize_images,
    direct_api,
):
    """
    Función para procesar un solo documento.
    """
    file_bytes = None
    file_type = None

    try:
        logger.info(f"Procesando documento {idx+1}/{total}")

        # Determinar el tipo de archivo automáticamente
        if source_type == "Archivo local":
            file_name = source.name
            mime = mimetypes.guess_type(file_name)[0]
            if mime == "application/pdf":
                file_type = "PDF"
            elif mime and mime.startswith("image/"):
                file_type = "Imagen"
            else:
                logger.warning(f"Tipo de archivo no soportado: {mime} para {file_name}")
                return {
                    "success": False,
                    "result_text": f"Tipo de archivo no soportado: {file_name}",
                    "preview_src": "",
                    "file_name": file_name,
                    "file_bytes": None,
                    "raw_response": None,
                }
        elif source_type == "URL":
            source_name = source.split("/")[-1]
            if source.lower().endswith(".pdf"):
                file_type = "PDF"
            else:
                file_type = "Imagen"  # Assume image for other URLs for simplicity, more robust detection could be added
        else:
            return {
                "success": False,
                "result_text": "Tipo de fuente desconocido.",
                "preview_src": "",
                "file_name": f"Error-{idx+1}",
                "file_bytes": None,
                "raw_response": None,
            }

        # Preparar el documento según el tipo y la fuente
        if file_type == "PDF":
            if source_type == "URL":
                document = {
                    "type": "document_url",
                    "document_url": source.strip(),
                }
                preview_src = source.strip()
                file_name = source.split("/")[-1]
            else:
                try:
                    file_bytes = source.read()
                    encoded_pdf = base64.b64encode(file_bytes).decode("utf-8")
                    document = {
                        "type": "document_url",
                        "document_url": f"data:application/pdf;base64,{encoded_pdf}",
                    }
                    preview_src = f"data:application/pdf;base64,{encoded_pdf}"
                    file_name = source.name
                    # Reiniciar el cursor del archivo para futuras operaciones
                    source.seek(0)
                except Exception as e:
                    logger.error(f"Error al leer PDF: {str(e)}")
                    return {
                        "success": False,
                        "result_text": f"Error al leer el archivo PDF: {str(e)}",
                        "preview_src": "",
                        "file_name": getattr(source, "name", f"PDF-Error-{idx+1}"),
                        "file_bytes": None,
                        "raw_response": None,
                    }
        elif file_type == "Imagen":
            if source_type == "URL":
                document = {
                    "type": "image_url",
                    "image_url": source.strip(),
                }
                preview_src = source.strip()
                file_name = source.split("/")[-1]
            else:
                try:
                    # Leer los bytes de la imagen
                    file_bytes = source.read()

                    # Optimizar la imagen si está habilitado
                    if optimize_images:
                        file_bytes, mime_type = prepare_image_for_ocr(file_bytes)
                    else:
                        mime_type = source.type

                    # Codificar en base64 para enviar a la API
                    encoded_image = base64.b64encode(file_bytes).decode("utf-8")

                    # Preparar el documento con la imagen
                    document = {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{encoded_image}",
                    }
                    preview_src = f"data:{mime_type};base64,{encoded_image}"
                    file_name = source.name

                    # Reiniciar el cursor del archivo para futuras operaciones
                    source.seek(0)
                except Exception as e:
                    logger.error(f"Error al leer imagen: {str(e)}")
                    return {
                        "success": False,
                        "result_text": f"Error al leer la imagen: {str(e)}",
                        "preview_src": "",
                        "file_name": getattr(source, "name", f"Imagen-Error-{idx+1}"),
                        "file_bytes": None,
                        "raw_response": None,
                    }
        else:
            return {
                "success": False,
                "result_text": f"Tipo de archivo no soportado para {source_name if 'source_name' in locals() else 'documento'}.",
                "preview_src": "",
                "file_name": (
                    source_name if "source_name" in locals() else f"Error-{idx+1}"
                ),
                "file_bytes": None,
                "raw_response": None,
            }

        # Procesar documento con el método apropiado
        try:
            # Si es una imagen y está habilitada la API REST directa, usar ese método
            if file_type == "Imagen" and direct_api and source_type == "Archivo local":
                ocr_response = process_image_with_rest(api_key, file_bytes)
                # Convertir la respuesta al formato esperado por el resto del código
                if "text" in ocr_response:
                    ocr_response = {"pages": [{"markdown": ocr_response["text"]}]}
            else:
                # Determinar el método a usar basado en la selección
                if processing_method == "OCR API (Standard)":
                    ocr_response = process_ocr_with_curl(
                        api_key, document, method="OCR", show_debug=show_debug
                    )
                elif processing_method == "Document Understanding API":
                    ocr_response = process_with_document_understanding(
                        api_key, document
                    )
                else:  # Auto
                    ocr_response = process_ocr_with_curl(
                        api_key, document, method="Auto", show_debug=show_debug
                    )
        except Exception as e:
            logger.error(
                f"Error en el procesamiento OCR: {str(e)}\n{traceback.format_exc()}"
            )
            return {
                "success": False,
                "result_text": f"Error durante el procesamiento OCR: {str(e)}",
                "preview_src": preview_src if "preview_src" in locals() else "",
                "file_name": file_name if "file_name" in locals() else f"Error-{idx+1}",
                "file_bytes": file_bytes,
                "raw_response": None,
            }

        # Procesar la respuesta
        if "error" in ocr_response:
            result_text = f"Error al procesar {file_name}: {ocr_response['error']}"
            success = False
        else:
            pages = ocr_response.get("pages", [])
            if pages:
                result_text = "\n\n".join(
                    page.get("markdown", "") for page in pages if "markdown" in page
                )
                if result_text.strip():
                    success = True
                else:
                    result_text = f"No se encontró texto en {file_name}."
                    success = False
            else:
                result_text = f"Estructura de respuesta inesperada para {file_name}."
                success = False

        logger.info(
            f"Documento {idx+1}/{total} procesado: {'Éxito' if success else 'Fallido'}"
        )
        return {
            "success": success,
            "result_text": result_text,
            "preview_src": preview_src,
            "file_name": file_name,
            "file_bytes": file_bytes,
            "raw_response": (
                ocr_response.get("raw_response")
                if "raw_response" in ocr_response
                else None
            ),
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error inesperado procesando documento {idx+1}/{total}: {error_msg}\n{traceback.format_exc()}"
        )
        return {
            "success": False,
            "result_text": f"Error inesperado: {error_msg}",
            "preview_src": preview_src if "preview_src" in locals() else "",
            "file_name": (
                file_name
                if "file_name" in locals()
                else (
                    getattr(source, "name", f"Doc-{idx+1}")
                    if not isinstance(source, str)
                    else f"URL-{idx+1}"
                )
            ),
            "file_bytes": file_bytes,
            "raw_response": None,
        }


# ====================== INTERFAZ DE USUARIO ======================

# Título principal en el área de contenido
st.title("🔍 Aplicación Mistral OCR")

# Obtener la API key
api_key = get_mistral_api_key()

# ====================== BARRA LATERAL (CONFIGURACIÓN) ======================
with st.sidebar:
    st.image("assets/logo.png", width=150)
    st.header("Configuración")

    # UI para la API key - solo se muestra si no está en secrets o variables de entorno
    if not api_key:
        api_key_input = st.text_input(
            "API key de Mistral",
            value="",
            type="password",
            help="Tu API key de Mistral. Se utilizará para procesar los documentos.",
        )

        if not api_key_input:
            st.info("Por favor, introduce tu API key de Mistral para continuar.")

            # Instrucciones para obtener API key
            with st.expander("🔑 ¿Cómo obtener una API key?"):
                st.markdown(
                    """
                1. Visita [mistral.ai](https://mistral.ai) y crea una cuenta
                2. Navega a la sección de API Keys
                3. Genera una nueva API key
                4. Copia y pégala aquí

                También puedes configurar tu API key como:
                - Variable de entorno: `MISTRAL_API_KEY`
                - Secreto de Streamlit: `.streamlit/secrets.toml`
                """
                )
        else:
            # Verificar la API key ingresada
            valid, message = validate_api_key(api_key_input)
            if valid:
                st.success(f"✅ {message}")
                api_key = api_key_input
            else:
                st.warning(f"⚠️ {message}")
    else:
        # Verificar silenciosamente la API key existente
        valid, message = validate_api_key(api_key)
        if valid:
            st.success("✅ API key configurada correctamente")
        else:
            st.error(f"❌ La API key configurada no es válida: {message}")

    # Método de carga
    st.subheader("Método de carga")
    source_type = st.radio(
        "Selecciona el método de carga",
        options=["Archivo local", "URL"],
        help="Selecciona URL para procesar archivos desde internet o Archivo local para subir desde tu dispositivo.",
    )

    # Opciones avanzadas
    st.header("⚙️ Opciones avanzadas")

    # Sección principal de configuración
    st.subheader("Procesamiento")
    processing_method = st.radio(
        "Método de procesamiento",
        options=[
            "Auto (intentar ambos)",
            "OCR API (Standard)",
            "Document Understanding API",
        ],
        help="Selecciona el método para procesar los documentos",
    )

    # Opciones generales
    show_technical_details = st.checkbox(
        "Mostrar detalles técnicos",
        help="Muestra información técnica detallada durante el procesamiento",
    )
    # Actualizar el estado de sesión
    st.session_state["show_technical_details"] = show_technical_details

    optimize_images = st.checkbox(
        "Optimizar imágenes",
        value=True,
        help="Optimiza las imágenes antes de enviarlas para OCR (recomendado)",
    )

    # Opciones específicas para imágenes
    direct_api_for_images = st.checkbox(
        "Usar API REST directa para imágenes",
        value=True,
        help="Usa la API REST directamente para procesar imágenes (más confiable)",
    )

    # Herramientas de diagnóstico
    st.subheader("🔧 Diagnóstico")
    if st.button("Verificar instalación de cURL"):
        try:
            result = subprocess.run(
                ["curl", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                st.success(
                    f"cURL instalado correctamente: {result.stdout.splitlines()[0]}"
                )
            else:
                st.error(f"Error al verificar cURL: {result.stderr}")
        except Exception as e:
            st.error(f"Error al ejecutar cURL: {str(e)}")

    # Información de la aplicación
    with st.expander("ℹ️ Acerca de Mistral OCR"):
        st.markdown(
            """
        ### Características:
        - Extracción de texto con preservación de estructura
        - Soporte para PDF e imágenes
        - Múltiples métodos de procesamiento
        - Optimización de imágenes

        ### Limitaciones:
        - PDFs hasta 50 MB
        - Máximo 1,000 páginas por documento
        """
        )

    # Versión de la app
    st.caption(f"Mistral OCR App v{APP_VERSION}")

# ====================== ÁREA PRINCIPAL ======================

# Verificar si tenemos API key válida para continuar
if not api_key:
    st.warning("⚠️ Se requiere una API key válida para utilizar la aplicación.")

    # Mostrar información sobre la aplicación mientras no hay API key
    st.info(
        "Esta aplicación permite extraer texto de documentos PDF e imágenes usando tecnología OCR avanzada."
    )

    with st.expander("🔍 ¿Qué puedes hacer con Mistral OCR?"):
        st.markdown(
            """
        - **Digitalizar documentos** escaneados o fotografiados
        - **Extraer texto** de facturas, recibos, contratos, etc.
        - **Preservar el formato** del documento original
        - **Procesar documentos** en lote
        - **Descargar resultados** en diferentes formatos
        """
        )

    # Detener la ejecución hasta que tengamos una API key
    st.stop()

# Interfaz para cargar documentos
st.header("1️⃣ Cargar documentos")

input_url = ""
uploaded_files = []

if source_type == "URL":
    input_url = st.text_area(
        "Introduce URLs (una por línea)",
        help="Introduce las URLs de los documentos a procesar",
    )
else:
    acceptable_types = ["pdf", "jpg", "jpeg", "png"]
    uploaded_files = st.file_uploader(
        "Sube archivos",
        type=acceptable_types,
        accept_multiple_files=True,
        help=f"Formatos aceptados: {', '.join(acceptable_types)} (el tipo de archivo se detectará automáticamente)",
    )

# Botón de procesamiento
st.header("2️⃣ Procesar")

process_button = st.button(
    "📄 Procesar documentos",
    help="Inicia el procesamiento OCR",
    use_container_width=True,
    disabled=not api_key
    or (source_type == "URL" and not input_url.strip())
    or (source_type == "Archivo local" and not uploaded_files),
)

# ====================== LÓGICA DE PROCESAMIENTO ======================

if process_button:
    # Preparar fuentes
    try:
        sources = input_url.split("\n") if source_type == "URL" else uploaded_files
        sources = [
            s
            for s in sources
            if s and (isinstance(s, str) and s.strip() or not isinstance(s, str))
        ]

        if not sources:
            st.error("No se encontraron fuentes válidas para procesar.")
            st.stop()

        # Reiniciar estados
        st.session_state["ocr_result"] = []
        st.session_state["preview_src"] = []
        st.session_state["image_bytes"] = []
        st.session_state["file_names"] = []
        st.session_state["processing_complete"] = False

        total_files = len(sources)
        st.info(f"Procesando {total_files} documento(s)...")

        # Configurar barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Procesar documentos de forma secuencial con mejor información de progreso
        results = []

        for idx, source in enumerate(sources):
            # Actualizar progreso
            progress_value = idx / total_files
            progress_bar.progress(
                progress_value, text=f"Procesando {idx+1}/{total_files}"
            )

            # Nombre de fuente para mostrar
            source_name = source if isinstance(source, str) else source.name
            status_text.text(
                f"Procesando {'URL' if source_type == 'URL' else 'archivo'}: {source_name}"
            )

            # Procesar documento
            result = process_document(
                api_key,
                source,
                idx,
                total_files,
                source_type,
                processing_method,
                show_technical_details,
                optimize_images,
                direct_api_for_images,
            )

            results.append(result)

            # Actualizar listas de resultados
            st.session_state["ocr_result"].append(result["result_text"])
            st.session_state["preview_src"].append(result["preview_src"])
            st.session_state["file_names"].append(result["file_name"])
            if result["file_bytes"] is not None:
                st.session_state["image_bytes"].append(result["file_bytes"])

        # Marcar procesamiento como completado
        st.session_state["processing_complete"] = True

        # Actualizar progreso final
        progress_bar.progress(1.0, text="¡Procesamiento completado!")

        # Mostrar resumen
        success_count = sum(1 for r in results if r["success"])
        if success_count == total_files:
            st.success(
                f"✅ ¡Procesamiento completado con éxito! Se procesaron {total_files} documento(s)."
            )
        else:
            st.warning(
                f"⚠️ Procesamiento completado con {total_files - success_count} error(es). Se procesaron {success_count} de {total_files} documento(s) correctamente."
            )

    except Exception as e:
        st.error(f"Error al preparar documentos para procesamiento: {str(e)}")
        if st.session_state["show_technical_details"]:
            with st.expander("Detalles técnicos del error"):
                st.code(traceback.format_exc())

# ====================== VISUALIZACIÓN DE RESULTADOS ======================

# Mostrar resultados si están disponibles
if st.session_state.get("processing_complete") and st.session_state.get("ocr_result"):
    st.header("3️⃣ Resultados")

    try:
        if len(st.session_state["file_names"]) > 0:
            # Usar tabs para múltiples documentos
            if len(st.session_state["file_names"]) > 1:
                tabs = st.tabs(
                    [
                        f"Doc {idx+1}: {name}"
                        for idx, name in enumerate(st.session_state["file_names"])
                    ]
                )
            else:
                # Para un solo documento, crear un contenedor sin tabs
                tabs = [st.container()]

            for idx, tab in enumerate(tabs):
                with tab:
                    # Dividir el espacio para previsualización y texto
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.subheader("Vista previa del documento")

                        if (
                            idx < len(st.session_state["preview_src"])
                            and st.session_state["preview_src"][idx]
                        ):
                            file_name = st.session_state["file_names"][idx]

                            if "pdf" in file_name.lower():
                                # Solución para PDFs en Streamlit Cloud
                                pdf_display_html = f"""
                                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 20px; text-align: center;">
                                    <p style="margin-bottom: 15px;">Vista previa directa no disponible</p>
                                    <a href="{st.session_state["preview_src"][idx]}"
                                       target="_blank"
                                       style="display: inline-block; padding: 10px 20px;
                                              background-color: #1976D2; color: white;
                                              text-decoration: none; border-radius: 4px;
                                              font-weight: 500;">
                                        Abrir PDF en nueva pestaña
                                    </a>
                                </div>
                                """
                                st.markdown(pdf_display_html, unsafe_allow_html=True)
                            else:
                                # Para imágenes
                                try:
                                    if source_type == "Archivo local" and idx < len(
                                        st.session_state.get("image_bytes", [])
                                    ):
                                        st.image(
                                            st.session_state["image_bytes"][idx],
                                            caption=f"Imagen original: {file_name}",
                                            use_container_width=True,
                                        )
                                    elif st.session_state["preview_src"][idx]:
                                        st.image(
                                            st.session_state["preview_src"][idx],
                                            caption=f"Imagen original: {file_name}",
                                            use_container_width=True,
                                        )
                                    else:
                                        st.info(
                                            "Vista previa no disponible para este documento."
                                        )
                                except Exception as e:
                                    st.error(f"Error al mostrar imagen: {str(e)}")
                                    st.info(
                                        "Vista previa no disponible debido a un error."
                                    )
                        else:
                            st.info("Vista previa no disponible para este documento.")

                    with col2:
                        st.subheader(f"Texto extraído")

                        if idx < len(st.session_state["ocr_result"]):
                            result_text = st.session_state["ocr_result"][idx]

                            if not result_text.startswith("Error:"):
                                # Añadir contador de caracteres
                                char_count = len(result_text)
                                word_count = len(result_text.split())
                                st.caption(
                                    f"{word_count} palabras | {char_count} caracteres"
                                )

                            # Texto área con resultado
                            st.text_area(
                                label="",
                                value=result_text,
                                height=400,
                                key=f"text_area_{idx}",
                            )

                            # Opciones de descarga para resultados exitosos
                            if not result_text.startswith("Error"):
                                st.subheader("Descargar resultados")

                                try:
                                    # Nombre base para archivos de descarga
                                    base_filename = st.session_state["file_names"][
                                        idx
                                    ].split(".")[0]

                                    # Opciones de descarga con mejor UI
                                    download_col1, download_col2, download_col3 = (
                                        st.columns(3)
                                    )

                                    with download_col1:
                                        json_data = json.dumps(
                                            {"ocr_result": result_text},
                                            ensure_ascii=False,
                                            indent=2,
                                        )
                                        st.markdown(
                                            create_download_link(
                                                json_data,
                                                "application/json",
                                                f"{base_filename}.json",
                                            ),
                                            unsafe_allow_html=True,
                                        )

                                    with download_col2:
                                        st.markdown(
                                            create_download_link(
                                                result_text,
                                                "text/plain",
                                                f"{base_filename}.txt",
                                            ),
                                            unsafe_allow_html=True,
                                        )

                                    with download_col3:
                                        st.markdown(
                                            create_download_link(
                                                result_text,
                                                "text/markdown",
                                                f"{base_filename}.md",
                                            ),
                                            unsafe_allow_html=True,
                                        )
                                except Exception as e:
                                    st.error(
                                        f"Error al crear enlaces de descarga: {str(e)}"
                                    )
                        else:
                            st.error(
                                "No hay resultados disponibles para este documento."
                            )

    except Exception as e:
        st.error(f"Error al mostrar resultados: {str(e)}")
        if st.session_state["show_technical_details"]:
            with st.expander("Detalles técnicos del error"):
                st.code(traceback.format_exc())

# ====================== PANTALLA INICIAL ======================
# Si no hay procesamiento completado, mostrar información de bienvenida
if not st.session_state.get("processing_complete"):
    # Información sobre la aplicación
    with st.expander("🔍 Información sobre esta aplicación"):
        st.markdown(
            """
        Esta aplicación permite extraer información de documentos PDF e imágenes utilizando Mistral OCR.

        ### Características:
        - Procesa documentos PDF e imágenes
        - Soporta carga desde URL o archivos locales
        - Extrae texto manteniendo el formato del documento
        - Descarga los resultados en múltiples formatos
        - Implementa métodos de respaldo para máxima confiabilidad

        ### Cómo usar:
        1. Proporciona tu API key de Mistral (si no está configurada)
        2. Elige el método de carga (URL o archivo local) en el menú lateral
        3. Sube tus documentos (PDF, JPG, PNG) o proporciona URLs
        4. Haz clic en "Procesar"
        5. Visualiza y descarga los resultados
        """
        )

    # Crear columnas para organizar el contenido
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            """
        ## Bienvenido a Mistral OCR

        Esta aplicación te permite extraer texto de documentos PDF e imágenes utilizando
        la tecnología OCR avanzada de Mistral AI.

        ### Características principales:
        - Extracción de texto con preservación de formato
        - Soporte para documentos escaneados
        - Procesamiento de imágenes optimizado
        - Múltiples formatos de descarga
        """
        )

    with col2:
        # Imagen ilustrativa
        try:
            st.image(
                "https://images.unsplash.com/photo-1568667256549-094345857637?w=500",
                caption="OCR y extracción de texto",
                use_container_width=True,
            )
        except Exception:
            # Si no se puede cargar la imagen, mostrar un mensaje alternativo
            st.info("Mistral OCR - Digitaliza tus documentos")

# Información adicional
st.markdown("---")
with st.expander("🛠️ Solución de problemas"):
    st.markdown(
        """
    Si encuentras problemas al usar esta aplicación, intenta lo siguiente:

    1. **Error al procesar imágenes**:
       - Asegúrate de que la imagen tenga buen contraste y resolución
       - Activa la opción "Optimizar imágenes" en las opciones avanzadas
       - Usa "API REST directa para imágenes" en las opciones avanzadas

    2. **Error 404 (Not Found)**:
       - Verifica que tengas acceso a la API de OCR en tu plan de Mistral
       - Prueba con el método alternativo "Document Understanding API"

    3. **Error de API key**:
       - Verifica que tu API key de Mistral sea válida y esté correctamente introducida
       - Asegúrate de que la API key tenga permisos suficientes

    4. **Error de formato**:
       - Asegúrate de que tus archivos sean compatibles (PDF, JPG, PNG)
       - Verifica que los archivos no estén corruptos

    5. **Error de tamaño**:
       - Los archivos no deben exceder 50 MB
       - Intenta dividir documentos grandes

    Para más información, consulta la [documentación oficial de Mistral AI](https://docs.mistral.ai).
    """
    )

# Versión y créditos
st.markdown("---")
st.markdown(
    f"""
<div style="text-align: center; color: #666;">
    <p>Mistral OCR App v{APP_VERSION} | Desarrollada con Streamlit, Mistral AI API y procesamiento avanzado de imágenes</p>
</div>
""",
    unsafe_allow_html=True,
)
