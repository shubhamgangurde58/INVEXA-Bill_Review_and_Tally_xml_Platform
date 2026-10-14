"""
Flask application factory. Everything is wired up in one place so
tests can build a fresh app without touching the real database.

At startup this checks that Tesseract is available and prints a
loud warning if it is not. Otherwise the CA's OCR button would
fail on every click with no clue why.
"""

from flask import Flask, request
from flask_cors import CORS

from config import Config
from db_setup import setup_database
from extensions import limiter
from utils.responses import error, success
from utils.validators import contains_dollar_key

from modules.auth.routes import auth_bp
from modules.chat.routes import chat_bp
from modules.client.routes import client_bp
from modules.firm.routes import firm_bp
from modules.invoice.routes import invoice_bp
from modules.notifications.routes import notifications_bp
from modules.review.routes import review_bp
from modules.xml.routes import xml_bp


def create_app(setup_db=True):
    Config.check_required()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    CORS(app, origins=[Config.FRONTEND_ORIGIN], supports_credentials=True)

    limiter.init_app(app)

    if setup_db:
        prepare_database()

    register_blueprints(app)
    register_request_hooks(app)
    register_error_handlers(app)
    register_health_route(app)
    check_ocr_at_startup()

    return app


# Create collections and indexes at startup. If MongoDB is
# unreachable we stop with a clear message.
def prepare_database():
    try:
        setup_database()
    except Exception as problem:
        raise RuntimeError(
            "Could not set up MongoDB. Check MONGO_URI and your Atlas "
            "network access list. Details: " + str(problem)
        ) from problem


# Print the OCR health once. If Tesseract is missing the CA would
# click Extract and get nothing, so we tell the developer up front.
def check_ocr_at_startup():
    try:
        from modules.review.ocr import ocr_status
        status = ocr_status()
        if status["ready"]:
            print("[INVEXA] Tesseract is ready. OCR will work.")
        else:
            print("")
            print("[INVEXA] =======================================")
            print("[INVEXA] WARNING: OCR will not work.")
            print("[INVEXA] " + status["message"])
            print("[INVEXA] =======================================")
            print("")
    except Exception as exc:
        print("[INVEXA] OCR check failed:", exc)


# Attach each feature area under its own URL prefix.
def register_blueprints(app):
    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(firm_bp,          url_prefix="/api/firm")
    app.register_blueprint(client_bp,        url_prefix="/api/client")
    app.register_blueprint(invoice_bp,       url_prefix="/api/invoice")
    app.register_blueprint(review_bp,        url_prefix="/api/review")
    app.register_blueprint(chat_bp,          url_prefix="/api/chat")
    app.register_blueprint(xml_bp,           url_prefix="/api/xml")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")


# Security check before every request. Rejecting "$" keys here
# protects every route at once.
def register_request_hooks(app):
    @app.before_request
    def block_nosql_injection():
        if request.method == "OPTIONS":
            return None
        body = request.get_json(silent=True)
        if body is None:
            return None
        if contains_dollar_key(body):
            return error("Invalid request", 400)
        return None


# JSON error handlers so the frontend always sees the same shape.
def register_error_handlers(app):
    @app.errorhandler(400)
    def handle_bad_request(e):
        return error("Bad request", 400)

    @app.errorhandler(401)
    def handle_unauthorized(e):
        return error("Authentication required", 401)

    @app.errorhandler(403)
    def handle_forbidden(e):
        return error("You do not have permission", 403)

    @app.errorhandler(404)
    def handle_not_found(e):
        return error("Resource not found", 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return error("Method not allowed", 405)

    @app.errorhandler(413)
    def handle_file_too_large(e):
        return error("File too large. Maximum size is 10 MB", 413)

    @app.errorhandler(422)
    def handle_invalid_data(e):
        return error("Invalid data", 422)

    @app.errorhandler(429)
    def handle_rate_limit(e):
        return error("Too many requests. Please try again later", 429)

    @app.errorhandler(500)
    def handle_server_error(e):
        return error("Something went wrong on the server", 500)


# Small route that proves the server is up.
def register_health_route(app):
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return success({"service": "invexa-api", "ok": True})


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=Config.DEBUG)