"""Main blueprint routes."""
from flask import render_template, current_app
from app.blueprints.main import main


@main.route('/')
def index():
    """Main dashboard - no login required!"""
    return render_template('main/dashboard.html')


@main.route('/about')
def about():
    """About the Waffle Bowl."""
    return render_template('main/about.html')
