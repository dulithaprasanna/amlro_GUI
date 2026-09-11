from flask import Blueprint, current_app, jsonify, request

from amlro_gui.services import training_service

bp = Blueprint(
    "training", __name__, url_prefix="/api/experiments/<experiment_id>"
)


@bp.get("/training")
def training_table(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    table = training_service.get_training_table(workspace_root, experiment_id)
    return jsonify(table)


@bp.post("/training/next")
def training_next(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    body = request.get_json(silent=True) or {}
    result = training_service.next_training_batch(
        workspace_root, experiment_id, obj_values=body.get("obj_values")
    )
    return jsonify(result)
