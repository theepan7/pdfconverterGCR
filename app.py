
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
import os, uuid, subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image

app = Flask(__name__, static_folder='static')
CORS(app)

UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

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
        input_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.pdf")
        output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_compressed.pdf")
        uploaded_file.save(input_path)
        try:
            subprocess.run([
                "gs", "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={output_path}", input_path
            ], check=True)
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"Compression failed: {e}", 500
    return "Invalid file", 400

@app.route('/merge', methods=['POST'])
def merge():
    files = request.files.getlist('files')
    merger = PdfMerger()
    file_id = str(uuid.uuid4())
    output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_merged.pdf")
    try:
        for file in files:
            if file.filename.endswith('.pdf'):
                merger.append(PdfReader(file.stream))
        with open(output_path, 'wb') as f_out:
            merger.write(f_out)
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return f"Merging failed: {e}", 500

@app.route('/split', methods=['POST'])
def split():
    file = request.files.get('file')
    start = int(request.form.get('start', 1))
    end = int(request.form.get('end', 1))
    if file and file.filename.endswith('.pdf'):
        file_id = str(uuid.uuid4())
        output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_split.pdf")
        reader = PdfReader(file.stream)
        writer = PdfWriter()
        try:
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])
            with open(output_path, 'wb') as f_out:
                writer.write(f_out)
            return send_file(output_path, as_attachment=True)
        except Exception as e:
            return f"Splitting failed: {e}", 500
    return "Invalid file", 400

@app.route('/image-to-pdf', methods=['POST'])
def image_to_pdf():
    if 'file' not in request.files:
        return {'error': 'No file uploaded'}, 400

    img_file = request.files['file']
    if img_file.filename == '':
        return {'error': 'No selected file'}, 400

    try:
        img = Image.open(img_file)
        pdf_filename = f"{uuid.uuid4()}.pdf"
        pdf_path = os.path.join(PROCESSED_FOLDER, pdf_filename)

        # Convert image to RGB & resize
        a4_width, a4_height = A4
        img = img.convert("RGB")
        img_width, img_height = img.size
        ratio = min(a4_width / img_width, a4_height / img_height)
        img_width = int(img_width * ratio)
        img_height = int(img_height * ratio)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        x = (a4_width - img_width) / 2
        y = (a4_height - img_height) / 2

        temp_img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.jpg")
        img.save(temp_img_path)
        c.drawImage(temp_img_path, x, y, width=img_width, height=img_height)
        c.showPage()
        c.save()
        os.remove(temp_img_path)

        return send_file(pdf_path, as_attachment=True, download_name="converted.pdf")
    
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
