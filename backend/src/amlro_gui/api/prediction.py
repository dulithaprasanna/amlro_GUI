from flask import Blueprint, current_app, jsonify, request

from amlro_gui.services import prediction_service

bp = Blueprint(
    "prediction", __name__, url_prefix="/api/experiments/<experiment_id>"
)


@bp.get("/prediction")
def current_batch(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    result = prediction_service.get_current_batch(workspace_root, experiment_id)
    return jsonify(result)


@bp.post("/prediction/resume")
def resume_optimization(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    state = prediction_service.resume_optimization(workspace_root, experiment_id)
    return jsonify(state.model_dump(mode="json"))


@bp.post("/prediction/batch-size")
def update_batch_size(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    body = request.get_json(force=True)

    batch_size = body.get("batch_size")
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer.")

    state = prediction_service.update_batch_size(
        workspace_root, experiment_id, batch_size
    )
    return jsonify(state.model_dump(mode="json"))


@bp.post("/prediction/next")
def submit_batch(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    body = request.get_json(force=True)

    parameters = body.get("parameters")
    objectives = body.get("objectives")
    if parameters is None or objectives is None:
        raise ValueError(
            "parameters and objectives are required to submit a batch — use "
            "GET .../prediction to fetch the current batch without submitting."
        )

    result = prediction_service.submit_batch(
        workspace_root,
        experiment_id,
        parameters=parameters,
        objectives=objectives,
        stop=body.get("stop", False),
        batch_size=body.get("batch_size"),
    )
    return jsonify(result)
