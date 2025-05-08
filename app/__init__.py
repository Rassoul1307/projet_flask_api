from flask import Flask
from .config import Config
from .routes import main 

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialiser la base de données
    from .db_init import init_db
    with app.app_context():
        init_db()

    # Importer et enregistrer le blueprint principal
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app