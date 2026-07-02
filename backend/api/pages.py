from flask import Blueprint, render_template, session, redirect, url_for
from backend.utils.validators import login_required

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def home():
    return render_template('home.html', user=session.get('username'))


@pages_bp.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('pages.prediction'))
    return render_template('login.html')


@pages_bp.route('/register')
def register():
    if 'user_id' in session:
        return redirect(url_for('pages.prediction'))
    return render_template('register.html')


@pages_bp.route('/prediction')
@login_required
def prediction():
    return render_template('prediction.html', username=session.get('full_name'))


@pages_bp.route('/route-recommendation')
@login_required
def route_recommendation():
    return render_template('route_recommendation.html', username=session.get('full_name'))


@pages_bp.route('/travel-history')
@login_required
def travel_history():
    return render_template('travel_history.html', username=session.get('full_name'))


@pages_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=session.get('full_name'))


@pages_bp.route('/forgot-password')
def forgot_password():
    if 'user_id' in session:
        return redirect(url_for('pages.prediction'))
    return render_template('forgot_password.html')





@pages_bp.route('/weekly-report')
@login_required
def weekly_report():
    return render_template('weekly_report.html', username=session.get('full_name'))


@pages_bp.route('/commute-planner')
@login_required
def commute_planner():
    return render_template('commute_planner.html', username=session.get('full_name'))
