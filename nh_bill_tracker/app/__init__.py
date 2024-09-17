from app import models
from flask import Flask
from config import Config
from app.extensions import db, migrate, login, cache, scheduler
from flask_admin import Admin
from flask_wtf.csrf import CSRFProtect
import atexit

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)

    admin = Admin(app, name='NH Bill Tracker Admin',
                  template_mode='bootstrap3')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import init_admin
    init_admin(admin)

    from app.bill_tracker import update_bills_from_rss, update_bill_categories

    def run_bill_update():
        with app.app_context():
            update_bills_from_rss()

    def run_category_update():
        with app.app_context():
            update_bill_categories()

    scheduler.add_job(func=run_bill_update, trigger="interval", hours=6)
    scheduler.add_job(func=run_category_update, trigger="interval", hours=24)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    from app.cli import create_superuser
    app.cli.add_command(create_superuser)

    return app
