from flask import Blueprint, jsonify, request
from datetime import datetime
from core.db import get_db
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
import uuid

projects_bp = Blueprint('projects', __name__)


def generate_project_key():
    """Generate a unique, short project key"""
    # Generate UUID and take first 12 characters
    return uuid.uuid4().hex[:12]


@projects_bp.route('/v1/projects', methods=['POST'])
def create_project():
    """Create a new project
    ---
    tags:
      - Projects
    parameters:
      - in: body
        name: body
        description: Project creation request
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              description: Project name
              example: Demo App
    responses:
      200:
        description: Project created successfully
        schema:
          type: object
          properties:
            name:
              type: string
              example: Demo App
            projectKey:
              type: string
              example: a1b2c3d4e5f6
            createdAt:
              type: string
              format: date-time
              example: "2024-01-15T10:30:00Z"
            isActive:
              type: boolean
              example: true
      400:
        description: Invalid request
        schema:
          type: object
          properties:
            error:
              type: string
              example: "name is required"
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Database connection failed"
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        # Validate name
        name = data.get('name')
        if not name:
            return jsonify({"error": "name is required"}), 400
        
        # Get database and collection
        db = get_db()
        collection = db['projects']
        
        # Generate unique project key
        project_key = generate_project_key()
        
        # Check if key already exists (very unlikely, but safe)
        max_attempts = 5
        attempts = 0
        while collection.find_one({"projectKey": project_key}) and attempts < max_attempts:
            project_key = generate_project_key()
            attempts += 1
        
        # Create project document
        project_doc = {
            "name": name,
            "projectKey": project_key,
            "createdAt": datetime.utcnow(),
            "isActive": True
        }
        
        # Insert project
        result = collection.insert_one(project_doc)
        
        # Return project (without MongoDB _id or convert it to string)
        return jsonify({
            "name": project_doc["name"],
            "projectKey": project_doc["projectKey"],
            "createdAt": project_doc["createdAt"].isoformat() + "Z",
            "isActive": project_doc["isActive"]
        }), 200
        
    except DuplicateKeyError:
        return jsonify({
            "error": "Project key already exists, please try again"
        }), 500
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error creating project: {str(e)}"
        }), 500


@projects_bp.route('/v1/projects', methods=['GET'])
def get_projects():
    """Get all projects
    ---
    tags:
      - Projects
    parameters:
      - in: query
        name: limit
        type: integer
        description: Maximum number of projects to return
        required: false
      - in: query
        name: projectKey
        type: string
        description: Filter by specific project key
        required: false
    responses:
      200:
        description: List of projects
        schema:
          type: object
          properties:
            projects:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                    example: Demo App
                  projectKey:
                    type: string
                    example: a1b2c3d4e5f6
                  createdAt:
                    type: string
                    format: date-time
                    example: "2024-01-15T10:30:00Z"
                  isActive:
                    type: boolean
                    example: true
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Database connection failed"
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', type=int)
        project_key = request.args.get('projectKey')
        
        # Get database and collection
        db = get_db()
        collection = db['projects']
        
        # Build query - filter by projectKey if provided
        query = {}
        if project_key:
            query["projectKey"] = project_key
        
        cursor = collection.find(query)
        
        # Apply limit if provided
        if limit and limit > 0:
            cursor = cursor.limit(limit)
        
        # Convert to list and format
        projects = []
        for project in cursor:
            # Format createdAt safely
            created_at = project.get("createdAt")
            if created_at:
                if isinstance(created_at, datetime):
                    created_at_str = created_at.isoformat() + "Z"
                else:
                    created_at_str = str(created_at)
            else:
                created_at_str = None
            
            projects.append({
                "name": project.get("name"),
                "projectKey": project.get("projectKey"),
                "createdAt": created_at_str,
                "isActive": project.get("isActive", True)
            })
        
        return jsonify({
            "projects": projects
        }), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error fetching projects: {str(e)}"
        }), 500

