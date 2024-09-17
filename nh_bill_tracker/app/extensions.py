from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
cache = Cache(config={'CACHE_TYPE': 'simple'})
scheduler = BackgroundScheduler()

# Remove the Admin instance from here
