import streamlit as st
import os
import base64
import json
import time
import subprocess
import tempfile
import requests
from pathlib import Path

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
    1. Proporciona tu API key de Mistral
    2. Selecciona el tipo de archivo (PDF o imagen)
    3. Elige el método de carga (URL o archivo local)
    4. Sube tus documentos o proporciona URLs
    5. Haz clic en "Procesar"
    6. Visualiza y descarga los resultados
    """
    )


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


# Función para realizar solicitud OCR usando cURL
def process_ocr_with_curl(api_key, document, method="REST"):
    # Crear un directorio temporal para los archivos
    temp_dir = tempfile.mkdtemp()

    try:
        # Preparar el documento según su tipo
        if document.get("type") == "document_url":
            url = document["document_url"]
            if url.startswith("data:application/pdf;base64,"):
                # Guardar el PDF base64 en un archivo temporal
                pdf_base64 = url.replace("data:application/pdf;base64,", "")
                temp_pdf_path = os.path.join(temp_dir, "temp_document.pdf")
                with open(temp_pdf_path, "wb") as f:
                    f.write(base64.b64decode(pdf_base64))

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
                st.text("Subiendo archivo al servidor de Mistral...")
                result = subprocess.run(upload_command, capture_output=True, text=True)

                if result.returncode != 0:
                    return {"error": f"Error al subir archivo: {result.stderr}"}

                # Parsear el resultado para obtener el ID del archivo
                try:
                    file_data = json.loads(result.stdout)
                    file_id = file_data.get("id")
                    if not file_id:
                        return {"error": "No se pudo obtener el ID del archivo subido"}

                    st.text(f"Archivo subido correctamente. ID: {file_id}")

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
                        return {
                            "error": f"Error al obtener URL firmada: {url_result.stderr}"
                        }

                    url_data = json.loads(url_result.stdout)
                    signed_url = url_data.get("url")
                    if not signed_url:
                        return {"error": "No se pudo obtener la URL firmada"}

                    # Usar la URL firmada para el OCR
                    document = {"type": "document_url", "document_url": signed_url}

                except json.JSONDecodeError:
                    return {
                        "error": f"Error al parsear respuesta del servidor: {result.stdout}"
                    }

            # En este punto, document tiene una URL válida para procesar

        elif document.get("type") == "image_url":
            # Para imágenes, similar proceso pero con tipo image_url
            url = document["image_url"]
            if url.startswith("data:"):
                # Es una imagen en base64, la guardamos
                mime_type = url.split(";")[0].split(":")[1]
                extension = mime_type.split("/")[1]
                base64_data = (
                    url.split(",")[1] if "," in url else url.split(";base64,")[1]
                )

                temp_img_path = os.path.join(temp_dir, f"temp_image.{extension}")
                with open(temp_img_path, "wb") as f:
                    f.write(base64.b64decode(base64_data))

                # Crear un JSON para la solicitud
                json_data = {
                    "model": "mistral-ocr-latest",
                    "document": {
                        "type": "image_url",
                        "image_url": f"file://{temp_img_path}",
                    },
                    "include_image_base64": True,
                }

                # Crea un archivo temporal con el JSON
                temp_json_path = os.path.join(temp_dir, "request.json")
                with open(temp_json_path, "w") as f:
                    json.dump(json_data, f)

                # Comando cURL
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

                # Ejecutar y capturar
                st.text("Ejecutando OCR para imagen...")
                ocr_result = subprocess.run(ocr_command, capture_output=True, text=True)

                if ocr_result.returncode != 0:
                    return {"error": f"Error en OCR: {ocr_result.stderr}"}

                try:
                    return json.loads(ocr_result.stdout)
                except json.JSONDecodeError:
                    return {
                        "error": f"Error al parsear respuesta OCR: {ocr_result.stdout}"
                    }

        # Preparar datos para la solicitud OCR
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
        st.text("Ejecutando OCR con cURL...")
        st.code(" ".join(ocr_command).replace(api_key, "****"), language="bash")

        ocr_result = subprocess.run(ocr_command, capture_output=True, text=True)

        if ocr_result.returncode != 0:
            error_details = {
                "error": f"Error en OCR (código {ocr_result.returncode})",
                "stderr": ocr_result.stderr,
                "stdout": ocr_result.stdout,
            }
            st.error(f"Error durante la ejecución de cURL: {error_details['error']}")
            return {"error": json.dumps(error_details)}

        # Comprobar si hay errores en la respuesta
        if (
            "error" in ocr_result.stdout.lower()
            or "not found" in ocr_result.stdout.lower()
        ):
            st.warning("La API respondió, pero con un error")
            st.code(ocr_result.stdout, language="json")

            # Intentar método alternativo
            if "document understanding" not in method.lower():
                st.info("Intentando procesar con el método Document Understanding...")
                return process_with_document_understanding(api_key, document)

        try:
            return json.loads(ocr_result.stdout)
        except json.JSONDecodeError:
            if not ocr_result.stdout:
                return {"error": "Respuesta vacía del servidor"}
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

    if not doc_url:
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

    # Guardar la solicitud en un archivo temporal para inspección
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(request_data, tmp, indent=2)
        temp_json_path = tmp.name

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

    st.text("Ejecutando Document Understanding con cURL...")
    du_result = subprocess.run(du_command, capture_output=True, text=True)

    # Limpiar archivo temporal
    try:
        os.unlink(temp_json_path)
    except:
        pass

    if du_result.returncode != 0:
        return {"error": f"Error en Document Understanding: {du_result.stderr}"}

    try:
        result_json = json.loads(du_result.stdout)
        if "choices" in result_json and len(result_json["choices"]) > 0:
            content = result_json["choices"][0]["message"]["content"]

            # Simular el formato de respuesta de OCR
            pages = [{"markdown": content}]
            return {"pages": pages}
        else:
            return {
                "error": f"Respuesta no válida de Document Understanding: {du_result.stdout[:200]}..."
            }
    except json.JSONDecodeError:
        return {"error": f"Error al parsear respuesta: {du_result.stdout[:200]}..."}


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
        st.warning(
            f"⚠️ {message} - Algunos métodos de procesamiento podrían no funcionar correctamente."
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

# Crear columnas para los controles
col1, col2 = st.columns(2)

# Columna 1: Tipo de archivo y fuente
with col1:
    st.markdown("### Tipo de contenido")
    file_type = st.radio(
        "Selecciona el tipo de archivo",
        options=["PDF", "Imagen"],
        help="Selecciona PDF para documentos o Imagen para archivos JPG, PNG, etc.",
    )

    st.markdown("### Método de carga")
    source_type = st.radio(
        "Selecciona el método de carga",
        options=["URL", "Archivo local"],
        help="Selecciona URL para procesar archivos desde internet o Archivo local para subir desde tu dispositivo.",
    )

# Columna 2: URLs o carga de archivos
with col2:
    st.markdown("### Fuente de datos")
    input_url = ""
    uploaded_files = []

    if source_type == "URL":
        input_url = st.text_area(
            "Introduce una o varias URLs (una por línea)",
            help="Introduce las URLs de los documentos que quieres procesar, cada una en una línea nueva.",
        )
    else:
        acceptable_types = ["pdf"] if file_type == "PDF" else ["jpg", "jpeg", "png"]
        uploaded_files = st.file_uploader(
            "Sube uno o más archivos",
            type=acceptable_types,
            accept_multiple_files=True,
            help=f"Sube archivos {', '.join(acceptable_types)} desde tu dispositivo.",
        )

# Botón de procesamiento con estilo
st.markdown("### Procesamiento")

# Opciones avanzadas
with st.expander("⚙️ Opciones avanzadas"):
    st.markdown("#### Configuración de procesamiento")

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

    # Opciones de depuración cURL
    if show_technical_details:
        st.markdown("#### Opciones de cURL")
        curl_verbose = st.checkbox(
            "Modo verboso de cURL",
            help="Muestra información detallada de las peticiones cURL",
        )

        timeout = st.slider(
            "Tiempo de espera (segundos)",
            min_value=30,
            max_value=300,
            value=120,
            step=30,
            help="Tiempo máximo de espera para las peticiones",
        )

# Información sobre la API
st.info(
    """
**Nota importante sobre la API de Mistral OCR**: 
El servicio OCR de Mistral podría requerir un plan específico o estar en fase beta con acceso limitado.
Si experimentas errores, verifica tu cuenta en mistral.ai o contacta con soporte.
"""
)

process_button = st.button(
    "📄 Procesar documentos",
    help="Haz clic para comenzar el procesamiento de OCR en los documentos seleccionados.",
    use_container_width=True,
)

# Lógica de procesamiento
if process_button:
    if source_type == "URL" and not input_url.strip():
        st.error("Por favor, introduce al menos una URL válida.")
    elif source_type == "Archivo local" and not uploaded_files:
        st.error("Por favor, sube al menos un archivo.")
    else:
        with st.spinner("Preparando para procesar..."):
            # Reiniciar los resultados
            st.session_state["ocr_result"] = []
            st.session_state["preview_src"] = []
            st.session_state["image_bytes"] = []
            st.session_state["file_names"] = []

            # Preparar las fuentes
            sources = input_url.split("\n") if source_type == "URL" else uploaded_files
            sources = [
                s
                for s in sources
                if s and (isinstance(s, str) and s.strip() or not isinstance(s, str))
            ]

            if not sources:
                st.error("No se encontraron fuentes válidas para procesar.")
                st.stop()

            st.info(f"Procesando {len(sources)} documento(s)...")

            # Crear una barra de progreso
            progress_bar = st.progress(0)

            # Procesar cada fuente
            for idx, source in enumerate(sources):
                progress_text = f"Procesando {'URL' if source_type == 'URL' else 'archivo'} {idx+1}/{len(sources)}"
                progress_value = (idx) / len(sources)
                progress_bar.progress(progress_value, text=progress_text)

                with st.spinner(progress_text):
                    try:
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
                                file_bytes = source.read()
                                encoded_pdf = base64.b64encode(file_bytes).decode(
                                    "utf-8"
                                )
                                document = {
                                    "type": "document_url",
                                    "document_url": f"data:application/pdf;base64,{encoded_pdf}",
                                }
                                preview_src = (
                                    f"data:application/pdf;base64,{encoded_pdf}"
                                )
                                file_name = source.name
                                # Reiniciar el cursor del archivo para futuras operaciones
                                source.seek(0)
                        else:  # Imagen
                            if source_type == "URL":
                                document = {
                                    "type": "image_url",
                                    "image_url": source.strip(),
                                }
                                preview_src = source.strip()
                                file_name = source.split("/")[-1]
                            else:
                                file_bytes = source.read()
                                mime_type = source.type
                                encoded_image = base64.b64encode(file_bytes).decode(
                                    "utf-8"
                                )
                                document = {
                                    "type": "image_url",
                                    "image_url": f"data:{mime_type};base64,{encoded_image}",
                                }
                                preview_src = f"data:{mime_type};base64,{encoded_image}"
                                st.session_state["image_bytes"].append(file_bytes)
                                file_name = source.name
                                # Reiniciar el cursor del archivo para futuras operaciones
                                source.seek(0)

                        # Llamar a la API de OCR con método seleccionado
                        st.text(f"Enviando documento {file_name} para procesamiento...")

                        # Determinar el método a usar basado en la selección
                        if processing_method == "OCR API (Standard)":
                            ocr_response = process_ocr_with_curl(
                                api_key_input, document, method="OCR"
                            )
                        elif processing_method == "Document Understanding API":
                            ocr_response = process_with_document_understanding(
                                api_key_input, document
                            )
                        else:  # Auto
                            ocr_response = process_ocr_with_curl(
                                api_key_input, document, method="Auto"
                            )

                        # Procesar la respuesta
                        if "error" in ocr_response:
                            result_text = f"Error al procesar {file_name}: {ocr_response['error']}"
                            st.error(result_text)

                            # Mostrar detalles técnicos si está habilitado
                            if show_technical_details and isinstance(
                                ocr_response["error"], str
                            ):
                                try:
                                    error_details = json.loads(ocr_response["error"])
                                    st.markdown("**Detalles técnicos del error:**")
                                    st.code(
                                        json.dumps(error_details, indent=2),
                                        language="json",
                                    )
                                except:
                                    st.text(ocr_response["error"])
                        else:
                            pages = ocr_response.get("pages", [])
                            if pages:
                                result_text = "\n\n".join(
                                    page.get("markdown", "")
                                    for page in pages
                                    if "markdown" in page
                                )
                                if result_text.strip():
                                    st.success(
                                        f"Documento {file_name} procesado correctamente."
                                    )
                                else:
                                    result_text = (
                                        f"No se encontró texto en {file_name}."
                                    )
                                    st.warning(result_text)
                            else:
                                result_text = f"Estructura de respuesta inesperada para {file_name}."
                                st.warning(result_text)

                                # Mostrar la respuesta completa si está habilitado
                                if show_technical_details:
                                    st.markdown("**Estructura de respuesta:**")
                                    st.code(
                                        json.dumps(ocr_response, indent=2),
                                        language="json",
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
                        st.error(
                            f"Error al procesar {'URL' if source_type == 'URL' else 'archivo'} {idx+1}: {error_msg}"
                        )

                        # Mostrar detalles técnicos si está habilitado
                        if show_technical_details:
                            import traceback

                            st.markdown("**Detalles técnicos del error:**")
                            st.code(traceback.format_exc(), language="python")

                        # Añadir un resultado vacío para mantener la sincronización
                        st.session_state["ocr_result"].append(f"Error: {error_msg}")
                        if source_type == "URL":
                            st.session_state["preview_src"].append("")
                            st.session_state["file_names"].append(f"URL-{idx+1}")
                        else:
                            st.session_state["preview_src"].append("")
                            file_name = getattr(source, "name", f"Archivo-{idx+1}")
                            st.session_state["file_names"].append(file_name)
                        continue

            # Actualizar la barra de progreso a completado
            progress_bar.progress(1.0, text="¡Procesamiento completado!")
            st.success(
                f"¡Procesamiento completado! Se procesaron {len(st.session_state['ocr_result'])} documento(s)."
            )

# Mostrar resultados si están disponibles
if st.session_state.get("ocr_result"):
    st.markdown("## Resultados del OCR")

    # Crear tabs solo para los documentos que tienen nombres
    if len(st.session_state["file_names"]) > 0:
        tabs = st.tabs(
            [
                f"Documento {idx+1}: {st.session_state['file_names'][idx]}"
                for idx in range(len(st.session_state["file_names"]))
            ]
        )

        for idx, tab in enumerate(tabs):
            with tab:
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader(f"Vista previa del documento")
                    if (
                        idx < len(st.session_state["preview_src"])
                        and st.session_state["preview_src"][idx]
                    ):
                        if "pdf" in st.session_state["file_names"][idx].lower():
                            pdf_embed_html = f'<iframe src="{st.session_state["preview_src"][idx]}" width="100%" height="600" frameborder="0"></iframe>'
                            st.markdown(pdf_embed_html, unsafe_allow_html=True)
                        else:
                            if source_type == "Archivo local" and idx < len(
                                st.session_state.get("image_bytes", [])
                            ):
                                st.image(
                                    st.session_state["image_bytes"][idx],
                                    caption=f"Imagen original: {st.session_state['file_names'][idx]}",
                                )
                            elif st.session_state["preview_src"][idx]:
                                st.image(
                                    st.session_state["preview_src"][idx],
                                    caption=f"Imagen original: {st.session_state['file_names'][idx]}",
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
                    st.subheader(f"Texto extraído")
                    if idx < len(st.session_state["ocr_result"]):
                        st.text_area(
                            "Resultado OCR",
                            value=st.session_state["ocr_result"][idx],
                            height=450,
                            key=f"text_area_{idx}",
                        )

                        if not st.session_state["ocr_result"][idx].startswith("Error:"):
                            st.subheader(f"Descargar resultados")

                            def create_download_link(data, filetype, filename):
                                b64 = base64.b64encode(data.encode()).decode()
                                href = f'<a href="data:{filetype};base64,{b64}" download="{filename}" class="download-button">Descargar {filename}</a>'
                                return href

                            # Crear nombre de archivo base
                            base_filename = st.session_state["file_names"][idx].split(
                                "."
                            )[0]

                            # Opciones de descarga
                            download_col1, download_col2, download_col3 = st.columns(3)

                            with download_col1:
                                json_data = json.dumps(
                                    {"ocr_result": st.session_state["ocr_result"][idx]},
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
                                        st.session_state["ocr_result"][idx],
                                        "text/plain",
                                        f"{base_filename}.txt",
                                    ),
                                    unsafe_allow_html=True,
                                )

                            with download_col3:
                                st.markdown(
                                    create_download_link(
                                        st.session_state["ocr_result"][idx],
                                        "text/markdown",
                                        f"{base_filename}.md",
                                    ),
                                    unsafe_allow_html=True,
                                )
                    else:
                        st.error("No hay resultados disponibles para este documento.")

# Información adicional
st.markdown("---")
with st.expander("ℹ️ Acerca de Mistral OCR"):
    st.markdown(
        """
    ### Características de Mistral OCR:
    
    - Extrae texto manteniendo la estructura y jerarquía del documento
    - Preserva el formato como encabezados, párrafos, listas y tablas
    - Devuelve resultados en formato markdown para facilitar el análisis y la representación
    - Maneja diseños complejos incluyendo texto en múltiples columnas y contenido mixto
    - Procesa documentos a escala con alta precisión
    - Soporta múltiples formatos de documento incluyendo PDF, imágenes y documentos cargados
    
    ### Limitaciones:
    - Los archivos PDF subidos no deben exceder los 50 MB de tamaño
    - Los documentos no deben superar las 1,000 páginas
    """
    )

with st.expander("🔧 Solución de problemas"):
    st.markdown(
        """
    Si encuentras problemas al usar esta aplicación, intenta lo siguiente:
    
    1. **Error 404 (Not Found)**: 
       - Verifica que tengas acceso a la API de OCR en tu plan de Mistral
       - Prueba con el método alternativo "Document Understanding API"
       
    2. **Error de API key**: 
       - Verifica que tu API key de Mistral sea válida y esté correctamente introducida
       - Asegúrate de que la API key tenga permisos suficientes
       
    3. **Error de conexión**: 
       - Asegúrate de tener una conexión a Internet estable
       - Verifica que no haya restricciones de firewall
       
    4. **Error de formato**: 
       - Asegúrate de que tus archivos sean compatibles (PDF, JPG, PNG)
       - Verifica que los archivos no estén corruptos
       
    5. **Error de tamaño**: 
       - Los archivos no deben exceder 50 MB
       - Intenta dividir documentos grandes
       
    6. **Límites de API**: 
       - Si recibes errores de límite excedido, espera unos minutos e intenta nuevamente
    
    Para más información, consulta la [documentación oficial de Mistral AI](https://docs.mistral.ai).
    """
    )

with st.expander("🛠️ Método curl vs REST API"):
    st.markdown(
        """
    ### Comparación de métodos de procesamiento:
    
    Esta aplicación implementa dos métodos principales para procesar documentos:
    
    #### 1. OCR API (mediante cURL)
    - Llamada directa al endpoint de OCR de Mistral
    - Permite más control sobre los parámetros
    - Mejor manejo de archivos grandes
    - Proporciona información detallada de errores
    
    #### 2. Document Understanding API
    - Utiliza el modelo de chat para extraer texto
    - Puede funcionar incluso si el OCR directo no está disponible en tu plan
    - Más lento pero potencialmente más flexible
    - Útil como método de respaldo
    
    La opción "Auto" intenta primero el OCR directo y, si falla, recurre al Document Understanding.
    """
    )

# Versión y créditos
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <p>Mistral OCR App v2.0 | Desarrollada con Streamlit, Mistral AI API y cURL</p>
</div>
""",
    unsafe_allow_html=True,
)
