from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from core.config import HOST, PORT, DEBUG
from routes import register_routes
from core.db import init_db, create_indexes

app = Flask(__name__)

# Enable CORS for frontend 
if DEBUG:
    CORS(app, origins="*")
else:
    CORS(app, origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # Add production frontend URLs 
        "https://apptracker-frontend-gvcqjfrtt-dani-mamontovs-projects.vercel.app",
        "https://apptracker-frontend.vercel.app",
        "https://*.vercel.app",
    ]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

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
    "basePath": "/",
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Register all routes
register_routes(app)

# Root route - redirect to Swagger UI or return API info
@app.route('/', methods=['GET'])
def root():
    # Root endpoint - redirects to Swagger UI
    from flask import redirect
    return redirect('/swagger', code=302)

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG)

