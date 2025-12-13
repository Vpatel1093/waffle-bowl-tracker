"""Flask application factory."""
from flask import Flask, render_template
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_htmx import HTMX

from app.config import config

# Initialize extensions
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
htmx = HTMX()


def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    cache.init_app(app)
    limiter.init_app(app)
    htmx.init_app(app)

    # Register blueprints
    from app.blueprints.main import main as main_blueprint
    from app.blueprints.api import api as api_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # Cache service instances
    @app.before_request
    def setup_services():
        """Initialize cached service instances for this request."""
        from flask import g
        if not hasattr(g, 'yahoo_service'):
            from app.services.yahoo_service import YahooService
            g.yahoo_service = YahooService()

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    return app
