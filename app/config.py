"""Flask application configuration."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Yahoo OAuth (Shared Authentication)
    YAHOO_CLIENT_ID = os.getenv('YAHOO_CLIENT_ID')
    YAHOO_CLIENT_SECRET = os.getenv('YAHOO_CLIENT_SECRET')
    YAHOO_REDIRECT_URI = os.getenv('YAHOO_REDIRECT_URI', 'https://localhost:8080/auth/callback')
    YAHOO_ACCESS_TOKEN = os.getenv('YAHOO_ACCESS_TOKEN')
    YAHOO_REFRESH_TOKEN = os.getenv('YAHOO_REFRESH_TOKEN')

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # Caching
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300

    # Rate Limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "200 per hour"

    # League Configuration
    LEAGUE_ID = os.getenv('LEAGUE_ID')
    WAFFLE_BOWL_TEAMS = int(os.getenv('WAFFLE_BOWL_TEAMS', 6))
    CACHE_LIVE_SCORES = int(os.getenv('CACHE_LIVE_SCORES', 30))  # seconds


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
