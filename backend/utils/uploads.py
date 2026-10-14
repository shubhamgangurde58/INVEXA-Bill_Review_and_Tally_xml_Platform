import ntpath
import os

from werkzeug.utils import secure_filename

from config import Config

EXTENSION_TO_KIND = {"pdf": "pdf", "jpg": "jpeg", "jpeg": "jpeg", "png": "png"}
KIND_TO_MIME = {"pdf": "application/pdf", "jpeg": "image/jpeg", "png": "image/png"}
ALLOWED_MIMES = {
    "pdf": ["application/pdf", "application/x-pdf"],
    "jpeg": ["image/jpeg", "image/pjpeg"],
    "png": ["image/png"],
}
MAX_STEM_LENGTH = 60


# Look at the first bytes of the file to find out what it really is.
# The extension and the browser's content type can both be faked, but a
# real PDF, PNG or JPEG always starts with the same signature bytes.
def detect_kind(data):
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    return ""


# Build a safe stored file name: letters, digits, dash and underscore only,
# with the checked extension. The original name is never trusted.
def make_file_name(original_name, extension):
    stem = ntpath.splitext(ntpath.basename(original_name))[0]
    stem = secure_filename(stem)[:MAX_STEM_LENGTH]
    if stem == "":
        stem = "bill"
    return stem + "." + extension


# Check an uploaded file in four ways: extension, browser content type, size
# and real content. All four must agree, as the spec requires. Returns
# (upload, None) or (None, (message, status)). upload holds the bytes, the
# clean extension, the content type and the safe file name.
def read_upload(file_storage):
    if file_storage is None or file_storage.filename == "":
        return None, ("Please choose a file to upload", 400)

    extension = os.path.splitext(file_storage.filename)[1].lower().lstrip(".")
    kind = EXTENSION_TO_KIND.get(extension, "")
    if kind == "":
        return None, ("Only PDF, JPG and PNG files are allowed", 400)

    if (file_storage.mimetype or "").lower() not in ALLOWED_MIMES[kind]:
        return None, ("The file type does not match its extension", 400)

    data = file_storage.read(Config.MAX_UPLOAD_BYTES + 1)
    if len(data) > Config.MAX_UPLOAD_BYTES:
        return None, ("The file is too large. The limit is 10 MB", 413)
    if len(data) == 0:
        return None, ("The file is empty", 400)
    if detect_kind(data) != kind:
        return None, ("The file content does not match its type", 400)

    clean_extension = extension
    if kind == "jpeg":
        clean_extension = "jpg"

    upload = {
        "data": data,
        "extension": clean_extension,
        "mime_type": KIND_TO_MIME[kind],
        "file_name": make_file_name(file_storage.filename, clean_extension),
    }
    return upload, None
