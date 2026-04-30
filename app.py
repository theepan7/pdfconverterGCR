from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import uuid
import zipfile
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
            "https://minipdftools.com",
            "https://www.minipdftools.com",
            "https://93adaee1.minipdftools.pages.dev"
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




# ---------------- Rotate PDF ---------------- #

@app.route("/rotate", methods=["POST"])
def rotate():
    """
    Rotate pages in a PDF.

    Form fields:
      file    — one PDF file (required)
      angle   — 90 | 180 | 270  (required)
      pages   — "all"  OR  "1,3,5"  OR  "1-5,8,10-12"  (default: "all")
                Page numbers are 1-based.
    """
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    # Validate angle
    try:
        angle = int(request.form.get("angle", 90))
        if angle not in (90, 180, 270):
            raise ValueError
    except (ValueError, TypeError):
        return json_error("Invalid angle. Must be 90, 180, or 270.", 400)

    pages_param    = request.form.get("pages", "all").strip()
    original_filename = file.filename
    start_time     = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_id    = str(uuid.uuid4())
            input_path = os.path.join(tmp_dir, f"{file_id}_input.pdf")
            file.save(input_path)
            input_size_kb = get_file_size_kb(input_path)

            log_event("upload", "success",
                      operation="rotate",
                      filename=original_filename,
                      file_size_kb=input_size_kb)

            reader     = PdfReader(input_path)
            num_pages  = len(reader.pages)
            writer     = PdfWriter()

            # Parse which pages to rotate
            try:
                rotate_indices = set(_parse_page_list(pages_param, num_pages))
            except ValueError as ve:
                return json_error(str(ve), 400)

            for i, page in enumerate(reader.pages):
                if i in rotate_indices:
                    page.rotate(angle)
                writer.add_page(page)

            output_path = os.path.join(tmp_dir, f"{file_id}_rotated.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            output_size_kb = get_file_size_kb(output_path)
            duration_ms    = round((time.monotonic() - start_time) * 1000)

            log_event("rotate", "success",
                      filename=original_filename,
                      total_pages=num_pages,
                      pages_rotated=len(rotate_indices),
                      angle=angle,
                      input_size_kb=input_size_kb,
                      output_size_kb=output_size_kb,
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="rotate",
                      filename=original_filename,
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"rotated_{original_filename}",
            )

    except Exception as e:
        log_event("rotate", "error",
                  filename=original_filename,
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Rotation failed due to a server error.", 500)


# ---------------- Delete PDF Pages ---------------- #

@app.route("/delete", methods=["POST"])
def delete_pages():
    """
    Delete specific pages from a PDF.

    Form fields:
      file    — one PDF file (required)
      pages   — "1,3,5"  OR  "1-5,8,10-12"  (required)
                Page numbers are 1-based.
    """
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    pages_param = request.form.get("pages", "").strip()
    if not pages_param:
        return json_error("No pages specified. Provide a 'pages' field.", 400)

    original_filename = file.filename
    start_time        = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_id    = str(uuid.uuid4())
            input_path = os.path.join(tmp_dir, f"{file_id}_input.pdf")
            file.save(input_path)
            input_size_kb = get_file_size_kb(input_path)

            log_event("upload", "success",
                      operation="delete_pages",
                      filename=original_filename,
                      file_size_kb=input_size_kb)

            reader    = PdfReader(input_path)
            num_pages = len(reader.pages)

            # Parse pages to DELETE
            try:
                delete_indices = set(_parse_page_list(pages_param, num_pages))
            except ValueError as ve:
                return json_error(str(ve), 400)

            keep_indices = [i for i in range(num_pages) if i not in delete_indices]
            if not keep_indices:
                return json_error(
                    "Cannot delete all pages — at least one page must remain.", 400
                )

            writer = PdfWriter()
            for i in keep_indices:
                writer.add_page(reader.pages[i])

            output_path = os.path.join(tmp_dir, f"{file_id}_deleted.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)

            output_size_kb = get_file_size_kb(output_path)
            duration_ms    = round((time.monotonic() - start_time) * 1000)

            log_event("delete_pages", "success",
                      filename=original_filename,
                      total_pages=num_pages,
                      pages_deleted=len(delete_indices),
                      pages_kept=len(keep_indices),
                      input_size_kb=input_size_kb,
                      output_size_kb=output_size_kb,
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="delete_pages",
                      filename=original_filename,
                      output_size_kb=output_size_kb)

            return send_file(
                output_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"deleted_{original_filename}",
            )

    except Exception as e:
        log_event("delete_pages", "error",
                  filename=original_filename,
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("Delete pages failed due to a server error.", 500)


# ---------------- PDF to JPG ---------------- #

@app.route("/pdf-to-jpg", methods=["POST"])
def pdf_to_jpg():
    """
    Convert PDF pages to JPG images, returned as a ZIP archive.

    Form fields:
      file    — one PDF file (required)
      pages   — "all"  OR  "1,3,5"  OR  "1-5,8"  (default: "all")
                Page numbers are 1-based.
      dpi     — output resolution, default 150 (max 300)
    """
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return json_error("Invalid file. Please upload a PDF.", 400)

    pages_param = request.form.get("pages", "all").strip()

    try:
        dpi = int(request.form.get("dpi", 150))
        dpi = max(72, min(dpi, 300))   # clamp between 72 and 300
    except (ValueError, TypeError):
        dpi = 150

    original_filename = file.filename
    base_name         = os.path.splitext(original_filename)[0]
    start_time        = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_id    = str(uuid.uuid4())
            input_path = os.path.join(tmp_dir, f"{file_id}_input.pdf")
            file.save(input_path)
            input_size_kb = get_file_size_kb(input_path)

            log_event("upload", "success",
                      operation="pdf_to_jpg",
                      filename=original_filename,
                      file_size_kb=input_size_kb)

            # Determine how many pages the PDF has using PyPDF2
            reader    = PdfReader(input_path)
            num_pages = len(reader.pages)

            # Parse which pages to export
            try:
                export_indices = _parse_page_list(pages_param, num_pages)
            except ValueError as ve:
                return json_error(str(ve), 400)

            # Convert requested pages with Ghostscript (one page at a time)
            # Using Ghostscript avoids needing poppler and keeps the container lean.
            jpg_paths = []
            for idx in export_indices:
                page_num    = idx + 1   # 1-based for GS
                jpg_path    = os.path.join(tmp_dir, f"page_{page_num:04d}.jpg")

                gs_cmd = [
                    "gs",
                    "-dNOPAUSE", "-dBATCH", "-dQUIET",
                    "-sDEVICE=jpeg",
                    f"-r{dpi}",
                    f"-dFirstPage={page_num}",
                    f"-dLastPage={page_num}",
                    f"-sOutputFile={jpg_path}",
                    input_path,
                ]
                result = subprocess.run(gs_cmd, capture_output=True, text=True)

                if result.returncode != 0 or not os.path.exists(jpg_path):
                    log_event("pdf_to_jpg", "error",
                              filename=original_filename,
                              page=page_num,
                              error="Ghostscript failed",
                              gs_stderr=result.stderr[:300])
                    return json_error(
                        f"Failed to convert page {page_num}.", 500
                    )

                jpg_paths.append((page_num, jpg_path))

            # Pack all JPGs into a ZIP in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for page_num, jpg_path in jpg_paths:
                    arcname = f"{base_name}_page_{page_num:04d}.jpg"
                    zf.write(jpg_path, arcname=arcname)
            zip_buffer.seek(0)

            total_jpg_kb = sum(
                get_file_size_kb(p) for _, p in jpg_paths
            )
            duration_ms = round((time.monotonic() - start_time) * 1000)

            log_event("pdf_to_jpg", "success",
                      filename=original_filename,
                      total_pages=num_pages,
                      pages_exported=len(jpg_paths),
                      dpi=dpi,
                      input_size_kb=input_size_kb,
                      total_jpg_size_kb=round(total_jpg_kb, 2),
                      duration_ms=duration_ms)

            log_event("download", "success",
                      operation="pdf_to_jpg",
                      filename=original_filename,
                      pages_exported=len(jpg_paths))

            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{base_name}_images.zip",
            )

    except Exception as e:
        log_event("pdf_to_jpg", "error",
                  filename=original_filename,
                  error=str(e),
                  traceback=traceback.format_exc()[:500])
        return json_error("PDF to JPG failed due to a server error.", 500)


# ---- shared page-list parser used by rotate, delete, pdf-to-jpg ---- #

def _parse_page_list(raw: str, total_pages: int) -> list:
    """
    Convert a page specification into a sorted list of 0-based page indices.

    Accepts:
      "all"           → every page
      "1,3,5"         → individual pages  (1-based)
      "1-5"           → inclusive range
      "1-3,7,10-12"   → mixed

    Raises ValueError with a descriptive message on bad input.
    """
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(total_pages))

    indices = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            try:
                start, end = int(bounds[0]), int(bounds[1])
            except ValueError:
                raise ValueError(f"Invalid range segment: '{part}'")
            if start < 1 or end < start or end > total_pages:
                raise ValueError(
                    f"Range {start}–{end} is out of bounds "
                    f"(document has {total_pages} pages)."
                )
            indices.update(range(start - 1, end))
        else:
            try:
                n = int(part)
            except ValueError:
                raise ValueError(f"'{part}' is not a valid page number.")
            if n < 1 or n > total_pages:
                raise ValueError(
                    f"Page {n} is out of bounds "
                    f"(document has {total_pages} pages)."
                )
            indices.add(n - 1)

    return sorted(indices)


# ---------------- Health Check ---------------- #
@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
