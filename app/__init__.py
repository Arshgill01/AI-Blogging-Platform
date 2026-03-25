from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    default_db_path = Path(app.instance_path) / "blog.db"
    app.config.from_mapping(
        SECRET_KEY="dev",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{default_db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from app.seed import load_seed_data, register_seed_commands

    from app.routes.analytics import analytics_bp
    from app.routes.main import main_bp
    from app.routes.posts import posts_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(analytics_bp)
    register_seed_commands(app)

    with app.app_context():
        from app import models

        db.create_all()
        load_seed_data()

    return app
