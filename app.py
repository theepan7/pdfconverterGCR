from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import uuid
import subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
from google.cloud import storage
from datetime import timedelta
from google.oauth2 import service_account
import traceback
import tempfile

# ---------------- Config & Auth ---------------- #
SERVICE_ACCOUNT_PATH = "/secrets/pdftoolkit-key"
if not os.path.exists(SERVICE_ACCOUNT_PATH):
    raise FileNotFoundError(f"Service account file not found at {SERVICE_ACCOUNT_PATH}")

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)

app = Flask(__name__, static_folder='static')
CORS(app)

# Max upload size = 32 MB (matches Cloud Run HTTP limit)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# GCS bucket name (env var or fallback)
GCS_BUCKET = os.environ.get("GCS_BUCKET", "pdftoolkituploads")

# Signed URL lifetime
SIGNED_URL_HOURS = int(os.environ.get("SIGNED_URL_HOURS", "1"))

# Initialize GCS client with service account credentials
storage_client = storage.Client(credentials=credentials)
bucket = storage_client.bucket(GCS_BUCKET)


# ---------------- Utility Functions ---------------- #
def upload_blob_from_fileobj(file_obj, destination_blob_name, content_type="application/pdf"):
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file_obj, rewind=True, content_type=content_type)
    return blob


def download_blob_to_tmp(blob_name, tmp_dir):
    local_path = os.path.join(tmp_dir, f"{uuid.uuid4()}_{os.path.basename(blob_name)}")
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    return local_path


def upload_file_to_gcs(local_path, destination_blob_name, content_type="application/pdf"):
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    return blob


def generate_signed_url(blob_name, expiration_hours=SIGNED_URL_HOURS):
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(hours=expiration_hours),
        method="GET",
    )
    return url


def json_error(message, code=500, extra=None):
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), code


# ---------------- Error Handlers ---------------- #
@app.errorhandler(413)
def request_entity_too_large(_error):
    return json_error("File too large. Max allowed size is 32 MB.", 413)


@app.errorhandler(404)
def not_found(_error):
    return json_error("Not Found", 404)


@app.errorhandler(500)
def internal_error(_error):
    return json_error("Internal Server Error", 500)


# ---------------- Routes for HTML Pages ---------------- #
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/compress-page")
def compress_page():
    return render_template("compress.html")


@app.route("/merge-page")
def merge_page():
    return render_template("merge.html")


@app.route("/split-page")
def split_page():
    return render_template("split.html")


@app.route("/image-page")
def image_page():
    return render_template("image.html")


# ---------------- PDF Operations ---------------- #
@app.route("/compress", methods=["POST"])
def compress():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    file_id = str(uuid.uuid4())
    gcs_input_path = f"uploads/{file_id}.pdf"
    gcs_output_path = f"processed/{file_id}_compressed.pdf"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Upload original to GCS
            upload_blob_from_fileobj(uploaded_file.stream, gcs_input_path)

            # Download to tmp
            input_tmp_path = download_blob_to_tmp(gcs_input_path, tmp_dir)
            output_tmp_path = os.path.join(tmp_dir, f"{file_id}_compressed.pdf")

            # Run Ghostscript
            gs_cmd = [
                "gs", "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={output_tmp_path}", input_tmp_path
            ]

            result = subprocess.run(gs_cmd, capture_output=True, text=True)
            if result.returncode != 0 or not os.path.exists(output_tmp_path):
                print("Ghostscript failed", {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })
                return json_error("Compression failed while running Ghostscript.", 500)

            upload_file_to_gcs(output_tmp_path, gcs_output_path)
            signed_url = generate_signed_url(gcs_output_path)
            return jsonify({"download_url": signed_url})

    except Exception as e:
        print("Compression exception:", str(e))
        print(traceback.format_exc())
        return json_error("Compression failed due to a server error.", 500, {"exception": str(e)})


@app.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("files")
    if not files:
        return json_error("No files uploaded.", 400)

    file_id = str(uuid.uuid4())
    gcs_output_path = f"processed/{file_id}_merged.pdf"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            merger = PdfMerger()
            valid_files_found = False

            for file in files:
                if file.filename.lower().endswith(".pdf"):
                    temp_blob_path = f"uploads/{uuid.uuid4()}.pdf"
                    upload_blob_from_fileobj(file.stream, temp_blob_path)
                    tmp_path = download_blob_to_tmp(temp_blob_path, tmp_dir)
                    merger.append(PdfReader(tmp_path))
                    valid_files_found = True

            if not valid_files_found:
                return json_error("No valid PDF files found.", 400)

            output_tmp_path = os.path.join(tmp_dir, f"{file_id}_merged.pdf")
            with open(output_tmp_path, "wb") as f_out:
                merger.write(f_out)
            merger.close()

            upload_file_to_gcs(output_tmp_path, gcs_output_path)
            signed_url = generate_signed_url(gcs_output_path)
            return jsonify({"download_url": signed_url})

    except Exception as e:
        print("Merging exception:", str(e))
        print(traceback.format_exc())
        return json_error("Merging failed due to a server error.", 500, {"exception": str(e)})


@app.route("/split", methods=["POST"])
def split():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    try:
        start = int(request.form.get("start", 1))
        end = int(request.form.get("end", 1))
    except Exception:
        return json_error("Invalid page range.", 400)

    file_id = str(uuid.uuid4())
    gcs_input_path = f"uploads/{file_id}.pdf"
    gcs_output_path = f"processed/{file_id}_split.pdf"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            upload_blob_from_fileobj(file.stream, gcs_input_path)
            input_tmp_path = download_blob_to_tmp(gcs_input_path, tmp_dir)
            reader = PdfReader(input_tmp_path)
            num_pages = len(reader.pages)

            if start < 1:
                start = 1
            if end > num_pages:
                end = num_pages
            if start > end:
                return json_error("Invalid range: start must be ≤ end.", 400)

            writer = PdfWriter()
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])

            output_tmp_path = os.path.join(tmp_dir, f"{file_id}_split.pdf")
            with open(output_tmp_path, "wb") as f_out:
                writer.write(f_out)

            upload_file_to_gcs(output_tmp_path, gcs_output_path)
            signed_url = generate_signed_url(gcs_output_path)
            return jsonify({"download_url": signed_url})

    except Exception as e:
        print("Splitting exception:", str(e))
        print(traceback.format_exc())
        return json_error("Splitting failed due to a server error.", 500, {"exception": str(e)})


@app.route("/image", methods=["POST"])
def image_to_pdf():
    files = request.files.getlist("file")
    images = []

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for file in files:
                name = file.filename.lower()
                if name.endswith((".png", ".jpg", ".jpeg")):
                    img = Image.open(file.stream).convert("RGB")
                    images.append(img)

            if not images:
                return json_error("No valid images uploaded.", 400)

            file_id = str(uuid.uuid4())
            gcs_output_path = f"processed/{file_id}_image2pdf.pdf"
            output_tmp_path = os.path.join(tmp_dir, f"{file_id}_image2pdf.pdf")

            images[0].save(output_tmp_path, format="PDF", save_all=True, append_images=images[1:])
            upload_file_to_gcs(output_tmp_path, gcs_output_path)
            signed_url = generate_signed_url(gcs_output_path)
            return jsonify({"download_url": signed_url})

    except Exception as e:
        print("Image->PDF exception:", str(e))
        print(traceback.format_exc())
        return json_error("Image to PDF failed due to a server error.", 500, {"exception": str(e)})

    finally:
        for im in images:
            try:
                im.close()
            except Exception:
                pass


# Optional: simple health check
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
