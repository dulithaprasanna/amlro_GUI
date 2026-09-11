from flask import Blueprint, current_app, jsonify, request

from amlro_gui.schemas.config import ExperimentConfig
from amlro_gui.services import reaction_scope_service

bp = Blueprint(
    "reaction_scope", __name__, url_prefix="/api/experiments/<experiment_id>"
)


@bp.post("/reaction-scope")
def create_reaction_scope(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    config = ExperimentConfig.model_validate(request.get_json(force=True))
    state = reaction_scope_service.create_reaction_scope(
        workspace_root, experiment_id, config
    )
    return jsonify(state.model_dump(mode="json"))
