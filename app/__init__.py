from flask import Flask
from .database import db

def create_app(config=None):
    app = Flask(__name__, static_folder='static', static_url_path='')
    app.config.from_object('config')
    if config:
        app.config.update(config)

    db.init_app(app)

    with app.app_context():
        from . import models  # noqa: ensure models are registered
        db.create_all()

    from .api import pantry, preferences, recipes, weeks
    app.register_blueprint(pantry.bp)
    app.register_blueprint(preferences.bp)
    app.register_blueprint(recipes.bp)
    app.register_blueprint(weeks.bp)

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    return app
