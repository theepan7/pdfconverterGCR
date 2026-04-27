from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import subprocess
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from PIL import Image
import traceback
import tempfile
import json
import time
from datetime import datetime, timezone

# ---------------- Config ---------------- #
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://minipdftool.com",
            "https://www.minipdftool.com",
        ],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
    }
})

# Max upload size = 32 MB
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024


# ---------------- Structured Logging ---------------- #
def log_event(event: str, status: str, **kwargs):
    """
    Emit a structured JSON log line that Cloud Logging can parse and query.

    Fields always present:
      - timestamp  : ISO-8601 UTC
      - event      : operation name  (upload, compress, merge, split, image_to_pdf, download)
      - status     : "success" | "error"

    Optional kwargs (pass whatever is relevant):
      - file_size_kb, page_count, duration_ms, error, filename, file_count, etc.
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "status": status,
        **kwargs,
    }
    # Cloud Run captures stdout → Cloud Logging automatically
    print(json.dumps(payload), flush=True)


# ---------------- Utility ---------------- #
def get_file_size_kb(path: str) -> float:
    try:
        return round(os.path.getsize(path) / 1024, 2)
    except Exception:
        return 0.0


def json_error(message, code=500, extra=None):
    payload = {"error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), code


# ---------------- Error Handlers ---------------- #
@app.errorhandler(413)
def request_entity_too_large(_error):
    log_event("upload", "error", error="File exceeds 32 MB limit")
    return json_error("File too large. Max allowed size is 32 MB.", 413)


@app.errorhandler(404)
def not_found(_error):
    return json_error("Not Found", 404)


@app.errorhandler(500)
def internal_error(_error):
    return json_error("Internal Server Error", 500)


# ---------------- PDF Operations ---------------- #

@app.route("/compress", methods=["POST"])
def compress():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    original_filename = uploaded_file.filename
    start_time = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_id = str(uuid.uuid4())
            input_path = os.path.join(tmp_dir, f"{file_id}_input.pdf")
            output_path = os.path.join(tmp_dir, f"{file_id}_compressed.pdf")

            # Save upload to tmp
            uploaded_file.save(input_path)
            input_size_kb = get_file_size_kb(input_path)

            log_event("upload", "success",
                      operation="compress",
                      filename=original_filename,
                      file_size_kb=input_size_kb)

            # Run Ghostscript
            gs_cmd = [
                "gs", "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE", "-dQUIET", "-dBATCH",
                f"-sOutputFile={output_path}", input_path
            ]
            result = subprocess.run(gs_cmd, capture_output=True, text=True)

            if result.returncode != 0 or not os.path.exists(output_path):
                log_event("compress", "error",
                          filename=original_filename,
                          error="Ghostscript failed",
                          gs_stderr=result.stderr[:500])
                return json_error("Compression failed while running Ghostscript.", 500)

            output_size_kb = get_file_size_kb(output_path)
            duration_ms = round((time.monotonic() - start_time) * 1000)

            log_event("compress", "success",
                      filename=original_filename,
                      input_size_kb=input_size_kb,
                      output_size_kb=output_size_kb,
                      saved_kb=round(input_size_kb - output_size_kb, 2),
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="compress",
                      filename=original_filename,
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"compressed_{original_filename}",
            )

    except Exception as e:
        log_event("compress", "error",
                  filename=original_filename,
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Compression failed due to a server error.", 500)


@app.route("/merge", methods=["POST"])
def merge():
    files = request.files.getlist("files")
    if not files:
        return json_error("No files uploaded.", 400)

    start_time = time.monotonic()
    total_input_kb = 0.0
    valid_count = 0

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            merger = PdfMerger()

            for file in files:
                if file.filename.lower().endswith(".pdf"):
                    tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4()}.pdf")
                    file.save(tmp_path)
                    size_kb = get_file_size_kb(tmp_path)
                    total_input_kb += size_kb
                    valid_count += 1

                    log_event("upload", "success",
                              operation="merge",
                              filename=file.filename,
                              file_size_kb=size_kb)

                    merger.append(PdfReader(tmp_path))

            if valid_count == 0:
                return json_error("No valid PDF files found.", 400)

            file_id = str(uuid.uuid4())
            output_path = os.path.join(tmp_dir, f"{file_id}_merged.pdf")

            with open(output_path, "wb") as f_out:
                merger.write(f_out)
            merger.close()

            output_size_kb = get_file_size_kb(output_path)
            duration_ms = round((time.monotonic() - start_time) * 1000)

            log_event("merge", "success",
                      file_count=valid_count,
                      total_input_size_kb=round(total_input_kb, 2),
                      output_size_kb=output_size_kb,
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="merge",
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name="merged.pdf",
            )

    except Exception as e:
        log_event("merge", "error",
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Merging failed due to a server error.", 500)


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

    original_filename = file.filename
    start_time = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_id = str(uuid.uuid4())
            input_path = os.path.join(tmp_dir, f"{file_id}_input.pdf")
            file.save(input_path)
            input_size_kb = get_file_size_kb(input_path)

            log_event("upload", "success",
                      operation="split",
                      filename=original_filename,
                      file_size_kb=input_size_kb)

            reader = PdfReader(input_path)
            num_pages = len(reader.pages)

            start = max(1, start)
            end = min(end, num_pages)

            if start > end:
                return json_error("Invalid range: start must be ≤ end.", 400)

            writer = PdfWriter()
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])

            output_path = os.path.join(tmp_dir, f"{file_id}_split.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            output_size_kb = get_file_size_kb(output_path)
            duration_ms = round((time.monotonic() - start_time) * 1000)
            pages_extracted = end - start + 1

            log_event("split", "success",
                      filename=original_filename,
                      total_pages=num_pages,
                      pages_extracted=pages_extracted,
                      page_range=f"{start}-{end}",
                      input_size_kb=input_size_kb,
                      output_size_kb=output_size_kb,
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="split",
                      filename=original_filename,
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"split_{original_filename}",
            )

    except Exception as e:
        log_event("split", "error",
                  filename=original_filename,
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Splitting failed due to a server error.", 500)


@app.route("/image", methods=["POST"])
def image_to_pdf():
    files = request.files.getlist("file")
    images = []
    start_time = time.monotonic()
    total_input_kb = 0.0
    valid_count = 0

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for file in files:
                name = file.filename.lower()
                if name.endswith((".png", ".jpg", ".jpeg")):
                    tmp_img_path = os.path.join(tmp_dir, f"{uuid.uuid4()}_{file.filename}")
                    file.save(tmp_img_path)
                    size_kb = get_file_size_kb(tmp_img_path)
                    total_input_kb += size_kb
                    valid_count += 1

                    log_event("upload", "success",
                              operation="image_to_pdf",
                              filename=file.filename,
                              file_size_kb=size_kb)

                    img = Image.open(tmp_img_path).convert("RGB")
                    images.append(img)

            if not images:
                return json_error("No valid images uploaded.", 400)

            file_id = str(uuid.uuid4())
            output_path = os.path.join(tmp_dir, f"{file_id}_image2pdf.pdf")
            images[0].save(output_path, format="PDF", save_all=True, append_images=images[1:])

            output_size_kb = get_file_size_kb(output_path)
            duration_ms = round((time.monotonic() - start_time) * 1000)

            log_event("image_to_pdf", "success",
                      image_count=valid_count,
                      total_input_size_kb=round(total_input_kb, 2),
                      output_size_kb=output_size_kb,
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="image_to_pdf",
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name="images_converted.pdf",
            )

    except Exception as e:
        log_event("image_to_pdf", "error",
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Image to PDF failed due to a server error.", 500)

    finally:
        for im in images:
            try:
                im.close()
            except Exception:
                pass


# ---------------- Health Check ---------------- #
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
