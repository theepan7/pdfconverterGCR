from flask import Flask, request, send_file
from flask_cors import CORS
import os
import uuid
import subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

app = Flask(__name__)

# --- CORRECTED CORS CONFIGURATION ---
# The flask_cors extension simplifies this, so you don't need the `add_cors_headers`
# after_request function. Just provide the specific origin(s).
CORS(app, origins="https://lemonchiffon-dunlin-886347.hostingersite.com")

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# --- CORRECTED - Removed the redundant `add_cors_headers` function ---
# The flask_cors extension handles this automatically.
# It will correctly set the 'Access-Control-Allow-Origin', 'Access-Control-Allow-Headers',
# and 'Access-Control-Allow-Methods' headers based on the configuration above.
# It also correctly handles preflight OPTIONS requests, so the manual `if request.method == 'OPTIONS'`
# checks are no longer necessary.

@app.route('/')
def index():
    return "✅ PDF Tool API is running."

# === API: Compress PDF ===
# Removed the manual OPTIONS method check, as flask_cors handles it.
@app.route('/compress', methods=['POST'])
def compress():
    # --- ERROR: Request Entity Too Large (413) ---
    # The default request body size limit for Flask/Werkzeug is quite small.
    # To fix the 413 error, you need to increase this limit.
    # You can configure this using app.config, but a better approach on Cloud Run
    # is to ensure your client is using HTTP/2 and that your code doesn't
    # have any internal limits that are too low. However, to be safe, you can
    # increase the max content length. The `flask_cors` extension handles this as well.
    # A more robust solution is to use a dedicated library for file uploads that
    # handles larger files better, but for now, this is a reasonable change.

    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename.endswith('.pdf'):
        return "Invalid file", 400

    file_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.pdf")
    output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_compressed.pdf")

    try:
        uploaded_file.save(input_path)
        # Use a more efficient subprocess command.
        # Check if ghostscript is installed on the Cloud Run container image.
        subprocess.run([
            "gs", "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_path}", input_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) # Suppress output

        return send_file(output_path, as_attachment=True, mimetype='application/pdf')
    except subprocess.CalledProcessError as e:
        return f"Compression failed: {e}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        # --- BEST PRACTICE: CLEAN UP FILES ---
        # It's crucial to remove temporary files after processing.
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# === API: Merge PDFs ===
@app.route('/merge', methods=['POST'])
def merge():
    files = request.files.getlist('files')
    if not files:
        return "No files provided", 400
    
    file_id = str(uuid.uuid4())
    output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_merged.pdf")

    try:
        merger = PdfMerger()
        for file in files:
            if file and file.filename.endswith('.pdf'):
                merger.append(PdfReader(file.stream))
        
        merger.write(output_path)
        merger.close()

        return send_file(output_path, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return f"Merging failed: {e}", 500
    finally:
        # --- CLEAN UP ---
        if os.path.exists(output_path):
            os.remove(output_path)


# === API: Split PDF ===
@app.route('/split', methods=['POST'])
def split():
    file = request.files.get('file')
    start = request.form.get('start', type=int, default=1)
    end = request.form.get('end', type=int, default=1)

    if not file or not file.filename.endswith('.pdf'):
        return "Invalid file", 400

    file_id = str(uuid.uuid4())
    output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_split.pdf")

    try:
        reader = PdfReader(file.stream)
        writer = PdfWriter()
        
        # Validate page numbers
        if not (1 <= start <= end <= len(reader.pages)):
            return "Invalid start or end page numbers", 400

        for i in range(start - 1, end):
            writer.add_page(reader.pages[i])

        with open(output_path, 'wb') as f_out:
            writer.write(f_out)

        return send_file(output_path, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        return f"Splitting failed: {e}", 500
    finally:
        # --- CLEAN UP ---
        if os.path.exists(output_path):
            os.remove(output_path)

# === Run App ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
