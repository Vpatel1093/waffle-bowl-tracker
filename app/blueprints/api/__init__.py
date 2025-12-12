"""API blueprint for HTMX endpoints."""
from flask import Blueprint

api = Blueprint('api', __name__)

from app.blueprints.api import routes
