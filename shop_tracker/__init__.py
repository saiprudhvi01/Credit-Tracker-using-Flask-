import os

from flask import Flask

from shop_tracker.config import Config
from shop_tracker.db import close_db, init_db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if app.config["OAUTH_REDIRECT_URI"].startswith("http://localhost"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    from shop_tracker.routes.api import api_bp
    from shop_tracker.routes.auth import auth_bp
    from shop_tracker.routes.customers import customers_bp
    from shop_tracker.routes.dashboard import dashboard_bp
    from shop_tracker.routes.gmail import gmail_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(gmail_bp)
    app.register_blueprint(api_bp)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    return app
