from flask import Blueprint, jsonify, request
from datetime import datetime
from db import get_db
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

reports_bp = Blueprint('reports', __name__)

def _parse_iso_datetime(value, field_name):
    """Parse ISO datetime string. Returns datetime or None."""
    if not value:
        return None, None
    try:
        # Support "Z" timezone
        return datetime.fromisoformat(value.replace('Z', '+00:00')), None
    except ValueError:
        return None, f"Invalid '{field_name}' date format. Use ISO 8601 format"

def _add_timestamp_range_to_pipeline(pipeline, from_date, to_date):
    """
    Add a timestamp (ISO string) range filter to an aggregation pipeline.
    We convert event 'timestamp' to a real date and filter by that.
    Events without a valid timestamp are ignored when range is used.
    """
    if not from_date and not to_date:
        return pipeline

    # Convert the ISO timestamp string to a Date.
    # onError/onNull -> None means invalid/missing timestamps won't match the range.
    pipeline.append({
        "$addFields": {
            "_eventTime": {
                "$dateFromString": {
                    "dateString": "$timestamp",
                    "onError": None,
                    "onNull": None
                }
            }
        }
    })

    match_range = {"_eventTime": {}}
    if from_date:
        match_range["_eventTime"]["$gte"] = from_date
    if to_date:
        match_range["_eventTime"]["$lte"] = to_date

    pipeline.append({"$match": match_range})
    return pipeline

def _get_events_pipeline_base(project_key):
    """Base match stage for events by projectKey."""
    return [{"$match": {"projectKey": project_key}}]


@reports_bp.route('/v1/reports/overview', methods=['GET'])
def overview_report():
    """Get overview report for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
    responses:
      200:
        description: Overview report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: a1b2c3d4e5f6
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
                  example: "2024-01-15T23:59:59Z"
            totalEvents:
              type: integer
              description: Total number of events in the time range
              example: 150
            uniqueUsers:
              type: integer
              description: Number of unique users (based on userId or anonymousId)
              example: 45
            uniqueEventNames:
              type: integer
              description: Number of distinct event types
              example: 8
      400:
        description: Invalid request (missing projectKey)
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
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        
        # Validate projectKey
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
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400

        # Get events collection
        events_collection = db['events']

        # If there is a time range, filter by event timestamp (not receivedAt).
        if from_date or to_date:
            # totalEvents
            total_pipeline = _get_events_pipeline_base(project_key)
            _add_timestamp_range_to_pipeline(total_pipeline, from_date, to_date)
            total_pipeline.append({"$count": "count"})
            total_result = list(events_collection.aggregate(total_pipeline))
            total_events = total_result[0]["count"] if total_result else 0

            # uniqueUsers (prefer userId, fallback to anonymousId)
            users_pipeline = _get_events_pipeline_base(project_key)
            _add_timestamp_range_to_pipeline(users_pipeline, from_date, to_date)
            users_pipeline.append({"$project": {"userId": 1, "anonymousId": 1}})
            user_events = events_collection.aggregate(users_pipeline)

            unique_user_ids = set()
            for event in user_events:
                user_id = event.get('userId') or event.get('anonymousId')
                if user_id:
                    unique_user_ids.add(user_id)
            unique_users = len(unique_user_ids)

            # uniqueEventNames
            names_pipeline = _get_events_pipeline_base(project_key)
            _add_timestamp_range_to_pipeline(names_pipeline, from_date, to_date)
            names_pipeline.append({"$group": {"_id": "$eventName"}})
            unique_event_names_count = len(list(events_collection.aggregate(names_pipeline)))
        else:
            # No range: use all events (do not depend on receivedAt)
            events_filter = {"projectKey": project_key}
            total_events = events_collection.count_documents(events_filter)

            user_events = events_collection.find(events_filter, {"userId": 1, "anonymousId": 1})
            unique_user_ids = set()
            for event in user_events:
                user_id = event.get('userId') or event.get('anonymousId')
                if user_id:
                    unique_user_ids.add(user_id)
            unique_users = len(unique_user_ids)

            unique_event_names = events_collection.distinct("eventName", events_filter)
            unique_event_names_count = len(unique_event_names)
        
        # Build response
        response = {
            "projectKey": project_key,
            "range": {
                "from": from_date_str if from_date_str else None,
                "to": to_date_str if to_date_str else None
            },
            "totalEvents": total_events,
            "uniqueUsers": unique_users,
            "uniqueEventNames": unique_event_names_count
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/top-events', methods=['GET'])
def top_events_report():
    """Get top events report for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: limit
        type: integer
        description: "Maximum number of events to return (default: 10, max: 50)"
        required: false
    responses:
      200:
        description: Top events report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            items:
              type: array
              items:
                type: object
                properties:
                  eventName:
                    type: string
                    example: button_click
                  count:
                    type: integer
                    example: 15
      400:
        description: Invalid request (missing projectKey or invalid limit)
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
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        limit = request.args.get('limit', type=int, default=10)
        
        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400
        
        # Validate limit
        if limit < 1:
            limit = 10
        if limit > 50:
            limit = 50
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400
        
        # Get events collection
        events_collection = db['events']
        
        # Use aggregation pipeline to group by eventName and count
        pipeline = _get_events_pipeline_base(project_key)
        _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
        # Exclude screen_view events from top events
        pipeline.append({"$match": {"eventName": {"$ne": "screen_view"}}})
        pipeline.extend([
            {"$group": {
                "_id": "$eventName",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},  # Sort by count descending
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "eventName": "$_id",
                "count": 1
            }}
        ])
        
        # Execute aggregation
        results = list(events_collection.aggregate(pipeline))
        
        # Build response
        response = {
            "projectKey": project_key,
            "items": results
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/top-screens', methods=['GET'])
def top_screens_report():
    """Get top screens report for a project (most viewed screens)
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: limit
        type: integer
        description: "Maximum number of screens to return (default: 20, max: 100)"
        required: false
    responses:
      200:
        description: Top screens report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            items:
              type: array
              items:
                type: object
                properties:
                  screenName:
                    type: string
                    example: Home
                  count:
                    type: integer
                    example: 250
      400:
        description: Invalid request (missing projectKey or invalid limit)
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
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        limit = request.args.get('limit', type=int, default=20)
        
        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400
        
        # Validate limit
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400
        
        # Get events collection
        events_collection = db['events']
        
        # Build aggregation pipeline
        pipeline = _get_events_pipeline_base(project_key)
        _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
        
        # Filter for screen_view events only
        pipeline.append({"$match": {"eventName": "screen_view"}})
        
        # Extract screen_name from properties
        pipeline.append({
            "$addFields": {
                "screenName": {"$ifNull": ["$properties.screen_name", "Unknown"]}
            }
        })
        
        # Group by screenName and count
        pipeline.extend([
            {"$group": {
                "_id": "$screenName",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},  # Sort by count descending
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "screenName": "$_id",
                "count": 1
            }}
        ])
        
        # Execute aggregation
        results = list(events_collection.aggregate(pipeline))
        
        # Build response
        response = {
            "projectKey": project_key,
            "items": results
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/button-clicks', methods=['GET'])
def button_clicks_report():
    """Get button clicks breakdown report for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: limit
        type: integer
        description: "Maximum number of results to return (default: 20, max: 100)"
        required: false
    responses:
      200:
        description: Button clicks breakdown report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            items:
              type: array
              items:
                type: object
                properties:
                  buttonId:
                    type: string
                    example: view_details
                  buttonText:
                    type: string
                    example: View Details
                  count:
                    type: integer
                    example: 45
      400:
        description: Invalid request
      403:
        description: Project not found or not active
      500:
        description: Server error
    """
    try:
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        limit = request.args.get('limit', type=int, default=20)
        
        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400
        
        # Validate limit
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400
        
        # Get events collection
        events_collection = db['events']
        
        # Build aggregation pipeline
        pipeline = _get_events_pipeline_base(project_key)
        _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
        
        # Filter for button_click events
        pipeline.append({"$match": {"eventName": "button_click"}})
        
        # Extract button_id and button_text from properties
        pipeline.append({
            "$addFields": {
                "buttonId": {"$ifNull": ["$properties.button_id", "unknown"]},
                "buttonText": {"$ifNull": ["$properties.button_text", "Unknown"]}
            }
        })
        
        # Group by buttonId and buttonText, count
        pipeline.extend([
            {"$group": {
                "_id": {
                    "buttonId": "$buttonId",
                    "buttonText": "$buttonText"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "buttonId": "$_id.buttonId",
                "buttonText": "$_id.buttonText",
                "count": 1
            }}
        ])
        
        # Execute aggregation
        results = list(events_collection.aggregate(pipeline))
        
        # Build response
        response = {
            "projectKey": project_key,
            "items": results
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/view-items', methods=['GET'])
def view_items_report():
    """Get view items breakdown report for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: limit
        type: integer
        description: "Maximum number of results to return (default: 20, max: 100)"
        required: false
    responses:
      200:
        description: View items breakdown report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            items:
              type: array
              items:
                type: object
                properties:
                  itemId:
                    type: string
                    example: "1"
                  itemName:
                    type: string
                    example: Laptop
                  count:
                    type: integer
                    example: 25
      400:
        description: Invalid request
      403:
        description: Project not found or not active
      500:
        description: Server error
    """
    try:
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        limit = request.args.get('limit', type=int, default=20)
        
        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400
        
        # Validate limit
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100
        
        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400
        
        # Get events collection
        events_collection = db['events']
        
        # Build aggregation pipeline
        pipeline = _get_events_pipeline_base(project_key)
        _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
        
        # Filter for view_item events
        pipeline.append({"$match": {"eventName": "view_item"}})
        
        # Extract item_id and item_name from properties
        pipeline.append({
            "$addFields": {
                "itemId": {"$ifNull": ["$properties.item_id", "unknown"]},
                "itemName": {"$ifNull": ["$properties.item_name", "Unknown"]}
            }
        })
        
        # Group by itemId and itemName, count
        pipeline.extend([
            {"$group": {
                "_id": {
                    "itemId": "$itemId",
                    "itemName": "$itemName"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "itemId": "$_id.itemId",
                "itemName": "$_id.itemName",
                "count": 1
            }}
        ])
        
        # Execute aggregation
        results = list(events_collection.aggregate(pipeline))
        
        # Build response
        response = {
            "projectKey": project_key,
            "items": results
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/screen-views-by-hour', methods=['GET'])
def screen_views_by_hour_report():
    """Get screen views breakdown by hour for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
    responses:
      200:
        description: Screen views by hour report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            items:
              type: array
              items:
                type: object
                properties:
                  screenName:
                    type: string
                    example: Home
                  hour:
                    type: integer
                    example: 14
                  count:
                    type: integer
                    example: 5
      400:
        description: Invalid request
      403:
        description: Project not found or not active
      500:
        description: Server error
    """
    try:
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        
        # Validate projectKey
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
        
        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400
        
        # Get events collection
        events_collection = db['events']
        
        # Build aggregation pipeline
        pipeline = _get_events_pipeline_base(project_key)
        _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
        
        # Filter for screen_view events
        pipeline.append({"$match": {"eventName": "screen_view"}})
        
        # Convert timestamp to date and extract hour
        pipeline.append({
            "$addFields": {
                "_eventTime": {
                    "$dateFromString": {
                        "dateString": "$timestamp",
                        "onError": None,
                        "onNull": None
                    }
                },
                "screenName": {"$ifNull": ["$properties.screen_name", "Unknown"]}
            }
        })
        
        # Filter out events without valid timestamp
        pipeline.append({"$match": {"_eventTime": {"$ne": None}}})
        
        # Extract hour from timestamp
        pipeline.append({
            "$addFields": {
                "hour": {"$hour": "$_eventTime"}
            }
        })
        
        # Group by screenName and hour, count
        pipeline.extend([
            {"$group": {
                "_id": {
                    "screenName": "$screenName",
                    "hour": "$hour"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.screenName": 1, "_id.hour": 1}},
            {"$project": {
                "_id": 0,
                "screenName": "$_id.screenName",
                "hour": "$_id.hour",
                "count": 1
            }}
        ])
        
        # Execute aggregation
        results = list(events_collection.aggregate(pipeline))
        
        # Build response
        response = {
            "projectKey": project_key,
            "items": results
        }
        
        return jsonify(response), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/events-timeseries', methods=['GET'])
def events_timeseries_report():
    """Get events time series report for a project
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: interval
        type: string
        description: "Time grouping interval: day (default) or hour"
        required: false
    responses:
      200:
        description: Events time series report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            interval:
              type: string
              example: day
            items:
              type: array
              items:
                type: object
                properties:
                  time:
                    type: string
                    example: "2025-01-01"
                  count:
                    type: integer
                    example: 12
      400:
        description: Invalid request (missing projectKey or invalid interval)
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
        # Get query parameters
        project_key = request.args.get('projectKey')
        from_date_str = request.args.get('from')
        to_date_str = request.args.get('to')
        interval = request.args.get('interval', 'day')

        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400

        # Validate interval
        if interval not in ['day', 'hour']:
            return jsonify({"error": "interval must be 'day' or 'hour'"}), 400

        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})

        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403

        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403

        # Parse date range if provided
        from_date, from_err = _parse_iso_datetime(from_date_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_date_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400

        # Group format based on interval
        if interval == 'hour':
            time_format = "%Y-%m-%d %H:00"
        else:
            time_format = "%Y-%m-%d"

        # Get events collection
        events_collection = db['events']

        # Use aggregation pipeline to group by event timestamp and count events
        pipeline = _get_events_pipeline_base(project_key)
        # Always convert timestamp for time series (events without timestamp are ignored)
        pipeline.append({
            "$addFields": {
                "_eventTime": {
                    "$dateFromString": {
                        "dateString": "$timestamp",
                        "onError": None,
                        "onNull": None
                    }
                }
            }
        })

        # Exclude events without timestamp (for time series grouping)
        pipeline.append({"$match": {"_eventTime": {"$ne": None}}})

        # Apply range if provided
        if from_date or to_date:
            match_range = {"_eventTime": {}}
            if from_date:
                match_range["_eventTime"]["$gte"] = from_date
            if to_date:
                match_range["_eventTime"]["$lte"] = to_date
            pipeline.append({"$match": match_range})

        pipeline.extend([
            {"$group": {
                "_id": {
                    "$dateToString": {
                        "format": time_format,
                        "date": "$_eventTime",
                        "timezone": "UTC"
                    }
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$project": {
                "_id": 0,
                "time": "$_id",
                "count": 1
            }}
        ])

        results = list(events_collection.aggregate(pipeline))

        response = {
            "projectKey": project_key,
            "interval": interval,
            "items": results
        }

        return jsonify(response), 200

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/funnel', methods=['POST'])
def funnel_report():
    """Funnel report - how many users reach each step in order
    ---
    tags:
      - Reports
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        description: Funnel request (projectKey + steps + optional from/to)
        required: true
        schema:
          type: object
          required:
            - projectKey
            - steps
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            steps:
              type: array
              description: Ordered list of event names (minimum 2)
              items:
                type: string
              example: ["app_open", "screen_view", "login_success"]
            from:
              type: string
              format: date-time
              description: Start date (filters by event timestamp, ISO 8601, optional)
              example: "2025-01-01T00:00:00Z"
            to:
              type: string
              format: date-time
              description: End date (filters by event timestamp, ISO 8601, optional)
              example: "2025-01-10T00:00:00Z"
    responses:
      200:
        description: Funnel results
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            steps:
              type: array
              items:
                type: object
                properties:
                  eventName:
                    type: string
                    example: app_open
                  users:
                    type: integer
                    example: 10
      400:
        description: Invalid request
        schema:
          type: object
          properties:
            error:
              type: string
              example: "steps must be an array with at least 2 items"
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
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        project_key = data.get('projectKey')
        steps = data.get('steps')
        from_str = data.get('from')
        to_str = data.get('to')

        # Validate projectKey
        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400

        # Validate steps
        if not isinstance(steps, list) or len(steps) < 2:
            return jsonify({"error": "steps must be an array with at least 2 items"}), 400

        # Validate each step is a non-empty string
        clean_steps = []
        for s in steps:
            if isinstance(s, str) and s.strip():
                clean_steps.append(s.strip())
        if len(clean_steps) < 2:
            return jsonify({"error": "steps must contain at least 2 valid event names"}), 400

        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403

        # Parse from/to (optional)
        from_date, from_err = _parse_iso_datetime(from_str, 'from')
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_str, 'to')
        if to_err:
            return jsonify({"error": to_err}), 400

        events_collection = db['events']

        # We process events in time order by event timestamp (not receivedAt).
        pipeline = [
            {"$match": {
                "projectKey": project_key,
                "eventName": {"$in": clean_steps},
            }},
            {"$addFields": {
                "_eventTime": {
                    "$dateFromString": {
                        "dateString": "$timestamp",
                        "onError": None,
                        "onNull": None
                    }
                }
            }},
            # Always ignore events without timestamp for funnel ordering
            {"$match": {"_eventTime": {"$ne": None}}}
        ]

        # Apply range if provided
        if from_date or to_date:
            match_range = {"_eventTime": {}}
            if from_date:
                match_range["_eventTime"]["$gte"] = from_date
            if to_date:
                match_range["_eventTime"]["$lte"] = to_date
            pipeline.append({"$match": match_range})

        pipeline.extend([
            {"$sort": {"_eventTime": 1}},
            {"$project": {"eventName": 1, "userId": 1, "anonymousId": 1}}
        ])

        cursor = events_collection.aggregate(pipeline)

        # For each user, keep "next step index" they need to complete.
        user_progress = {}  # user_key -> next_step_index
        step_users_count = [0] * len(clean_steps)

        for event in cursor:
            # Identify user: prefer userId, fallback to anonymousId
            user_key = event.get("userId") or event.get("anonymousId")
            if not user_key:
                continue

            current_index = user_progress.get(user_key, 0)
            if current_index >= len(clean_steps):
                continue  # user already completed all steps

            if event.get("eventName") == clean_steps[current_index]:
                # User reached the next step in the funnel
                step_users_count[current_index] += 1
                user_progress[user_key] = current_index + 1

        # Build response
        response_steps = []
        for i, name in enumerate(clean_steps):
            response_steps.append({
                "eventName": name,
                "users": step_users_count[i]
            })

        return jsonify({
            "projectKey": project_key,
            "steps": response_steps
        }), 200

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500


@reports_bp.route('/v1/reports/conversion', methods=['GET'])
def conversion_report():
    """Conversion report - conversion rate for a specific event
    ---
    tags:
      - Reports
    parameters:
      - in: query
        name: projectKey
        type: string
        description: Project key (required)
        required: true
      - in: query
        name: eventName
        type: string
        description: Conversion event name (required)
        required: true
      - in: query
        name: from
        type: string
        format: date-time
        description: Start date (filters by event timestamp, ISO 8601, optional)
        required: false
      - in: query
        name: to
        type: string
        format: date-time
        description: End date (filters by event timestamp, ISO 8601, optional)
        required: false
    responses:
      200:
        description: Conversion report
        schema:
          type: object
          properties:
            projectKey:
              type: string
              example: aa26419210ab
            conversionEvent:
              type: string
              example: purchase_success
            range:
              type: object
              properties:
                from:
                  type: string
                  format: date-time
                  example: "2025-01-01T00:00:00Z"
                to:
                  type: string
                  format: date-time
                  example: "2025-01-10T00:00:00Z"
            totalUsers:
              type: integer
              description: Unique users who did at least one event in the range
              example: 100
            convertedUsers:
              type: integer
              description: Unique users who did the conversion event in the range
              example: 12
            conversionRate:
              type: number
              format: float
              description: convertedUsers / totalUsers
              example: 0.12
      400:
        description: Invalid request (missing projectKey or eventName)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "eventName is required"
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
        project_key = request.args.get('projectKey')
        conversion_event = request.args.get('eventName')
        from_str = request.args.get('from')
        to_str = request.args.get('to')

        if not project_key:
            return jsonify({"error": "projectKey is required"}), 400

        if not conversion_event:
            return jsonify({"error": "eventName is required"}), 400

        # Verify project exists and is active
        db = get_db()
        projects_collection = db['projects']
        project = projects_collection.find_one({"projectKey": project_key})
        if not project:
            return jsonify({"error": f"Project with key '{project_key}' not found"}), 403
        if not project.get('isActive', True):
            return jsonify({"error": f"Project '{project_key}' is not active"}), 403

        # Parse from/to (optional) - filter by event timestamp (not receivedAt)
        from_date, from_err = _parse_iso_datetime(from_str, "from")
        if from_err:
            return jsonify({"error": from_err}), 400

        to_date, to_err = _parse_iso_datetime(to_str, "to")
        if to_err:
            return jsonify({"error": to_err}), 400

        events_collection = db['events']

        # Helper pipeline: convert timestamp, apply range, and create userKey
        def build_users_pipeline(extra_match=None):
            pipeline = _get_events_pipeline_base(project_key)
            _add_timestamp_range_to_pipeline(pipeline, from_date, to_date)
            if extra_match:
                pipeline.append({"$match": extra_match})

            # userKey = userId if exists, else anonymousId
            pipeline.append({
                "$addFields": {
                    "_userKey": {"$ifNull": ["$userId", "$anonymousId"]}
                }
            })
            pipeline.append({"$match": {"_userKey": {"$ne": None}}})
            pipeline.append({"$group": {"_id": "$_userKey"}})
            pipeline.append({"$count": "count"})
            return pipeline

        # totalUsers = users who did any event in the range
        total_pipeline = build_users_pipeline()
        total_result = list(events_collection.aggregate(total_pipeline))
        total_users = total_result[0]["count"] if total_result else 0

        # convertedUsers = users who did the conversion event in the range
        converted_pipeline = build_users_pipeline({"eventName": conversion_event})
        converted_result = list(events_collection.aggregate(converted_pipeline))
        converted_users = converted_result[0]["count"] if converted_result else 0

        # conversionRate
        if total_users == 0:
            conversion_rate = 0.0
        else:
            conversion_rate = converted_users / total_users

        return jsonify({
            "projectKey": project_key,
            "conversionEvent": conversion_event,
            "range": {
                "from": from_str if from_str else None,
                "to": to_str if to_str else None
            },
            "totalUsers": total_users,
            "convertedUsers": converted_users,
            "conversionRate": float(conversion_rate)
        }), 200

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "error": f"Database connection error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "error": f"Error generating report: {str(e)}"
        }), 500
