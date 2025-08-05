
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

def test_image_to_pdf():
    import io
    from PIL import Image

    # Create an in-memory test image (e.g., red square)
    img = Image.new('RGB', (1000, 1000), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    # Use Flask test client
    with app.test_client() as client:
        data = {
            'file': (img_byte_arr, 'test.jpg')
        }
        response = client.post('/image', data=data, content_type='multipart/form-data')
        print('Status code:', response.status_code)
        if response.status_code == 200:
            # Save output PDF locally to check
            with open('test_output.pdf', 'wb') as f:
                f.write(response.data)
            print('PDF generated and saved as test_output.pdf')
        else:
            print('Error:', response.get_data(as_text=True))

if __name__ == '__main__':
    # Uncomment to run the test before starting app
    # test_image_to_pdf()
    app.run(host="0.0.0.0", port=8080)

