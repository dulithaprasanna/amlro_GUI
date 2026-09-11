from flask import Blueprint, current_app, jsonify, request

from amlro_gui.services import experiment_service

bp = Blueprint("experiments", __name__, url_prefix="/api/experiments")


@bp.get("")
def list_experiments():
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    summaries = experiment_service.list_experiments(workspace_root)
    return jsonify([summary.model_dump(mode="json") for summary in summaries])


@bp.post("")
def create_experiment():
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    body = request.get_json(silent=True) or {}
    state = experiment_service.create_experiment(
        workspace_root,
        mode=body.get("mode", "new"),
        experiment_id=body.get("id"),
        exp_dir=body.get("exp_dir"),
    )
    return jsonify(state.model_dump(mode="json")), 201


@bp.get("/<experiment_id>")
def get_experiment(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    state = experiment_service.load_state(workspace_root, experiment_id)
    return jsonify(state.model_dump(mode="json"))


@bp.delete("/<experiment_id>")
def remove_experiment(experiment_id):
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    delete_files = request.args.get("delete_files", "false").lower() == "true"
    experiment_service.remove_experiment(
        workspace_root, experiment_id, delete_files=delete_files
    )
    return "", 204


@bp.post("/scan")
def scan_for_experiments():
    workspace_root = current_app.config["WORKSPACE_ROOT"]
    body = request.get_json(force=True)
    root_dir = body.get("root_dir")
    if not root_dir:
        raise ValueError("root_dir is required.")

    result = experiment_service.scan_for_experiments(workspace_root, root_dir)
    return jsonify(
        {
            "added": [summary.model_dump(mode="json") for summary in result["added"]],
            "skipped": result["skipped"],
        }
    )
