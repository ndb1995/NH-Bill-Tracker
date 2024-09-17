from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, login_required
from flask import redirect, url_for, flash, Markup, current_app, render_template
from app.extensions import db
from app.models import User, Bill
from app.bill_tracker import update_bills
from flask_wtf import FlaskForm
import logging


class SuperuserModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_superuser

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))


class BillModelView(SuperuserModelView):
    column_list = ('number', 'summary', 'sponsor',
                   'last_updated', 'status', 'html_link')
    column_searchable_list = ('number', 'summary', 'sponsor', 'full_text')
    column_filters = ('last_updated', 'status')
    column_formatters = {
        'html_link': lambda v, c, m, p: Markup(f'<a href="{m.html_link}" target="_blank">View Bill</a>')
    }


class UpdateBillsForm(FlaskForm):
    pass  # We don't need any fields, just CSRF protection


class UpdateBillsView(BaseView):
    @expose('/')
    @login_required
    def index(self):
        current_app.logger.info(
            f"User {current_user.username} accessed UpdateBillsView index")
        if not current_user.is_superuser:
            current_app.logger.warning(
                f"Non-superuser {current_user.username} attempted to access UpdateBillsView")
            flash('You must be a superuser to access this page.', 'error')
            return redirect(url_for('admin.index'))
        form = UpdateBillsForm()
        return self.render('admin/update_bills.html', form=form)

    @expose('/update', methods=['POST'])
    @login_required
    def update_bills(self):
        form = UpdateBillsForm()
        if form.validate_on_submit():
            current_app.logger.info(
                f"User {current_user.username} attempted to update bills")
            if not current_user.is_superuser:
                current_app.logger.warning(
                    f"Non-superuser {current_user.username} attempted to update bills")
                flash('You must be a superuser to update bills.', 'error')
                return redirect(url_for('admin.index'))
            new_bills, updated_bills = update_bills()
            flash(
                f'Added {new_bills} new bills and updated {updated_bills} bills.', 'success')
        else:
            flash('CSRF token is missing or invalid', 'error')
        return redirect(url_for('admin.index'))


def init_admin(admin):
    admin.add_view(ModelView(Bill, db.session))
    admin.add_view(UpdateBillsView(
        name='Update Bills', endpoint='update_bills'))
