from flask import Flask, jsonify

from amlro_gui.api import register_blueprints
from amlro_gui.config import Config
from amlro_gui.errors import register_error_handlers


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    register_blueprints(app)
    register_error_handlers(app)

    return app
