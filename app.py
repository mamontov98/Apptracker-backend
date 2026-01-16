from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from core.config import HOST, PORT, DEBUG
from routes import register_routes
from core.db import init_db, create_indexes

app = Flask(__name__)

# Enable CORS for frontend and Android
# Note: Android apps don't use CORS (direct HTTP requests), but we allow all origins in development
# In production, update this list to include your deployed frontend URLs
if DEBUG:
    CORS(app, origins="*")
else:
    # TODO: Update these URLs to match your deployed frontend domains
    CORS(app, origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # Add your production frontend URLs here:
        # "https://apptracker-dashboard.vercel.app",
        # "https://apptracker-frontend.netlify.app",
        # "https://dashboard.apptracker.com",
    ])

# Initialize MongoDB connection
init_db()

# Create indexes on startup
create_indexes()

# Initialize Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Analytics Backend API",
        "description": "API documentation for Analytics Backend",
        "version": "1.0.0"
    },
    "host": f"{HOST}:{PORT}",
    "basePath": "/",
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Register all routes
register_routes(app)

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG)

