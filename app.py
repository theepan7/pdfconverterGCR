from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os, uuid, subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
from google.cloud import storage
from datetime import timedelta
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "/secrets/pdftoolkitkey"
)
storage_client = storage.Client(credentials=credentials)


app = Flask(__name__, static_folder='static')
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

# Google Cloud Storage bucket name (set this in your environment or default here)
GCS_BUCKET = os.environ.get('GCS_BUCKET', 'pdftoolkituploads')

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

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

@app.errorhandler(413)
def request_entity_too_large(error):
    return "File too large. Max allowed size is 5MB.", 413

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/compress-page')
def compress_page():
    return render_template('compress.html')

@app.route('/merge-page')
def merge_page():
    return render_template('merge.html')

@app.route('/split-page')
def split_page():
    return render_template('split.html')

@app.route('/image-page')
def image_page():
    return render_template('image.html')

@app.route('/compress', methods=['POST'])
def compress():
    uploaded_file = request.files.get('file')
    if uploaded_file and uploaded_file.filename.endswith('.pdf'):
        file_id = str(uuid.uuid4())
        gcs_input_path = f"uploads/{file_id}.pdf"
        gcs_output_path = f"processed/{file_id}_compressed.pdf"

        # Upload original PDF to GCS
        upload_blob_from_fileobj(uploaded_file.stream, gcs_input_path)

        # Download to tmp for processing
        input_tmp_path = download_blob_to_tmp(gcs_input_path)
        output_tmp_path = f"/tmp/{file_id}_compressed.pdf"

        try:
            subprocess.run([
                "gs", "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={output_tmp_path}", input_tmp_path
            ], check=True)

            # Upload compressed PDF back to GCS
            upload_file_to_gcs(output_tmp_path, gcs_output_path)

            # Generate signed URL for client download
            signed_url = generate_signed_url(gcs_output_path)

            # Cleanup temp files
            os.remove(input_tmp_path)
            os.remove(output_tmp_path)

            return jsonify({"download_url": signed_url})

        except Exception as e:
            return f"Compression failed: {e}", 500

    return "Invalid file", 400

@app.route('/merge', methods=['POST'])
def merge():
    files = request.files.getlist('files')
    file_id = str(uuid.uuid4())
    gcs_output_path = f"processed/{file_id}_merged.pdf"

    merger = PdfMerger()

    try:
        # Upload all files to GCS and append them to merger
        for file in files:
            if file.filename.endswith('.pdf'):
                gcs_temp_path = f"uploads/{uuid.uuid4()}.pdf"
                upload_blob_from_fileobj(file.stream, gcs_temp_path)
                tmp_path = download_blob_to_tmp(gcs_temp_path)
                merger.append(PdfReader(tmp_path))
                os.remove(tmp_path)
                # Optionally, delete uploaded temp input from GCS here

        output_tmp_path = f"/tmp/{file_id}_merged.pdf"
        with open(output_tmp_path, 'wb') as f_out:
            merger.write(f_out)

        upload_file_to_gcs(output_tmp_path, gcs_output_path)
        signed_url = generate_signed_url(gcs_output_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})
    except Exception as e:
        return f"Merging failed: {e}", 500

@app.route('/split', methods=['POST'])
def split():
    file = request.files.get('file')
    start = int(request.form.get('start', 1))
    end = int(request.form.get('end', 1))

    if file and file.filename.endswith('.pdf'):
        file_id = str(uuid.uuid4())
        gcs_input_path = f"uploads/{file_id}.pdf"
        gcs_output_path = f"processed/{file_id}_split.pdf"

        upload_blob_from_fileobj(file.stream, gcs_input_path)
        input_tmp_path = download_blob_to_tmp(gcs_input_path)

        reader = PdfReader(input_tmp_path)
        writer = PdfWriter()
        try:
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])

            output_tmp_path = f"/tmp/{file_id}_split.pdf"
            with open(output_tmp_path, 'wb') as f_out:
                writer.write(f_out)

            upload_file_to_gcs(output_tmp_path, gcs_output_path)
            signed_url = generate_signed_url(gcs_output_path)

            os.remove(input_tmp_path)
            os.remove(output_tmp_path)

            return jsonify({"download_url": signed_url})

        except Exception as e:
            return f"Splitting failed: {e}", 500

    return "Invalid file", 400

@app.route('/image', methods=['POST'])
def image_to_pdf():
    files = request.files.getlist('file')
    images = []

    try:
        for file in files:
            if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(file.stream)
                img.load()
                img = img.convert("RGB")
                images.append(img)

        if not images:
            return "No valid images uploaded", 400

        file_id = str(uuid.uuid4())
        gcs_output_path = f"processed/{file_id}_image2pdf.pdf"
        output_tmp_path = f"/tmp/{file_id}_image2pdf.pdf"

        images[0].save(output_tmp_path, format='PDF', save_all=True, append_images=images[1:])
        upload_file_to_gcs(output_tmp_path, gcs_output_path)
        signed_url = generate_signed_url(gcs_output_path)
        os.remove(output_tmp_path)

        return jsonify({"download_url": signed_url})

    except Exception as e:
        print("[ERROR] Image to PDF failed:", e)
        return f"Image to PDF failed: {e}", 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
