from flask import Flask, jsonify
from pydantic import ValidationError

from amlro_gui.exceptions import (
    ExperimentAlreadyExistsError,
    ExperimentNotFoundError,
    InvalidExperimentIdError,
)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ExperimentNotFoundError)
    def handle_not_found(err):
        return jsonify({"error": str(err)}), 404

    @app.errorhandler(InvalidExperimentIdError)
    @app.errorhandler(ExperimentAlreadyExistsError)
    def handle_bad_request(err):
        return jsonify({"error": str(err)}), 400

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        messages = [
            "{}: {}".format(".".join(str(loc) for loc in e["loc"]), e["msg"])
            for e in err.errors()
        ]
        return jsonify({"error": "; ".join(messages)}), 422

    @app.errorhandler(ValueError)
    def handle_value_error(err):
        return jsonify({"error": str(err)}), 400

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Something went wrong. Please try again."}), 500
