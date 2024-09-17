import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User


@click.command('create-superuser')
@click.option('--username', prompt=True)
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_superuser(username, email, password):
    user = User(username=username, email=email, is_superuser=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Superuser {username} created successfully.')


@click.command('make-superuser')
@click.option('--email', prompt=True)
@with_appcontext
def make_superuser(email):
    user = User.query.filter_by(email=email).first()
    if user is None:
        click.echo(f'No user found with email {email}')
        return
    user.is_superuser = True
    db.session.commit()
    click.echo(f'User {user.username} is now a superuser.')

# Don't forget to register the new command in your app/__init__.py
# Add this line in the create_app function:
# app.cli.add_command(make_superuser)
