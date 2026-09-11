from flask import Flask

from amlro_gui.api.data import bp as data_bp
from amlro_gui.api.dataset import bp as dataset_bp
from amlro_gui.api.experiments import bp as experiments_bp
from amlro_gui.api.prediction import bp as prediction_bp
from amlro_gui.api.reaction_scope import bp as reaction_scope_bp
from amlro_gui.api.training import bp as training_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(experiments_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(reaction_scope_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(dataset_bp)
