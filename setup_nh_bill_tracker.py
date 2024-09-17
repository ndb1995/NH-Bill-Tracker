import os
import subprocess
import sys
import venv

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def create_file(path, content=''):
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created file: {path}")

def setup_project():
    base_dir = 'nh_bill_tracker'
    create_directory(base_dir)
    os.chdir(base_dir)

    # Create virtual environment
    venv.create('venv', with_pip=True)
    print("Created virtual environment")

    # Determine the path to the Python executable in the virtual environment
    if sys.platform == "win32":
        python_executable = os.path.join('venv', 'Scripts', 'python.exe')
    else:
        python_executable = os.path.join('venv', 'bin', 'python')

    # Function to run commands in the virtual environment
    def run_in_venv(command):
        subprocess.run([python_executable, "-m"] + command.split())

    # Create app directory and its contents
    create_directory('app')
    create_directory('app/main')
    create_directory('app/auth')
    create_directory('app/templates')
    create_directory('app/templates/auth')

    # Create __init__.py
    create_file('app/__init__.py', '''
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'
scheduler = BackgroundScheduler()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.bill_tracker import update_bills_from_rss
    
    def run_bill_update():
        with app.app_context():
            update_bills_from_rss()

    scheduler.add_job(func=run_bill_update, trigger="interval", hours=6)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    return app

from app import models
''')

    # Create models.py
    create_file('app/models.py', '''
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), index=True, unique=True)
    summary = db.Column(db.Text)
    sponsor = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, index=True)
    full_text = db.Column(db.Text)
''')

    # Create main/__init__.py
    create_file('app/main/__init__.py', '''
from flask import Blueprint

bp = Blueprint('main', __name__)

from app.main import routes
''')

    # Create main/routes.py
    create_file('app/main/routes.py', '''
from flask import render_template, request, current_app
from app.main import bp
from app.models import Bill
from app import db

@bp.route('/')
@bp.route('/index')
def index():
    page = request.args.get('page', 1, type=int)
    bills = Bill.query.order_by(Bill.last_updated.desc()).paginate(
        page=page, per_page=current_app.config['BILLS_PER_PAGE'], error_out=False)
    return render_template('index.html', title='Home', bills=bills)

@bp.route('/bill/<bill_number>')
def bill_detail(bill_number):
    bill = Bill.query.filter_by(number=bill_number).first_or_404()
    return render_template('bill_detail.html', title=f'Bill {bill_number}', bill=bill)
''')

    # Create auth/__init__.py
    create_file('app/auth/__init__.py', '''
from flask import Blueprint

bp = Blueprint('auth', __name__)

from app.auth import routes
''')

    # Create auth/routes.py
    create_file('app/auth/routes.py', '''
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user
from app.auth import bp
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # Implement login logic here
    return render_template('auth/login.html', title='Sign In')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    # Implement registration logic here
    return render_template('auth/register.html', title='Register')
''')

    # Create bill_tracker.py
    create_file('app/bill_tracker.py', '''
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app import db
from app.models import Bill

RSS_FEED_URL = "https://www.gencourt.state.nh.us/rssFeeds/rssQueryResults.aspx?&txtsessionyear=2024&sortoption="
BASE_URL = "https://www.gencourt.state.nh.us/bill_status/legacy/bs2016/"

def fetch_bill_details(bill_id):
    url = f"{BASE_URL}billText.aspx?sy=2024&id={bill_id}&txtFormat=html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract bill text
    bill_text_elem = soup.find('pre', class_='aaaCtype')
    bill_text = bill_text_elem.text if bill_text_elem else "Full bill text not available"
    
    # Extract sponsor
    sponsor_elem = soup.find('td', string='Short Title:')
    sponsor = sponsor_elem.find_next_sibling('td').text if sponsor_elem else "Unknown sponsor"
    
    return bill_text, sponsor

def summarize_bill(bill_text):
    # This is a placeholder for bill summarization
    # In a real implementation, you might use NLP techniques or an AI model to generate a summary
    return bill_text[:500] + "..."  # Return first 500 characters as a simple summary

def update_bills_from_rss():
    feed = feedparser.parse(RSS_FEED_URL)
    
    for entry in feed.entries:
        bill_number = entry.title
        bill_url = entry.link
        published_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
        
        # Extract bill ID from the link
        bill_id = bill_url.split('id=')[1].split('&')[0]
        
        existing_bill = Bill.query.filter_by(number=bill_number).first()
        
        if not existing_bill or existing_bill.last_updated < published_date:
            bill_text, sponsor = fetch_bill_details(bill_id)
            summary = summarize_bill(bill_text)
            
            if existing_bill:
                existing_bill.summary = summary
                existing_bill.sponsor = sponsor
                existing_bill.last_updated = published_date
                existing_bill.full_text = bill_text
            else:
                new_bill = Bill(number=bill_number, summary=summary, sponsor=sponsor, last_updated=published_date, full_text=bill_text)
                db.session.add(new_bill)
        
    db.session.commit()
    print(f"Updated bills from RSS feed at {datetime.now()}")
''')

    # Create templates
    create_file('app/templates/base.html', '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}NH Bill Tracker{% endblock %}</title>
    <!-- Materialize CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <!-- Material Icons -->
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    {% block styles %}{% endblock %}
</head>
<body>
    <nav class="blue" role="navigation">
        <div class="nav-wrapper container">
            <a href="{{ url_for('main.index') }}" class="brand-logo">NH Bill Tracker</a>
            <ul class="right hide-on-med-and-down">
                <li><a href="{{ url_for('main.index') }}">Home</a></li>
                {% if current_user.is_anonymous %}
                    <li><a href="{{ url_for('auth.login') }}">Login</a></li>
                    <li><a href="{{ url_for('auth.register') }}">Register</a></li>
                {% else %}
                    <li><a href="{{ url_for('auth.logout') }}">Logout</a></li>
                {% endif %}
            </ul>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
            <div class="card-panel teal lighten-2">{{ message }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <!-- Materialize JavaScript -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
''')

    create_file('app/templates/index.html', '''
{% extends "base.html" %}

{% block content %}
    <h1>New Hampshire Bills</h1>
    <div class="row">
        {% for bill in bills.items %}
            <div class="col s12 m6">
                <div class="card blue-grey darken-1">
                    <div class="card-content white-text">
                        <span class="card-title">{{ bill.number }}</span>
                        <p>{{ bill.summary[:100] }}...</p>
                    </div>
                    <div class="card-action">
                        <a href="{{ url_for('main.bill_detail', bill_number=bill.number) }}">View Details</a>
                    </div>
                </div>
            </div>
        {% endfor %}
    </div>
    <ul class="pagination">
        {% for page in bills.iter_pages() %}
            {% if page %}
                {% if page != bills.page %}
                    <li class="waves-effect"><a href="{{ url_for('main.index', page=page) }}">{{ page }}</a></li>
                {% else %}
                    <li class="active"><a href="#">{{ page }}</a></li>
                {% endif %}
            {% else %}
                <li class="disabled"><a href="#">...</a></li>
            {% endif %}
        {% endfor %}
    </ul>
{% endblock %}
''')

    create_file('app/templates/bill_detail.html', '''
{% extends "base.html" %}

{% block content %}
    <h1>Bill {{ bill.number }}</h1>
    <div class="card">
        <div class="card-content">
            <span class="card-title">Summary</span>
            <p>{{ bill.summary }}</p>
        </div>
        <div class="card-action">
            <p><strong>Sponsor:</strong> {{ bill.sponsor }}</p>
            <p><strong>Last Updated:</strong> {{ bill.last_updated.strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </div>
    </div>
    <div class="card">
        <div class="card-content">
            <span class="card-title">Full Text</span>
            <pre>{{ bill.full_text }}</pre>
        </div>
    </div>
{% endblock %}
''')

    for template in ['login.html', 'register.html']:
        create_file(f'app/templates/auth/{template}', '''
{% extends "base.html" %}

{% block content %}
    <h1>{{ title }}</h1>
    <!-- Add your authentication form here -->
{% endblock %}
''')

    # Create config.py
    create_file('config.py', '''
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BILLS_PER_PAGE = 20
''')

    # Create run.py
    create_file('run.py', '''
from app import create_app, db
from app.models import User, Bill

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Bill': Bill}

if __name__ == '__main__':
    app.run(debug=True)
''')

    # Create .env file
    create_file('.env', '''
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
''')

     # Install requirements
    run_in_venv("pip install -r requirements.txt")

    # Initialize the database
    run_in_venv("flask db init")
    run_in_venv("flask db migrate -m 'Initial migration.'")
    run_in_venv("flask db upgrade")

    print("\nProject setup complete!")
    print("\nTo run the application:")
    print(f"1. Activate the virtual environment:")
    if sys.platform == "win32":
        print(f"   .\\venv\\Scripts\\activate")
    else:
        print(f"   source venv/bin/activate")
    print("2. Run the application: python run.py")
    print("\nThe application will be available at http://localhost:5000")
    print("\nTo update bills from the RSS feed, run the following in a Python shell:")
    print("from app import create_app")
    print("from app.bill_tracker import update_bills_from_rss")
    print("app = create_app()")
    print("with app.app_context():")
    print("    update_bills_from_rss()")

if __name__ == "__main__":
    setup_project()