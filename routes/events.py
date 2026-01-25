from flask import Blueprint, jsonify, request
from datetime import datetime
from core.db import get_db
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, WriteError

events_bp = Blueprint('events', __name__)


@events_bp.route('/v1/events/batch', methods=['POST'])
def batch_events():
    """Batch events endpoint - receives and stores analytics events
    ---
    tags:
      - Events
    parameters:
      - in: body
        name: body
        description: Batch events request
        required: true
        schema:
          type: object
          required:
            - projectKey
            - events
          properties:
            projectKey:
              type: string
              description: Project identifier
              example: my-project-key
            events:
              type: array
              description: Array of events to store
              items:
                type: object
                required:
                  - eventName
                  - timestamp
                properties:
                  eventName:
                    type: string
                    example: page_view
                  timestamp:
                    type: string
                    format: date-time
                    description: ISO 8601 timestamp
                    example: "2024-01-15T10:30:00Z"
                  anonymousId:
                    type: string
                    example: "anon-12345"
                  userId:
                    type: string
                    example: "user-67890"
                  sessionId:
                    type: string
                    example: "session-abc123"
                  properties:
                    type: object
                    description: Additional event properties
                    example: {"page": "/home", "referrer": "google.com"}
                  processName:
                    type: string
                    description: Process/flow name (max 128 chars, required if processId is provided)
                    example: "checkout"
                    maxLength: 128
                  processId:
                    type: string
                    description: Unique process instance identifier (max 256 chars, requires processName and processStep)
                    example: "proc-12345"
                    maxLength: 256
                  processStep:
                    type: string
                    description: Process step - "START" or "END" (required if processId is provided)
                    enum: ["START", "END"]
                    example: "START"
    responses:
      200:
        description: Events processed successfully
        schema:
          type: object
          properties:
            received:
              type: integer
              example: 3
            inserted:
              type: integer
              example: 2
      400:
        description: Invalid request
        schema:
          type: object
          properties:
            error:
              type: string
              example: "projectKey is required"
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
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        # Validate projectKey
        project_key = data.get('projectKey')
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Validate events array
        events = data.get('events')
        if not events:
            return jsonify({"error": "events array is required"}), 400
        
        if not isinstance(events, list):
            return jsonify({"error": "events must be an array"}), 400
        
        # Initialize counters
        received_count = len(events)
        inserted_count = 0
        
        # Get database and collection
        db = get_db()
        collection = db['events']
        
        # Process each event
        valid_events = []
        for event in events:
            # Validate required fields
            if not isinstance(event, dict):
                continue
            
            event_name = event.get('eventName')
            timestamp = event.get('timestamp')
            
            # Skip if required fields are missing
            if not event_name or not timestamp:
                continue
            
            # Validate process fields: if processId exists, processName and processStep must exist
            process_id = event.get('processId')
            process_name = event.get('processName')
            process_step = event.get('processStep')
            
            if process_id:
                # If processId is provided, validate that processName and processStep are also provided
                if not process_name or not process_step:
                    continue  # Skip invalid event (missing required process fields)
                
                # Validate processStep is "START" or "END"
                if process_step not in ['START', 'END']:
                    continue  # Skip invalid processStep
                
                # Validate max lengths
                if len(process_name) > 128:
                    continue  # Skip if processName too long
                if len(process_id) > 256:
                    continue  # Skip if processId too long
            
            # Create document to insert
            event_doc = {
                "projectKey": project_key,
                "eventName": event_name,
                "timestamp": timestamp,
                "receivedAt": datetime.utcnow(),
            }
            
            # Add optional fields if present
            if 'anonymousId' in event:
                event_doc['anonymousId'] = event['anonymousId']
            
            if 'userId' in event:
                event_doc['userId'] = event['userId']
            
            if 'sessionId' in event:
                event_doc['sessionId'] = event['sessionId']
            
            if 'properties' in event and isinstance(event['properties'], dict):
                event_doc['properties'] = event['properties']
            
            # Add process fields if present
            if process_name:
                event_doc['processName'] = process_name
            if process_id:
                event_doc['processId'] = process_id
            if process_step:
                event_doc['processStep'] = process_step
            
            valid_events.append(event_doc)
        
        # Insert valid events to MongoDB
        if valid_events:
            result = collection.insert_many(valid_events)
            inserted_count = len(result.inserted_ids)
        
        return jsonify({
            "received": received_count,
            "inserted": inserted_count
        }), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except WriteError as e:
        return jsonify({
            "error": f"Database write error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error processing events: {str(e)}"
        }), 500

