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

# Application-level singleton services (initialized once, not per-request)
_yahoo_service = None


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

    # Initialize application-level singleton services
    def get_yahoo_service():
        """Get the singleton YahooService instance."""
        global _yahoo_service
        if _yahoo_service is None:
            from app.services.yahoo_service import YahooService
            _yahoo_service = YahooService()
        return _yahoo_service

    # Make service available to request context
    @app.before_request
    def setup_services():
        """Attach singleton service instances to request context."""
        from flask import g
        g.yahoo_service = get_yahoo_service()

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    @app.shell_context_processor
    def make_shell_context():
        from app.services.yahoo_service import YahooService
        # Initialize it so it's ready to use
        return {
            'YahooService': YahooService,
            'y': YahooService()
        }

    return app
