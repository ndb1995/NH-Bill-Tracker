from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_superuser = db.Column(db.Boolean, default=False)
    tracked_bills = db.relationship(
        'Bill', secondary='user_bills', backref='trackers')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), index=True, unique=True)
    session_year = db.Column(db.String(4))
    title = db.Column(db.Text)
    summary = db.Column(db.Text)
    sponsor = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    general_status = db.Column(db.String(200))
    house_status = db.Column(db.String(200))
    senate_status = db.Column(db.String(200))
    full_text = db.Column(db.Text)
    html_link = db.Column(db.String(300))
    category = db.Column(db.String(50), index=True)
    docket_link = db.Column(db.String(300))

    next_hearing = db.relationship(
        'Hearing', uselist=False, back_populates='bill')
    docket_entries = db.relationship(
        'DocketEntry', back_populates='bill', order_by='desc(DocketEntry.date)')

    def __repr__(self):
        return f'<Bill {self.number}>'


class Hearing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
    committee = db.Column(db.String(100))
    date = db.Column(db.Date)
    time = db.Column(db.String(20))
    location = db.Column(db.String(100))

    bill = db.relationship('Bill', back_populates='next_hearing')


class DocketEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'))
    date = db.Column(db.Date)
    chamber = db.Column(db.String(10))
    action = db.Column(db.Text)

    bill = db.relationship('Bill', back_populates='docket_entries')


# Association table for User-Bill many-to-many relationship
user_bills = db.Table('user_bills',
                      db.Column('user_id', db.Integer, db.ForeignKey(
                          'user.id'), primary_key=True),
                      db.Column('bill_id', db.Integer, db.ForeignKey(
                          'bill.id'), primary_key=True)
                      )


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
