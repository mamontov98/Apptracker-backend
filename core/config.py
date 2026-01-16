import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server Configuration
# Vercel doesn't use HOST/PORT - it handles routing automatically
# Using 0.0.0.0 allows connections from any IP (needed for Vercel)
HOST = os.getenv('HOST', '0.0.0.0')
# Vercel will handle the port, but we keep this for local dev
PORT = int(os.getenv('PORT', 5000))

# Environment Configuration
ENV = os.getenv('ENV', 'development')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# MongoDB Configuration
# For development, default to local MongoDB if MONGO_URI is not set
# For production, MONGO_URI must be set
if ENV == 'production':
    MONGO_URI = os.getenv('MONGO_URI')
    if not MONGO_URI:
        raise ValueError("MONGO_URI must be set in production environment")
else:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')

MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'analytics')
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', 5000))
MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv('MONGO_SERVER_SELECTION_TIMEOUT_MS', 5000))

