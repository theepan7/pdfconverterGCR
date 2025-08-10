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

# Path to mounted secret (Cloud Run mount location)
SERVICE_ACCOUNT_PATH = "/secrets/pdftoolkit-key"

if not os.path.exists(SERVICE_ACCOUNT_PATH):
    raise FileNotFoundError(f"Service account file not found at {SERVICE_ACCOUNT_PATH}")

# Load credentials from mounted secret
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Max upload size = 32 MB
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# GCS bucket name (from environment variable or fallback)
GCS_BUCKET = os.environ.get("GCS_BUCKET", "pdftoolkituploads")

# Initialize GCS client with service account credentials
storage_client = storage.Client(credentials=credentials)
bucket = storage_client.bucket(GCS_BUCKET)


# ---------------- Utility Functions ---------------- #
def upload_blob_from_fileobj(file_obj, destination_blob_name):
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(file_obj)
    return blob


def download_blob_to_tmp(blob_name):
    local_path = f"/tmp/{os.path.basename(blob_name)}"
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    return local_path


def upload_file_to_gcs(local_path, destination_blob_name):
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_path)
    return blob


def generate_signed_url(blob_name, expiration_hours=1):
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(expiration=timedelta(hours=expiration_hours))
    return url


# ---------------- Error Handlers ---------------- #
@app.errorhandler(413)
def request_entity_too_large(error):
    return "File too large. Max allowed size is 5MB.", 413


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
    if not uploaded_file or not uploaded_file.filename.endswith(".pdf"):
        return "Invalid file", 400

    file_id = str(uuid.uuid4())
    gcs_input_path = f"uploads/{file_id}.pdf"
    gcs_output_path = f"processed/{file_id}_compressed.pdf"

    try:
        # Upload original to GCS
        upload_blob_from_fileobj(uploaded_file.stream, gcs_input_path)

        # Download to temp
        input_tmp_path = download_blob_to_tmp(gcs_input_path)
        output_tmp_path = f"/tmp/{file_id}_compressed.pdf"

        # Compress PDF with Ghostscript
        subprocess.run([
            "gs", "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_tmp_path}", input_tmp_path
        ], check=True)

        # Upload compressed version
        upload_file_to_gcs(output_tmp_path, gcs_output_path)

        # Get signed URL
        signed_url = generate_signed_url(gcs_output_path)

        # Cleanup
        os.remove(input_tmp_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})

    except Exception as e:
        return f"Compression failed: {e}", 500


@app.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("files")
    if not files:
        return "No files uploaded", 400

    file_id = str(uuid.uuid4())
    gcs_output_path = f"processed/{file_id}_merged.pdf"
    merger = PdfMerger()

    try:
        for file in files:
            if file.filename.endswith(".pdf"):
                temp_blob_path = f"uploads/{uuid.uuid4()}.pdf"
                upload_blob_from_fileobj(file.stream, temp_blob_path)
                tmp_path = download_blob_to_tmp(temp_blob_path)
                merger.append(PdfReader(tmp_path))
                os.remove(tmp_path)

        output_tmp_path = f"/tmp/{file_id}_merged.pdf"
        with open(output_tmp_path, "wb") as f_out:
            merger.write(f_out)

        upload_file_to_gcs(output_tmp_path, gcs_output_path)
        signed_url = generate_signed_url(gcs_output_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})

    except Exception as e:
        return f"Merging failed: {e}", 500


@app.route("/split", methods=["POST"])
def split():
    file = request.files.get("file")
    if not file or not file.filename.endswith(".pdf"):
        return "Invalid file", 400

    start = int(request.form.get("start", 1))
    end = int(request.form.get("end", 1))
    file_id = str(uuid.uuid4())
    gcs_input_path = f"uploads/{file_id}.pdf"
    gcs_output_path = f"processed/{file_id}_split.pdf"

    try:
        upload_blob_from_fileobj(file.stream, gcs_input_path)
        input_tmp_path = download_blob_to_tmp(gcs_input_path)

        reader = PdfReader(input_tmp_path)
        writer = PdfWriter()
        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        output_tmp_path = f"/tmp/{file_id}_split.pdf"
        with open(output_tmp_path, "wb") as f_out:
            writer.write(f_out)

        upload_file_to_gcs(output_tmp_path, gcs_output_path)
        signed_url = generate_signed_url(gcs_output_path)

        os.remove(input_tmp_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})

    except Exception as e:
        return f"Splitting failed: {e}", 500


@app.route("/image", methods=["POST"])
def image_to_pdf():
    files = request.files.getlist("file")
    images = []

    try:
        for file in files:
            if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(file.stream)
                img = img.convert("RGB")
                images.append(img)

        if not images:
            return "No valid images uploaded", 400

        file_id = str(uuid.uuid4())
        gcs_output_path = f"processed/{file_id}_image2pdf.pdf"
        output_tmp_path = f"/tmp/{file_id}_image2pdf.pdf"

        images[0].save(output_tmp_path, format="PDF", save_all=True, append_images=images[1:])
        upload_file_to_gcs(output_tmp_path, gcs_output_path)
        signed_url = generate_signed_url(gcs_output_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})

    except Exception as e:
        return f"Image to PDF failed: {e}", 500


import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
