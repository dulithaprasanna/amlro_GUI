from flask import Blueprint, current_app, jsonify, request

from amlro_gui.services import data_service

bp = Blueprint(
    "data", __name__, url_prefix="/api/experiments/<experiment_id>"
)


@bp.post("/data")
def upload_data(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    file = request.files["file"]
    file_name = request.form.get("file_name", "reactions_data.csv")
    result = data_service.upload_reaction_data(
        workspace_root, experiment_id, file, file_name
    )
    return jsonify(result)
