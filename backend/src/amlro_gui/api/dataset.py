from flask import Blueprint, current_app, jsonify

from amlro_gui.services import dataset_service

bp = Blueprint(
    "dataset", __name__, url_prefix="/api/experiments/<experiment_id>"
)


@bp.get("/dataset")
def full_dataset(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    result = dataset_service.get_full_dataset(workspace_root, experiment_id)
    return jsonify(result)
