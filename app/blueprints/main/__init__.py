"""Main blueprint."""
from flask import Blueprint

main = Blueprint('main', __name__)

from app.blueprints.main import routes
