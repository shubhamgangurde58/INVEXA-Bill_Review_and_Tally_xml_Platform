import os

from dotenv import load_dotenv

# Read the .env file once at import time so every other file can use Config.
# Keeping secrets in .env means they never end up in git.
load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    MONGO_URI = os.getenv("MONGO_URI", "")
    DB_NAME = os.getenv("DB_NAME", "invexa")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # Optional paths for OCR tools (needed mostly on Windows)
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
    POPPLER_PATH = os.getenv("POPPLER_PATH", "")

    JWT_EXPIRY_HOURS = 24

    # Uploads are limited to 10 MB. Flask gets 1 MB extra for multipart overhead.
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024
    MAX_CONTENT_LENGTH = 11 * 1024 * 1024

    DEFAULT_RATE_LIMIT = "1000 per minute"      
    LOGIN_RATE_LIMIT   = "100 per 15 minutes"   
    SIGNUP_RATE_LIMIT  = "100 per hour"

    # Stop the app at startup if a required setting is missing or weak.
    # Failing early is better than failing later with a confusing JWT or DB error.
    @classmethod
    def check_required(cls):
        if not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY is missing. Add it to your .env file.")
        if len(cls.SECRET_KEY) < 64:
            raise RuntimeError(
                "SECRET_KEY is too short. Use a 32-byte hex key (64 characters)."
            )
        if not cls.MONGO_URI:
            raise RuntimeError("MONGO_URI is missing. Add it to your .env file.")
