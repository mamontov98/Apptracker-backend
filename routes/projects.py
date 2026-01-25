from flask import Blueprint, jsonify, request
from datetime import datetime
from core.db import get_db
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
import uuid

projects_bp = Blueprint('projects', __name__)


def _parse_iso_datetime(value, field_name):
    """Parse ISO datetime string. Returns datetime or None."""
    if not value:
        return None, None
    try:
        # Support "Z" timezone
        return datetime.fromisoformat(value.replace('Z', '+00:00')), None
    except ValueError:
        return None, f"Invalid '{field_name}' date format. Use ISO 8601 format"


def generate_project_key():
    # Generate a unique, short project key
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
        description: Filter by specific project key (takes priority over name)
        required: false
      - in: query
        name: name
        type: string
        description: Filter by project name (only used if projectKey is not provided)
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
        name = request.args.get('name')
        
        # Get database and collection
        db = get_db()
        collection = db['projects']
        
        # Build query - projectKey takes priority over name
        query = {}
        if project_key:
            # Search by projectKey (priority)
            query["projectKey"] = project_key
        elif name:
            # Search by name (only if projectKey is not provided)
            query["name"] = name
        
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


@projects_bp.route('/v1/projects/<project_key>/events/names', methods=['GET'])
def get_event_names(project_key):
    """Get list of distinct event names for a project
    ---
    tags:
      - Projects
    parameters:
      - in: path
        name: project_key
        type: string
        description: Project key
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional, defaults to 30 days ago)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional, defaults to now)
        required: false
    responses:
      200:
        description: List of event names
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: a1b2c3d4e5f6
            eventNames:
              type: array
              items:
                type: string
              example: ["app_open", "screen_view", "login_success", "purchase_success"]
            range:
              type: object
              properties:
                from:
                  type: string
                  format: date-time
                  example: "2024-01-15T00:00:00Z"
                to:
                  type: string
                  format: date-time
                  example: "2024-02-15T23:59:59Z"
      400:
        description: Invalid request
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Invalid date format"
      403:
        description: Project not found or not active
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Project with key 'abc123' not found"
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
        from datetime import timedelta
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Parse date range (default to last 30 days if not provided)
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        
        from_date = None
        to_date = None
        
        if from_date_str:
            from_date, error = _parse_iso_datetime(from_date_str, 'from')
            if error:
                return jsonify({"error": error}), 400
        
        if to_date_str:
            to_date, error = _parse_iso_datetime(to_date_str, 'to')
            if error:
                return jsonify({"error": error}), 400
        
        # Default to last 30 days if no dates provided
        if not from_date and not to_date:
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=30)
        elif not to_date:
            to_date = datetime.utcnow()
        elif not from_date:
            from_date = to_date - timedelta(days=30)
        
        # Build filter for events
        events_collection = db['events']
        events_filter = {"projectKey": project_key}
        
        # Add timestamp range filter if dates provided
        if from_date or to_date:
            # Use aggregation pipeline to filter by timestamp
            pipeline = [
                {"$match": {"projectKey": project_key}},
                {
                    "$addFields": {
                        "_eventTime": {
                            "$dateFromString": {
                                "dateString": "$timestamp",
                                "onError": None,
                                "onNull": None
                            }
                        }
                    }
                },
                {"$match": {"_eventTime": {}}}
            ]
            
            time_filter = {}
            if from_date:
                time_filter["$gte"] = from_date
            if to_date:
                time_filter["$lte"] = to_date
            
            pipeline[2]["$match"]["_eventTime"] = time_filter
            
            # Get distinct event names from filtered pipeline
            pipeline.append({"$group": {"_id": "$eventName"}})
            pipeline.append({"$project": {"_id": 0, "eventName": "$_id"}})
            
            result = list(events_collection.aggregate(pipeline))
            event_names = sorted([item["eventName"] for item in result if item.get("eventName")])
        else:
            # Simple distinct if no date range
            event_names = sorted(events_collection.distinct("eventName", events_filter))
        
        return jsonify({
            "projectKey": project_key,
            "eventNames": event_names,
            "range": {
                "from": from_date.isoformat() + "Z" if from_date else None,
                "to": to_date.isoformat() + "Z" if to_date else None
            }
        }), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error fetching event names: {str(e)}"
        }), 500
