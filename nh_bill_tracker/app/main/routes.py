from flask import render_template, request, current_app, flash, redirect, url_for
from flask_login import current_user, login_required
from app.main import bp
from app.models import Bill, User
from app.extensions import db
from sqlalchemy import func, or_


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


@bp.route('/search')
def search():
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    sponsor = request.args.get('sponsor', '')
    status = request.args.get('status', '')

    bills = Bill.query
    if query:
        bills = bills.filter(or_(Bill.number.contains(query),
                                 Bill.summary.contains(query),
                                 Bill.full_text.contains(query)))
    if category:
        bills = bills.filter(Bill.category == category)
    if sponsor:
        bills = bills.filter(Bill.sponsor.contains(sponsor))
    if status:
        bills = bills.filter(Bill.status == status)

    bills = bills.order_by(Bill.last_updated.desc()).paginate(
        page=request.args.get('page', 1, type=int),
        per_page=20,
        error_out=False
    )

    return render_template('search_results.html', bills=bills, query=query)


@bp.route('/track/<bill_number>')
@login_required
def track_bill(bill_number):
    bill = Bill.query.filter_by(number=bill_number).first_or_404()
    if bill not in current_user.tracked_bills:
        current_user.tracked_bills.append(bill)
        db.session.commit()
        flash(f'You are now tracking Bill {bill_number}', 'success')
    return redirect(url_for('main.bill_detail', bill_number=bill_number))


@bp.route('/untrack/<bill_number>')
@login_required
def untrack_bill(bill_number):
    bill = Bill.query.filter_by(number=bill_number).first_or_404()
    if bill in current_user.tracked_bills:
        current_user.tracked_bills.remove(bill)
        db.session.commit()
        flash(f'You are no longer tracking Bill {bill_number}', 'success')
    return redirect(url_for('main.bill_detail', bill_number=bill_number))


@bp.route('/my-tracked-bills')
@login_required
def tracked_bills():
    return render_template('tracked_bills.html', bills=current_user.tracked_bills)


@bp.route('/bill-categories')
def bill_categories():
    category_counts = db.session.query(Bill.category, func.count(Bill.id)).\
        group_by(Bill.category).all()

    categories = [c[0] for c in category_counts]
    counts = [c[1] for c in category_counts]

    return render_template('bill_categories.html', categories=categories, counts=counts)
