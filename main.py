import os
from pathlib import Path

from flask import Flask

from quiz.api import api_bp
from quiz.models import db

_env_file = Path(__file__).with_name(".env")
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        # Flask-SQLAlchemy читает именно SQLALCHEMY_DATABASE_URI
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///project.db"),
        ADMIN_API_KEY=os.environ.get("ADMIN_API_KEY", ""),
        JSON_AS_ASCII=False,
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    app.config.update(config or {})
    db.init_app(app)
    app.register_blueprint(api_bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    with app.app_context():
        db.create_all()
    return app


app = create_app()

if __name__ == "__main__":
    app.run()
