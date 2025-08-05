from flask import Flask, request, send_file, render_template
from flask_cors import CORS
import os, uuid, subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
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

@app.route('/image', methods=['POST'])
def image_to_pdf():
    from PIL import Image
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
        output_path = os.path.join(PROCESSED_FOLDER, f"{file_id}_image2pdf.pdf")

        # ✅ Add your debug print statements here
        print(f"[INFO] Number of files received: {len(files)}")
        print(f"[INFO] Files: {[f.filename for f in files]}")
        print(f"[INFO] Output PDF will be saved at: {output_path}")

        # Save the PDF
        images[0].save(output_path, format='PDF', save_all=True, append_images=images[1:])

        return send_file(output_path, mimetype='application/pdf', as_attachment=True)
    except Exception as e:
        print("[ERROR] Image to PDF failed:", e)
        return f"Image to PDF failed: {e}", 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
