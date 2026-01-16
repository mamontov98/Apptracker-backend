from flask import Blueprint, jsonify
from datetime import datetime
from core.db import get_db
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, WriteError
from core.config import MONGO_DB_NAME

db_bp = Blueprint('db', __name__)


@db_bp.route('/db/health', methods=['GET'])
def db_health_check():
    """Database health check endpoint
    ---
    tags:
      - Database
    responses:
      200:
        description: MongoDB connection is healthy
        schema:
          type: object
          properties:
            mongo:
              type: string
              example: ok
            db:
              type: string
              example: analytics
      500:
        description: MongoDB connection failed
        schema:
          type: object
          properties:
            mongo:
              type: string
              example: error
            message:
              type: string
              example: Connection timeout
    """
    try:
        db = get_db()
        # Ping the database to check connection
        db.client.admin.command('ping')
        return jsonify({
            "mongo": "ok",
            "db": MONGO_DB_NAME
        }), 200
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "mongo": "error",
            "message": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "mongo": "error",
            "message": str(e)
        }), 500


@db_bp.route('/db/test-insert', methods=['POST'])
def test_insert():
    """Test insert endpoint - inserts a test document to MongoDB
    ---
    tags:
      - Database
    responses:
      200:
        description: Document inserted successfully
        schema:
          type: object
          properties:
            inserted:
              type: boolean
              example: true
            collection:
              type: string
              example: connection_tests
            id:
              type: string
              example: 507f1f77bcf86cd799439011
      500:
        description: Insert failed due to connection or permission error
        schema:
          type: object
          properties:
            message:
              type: string
              example: Connection timeout
    """
    try:
        db = get_db()
        collection = db['connection_tests']
        
        # Create test document
        test_doc = {
            "type": "test_insert",
            "createdAt": datetime.utcnow(),
            "note": "first write test"
        }
        
        # Insert document
        result = collection.insert_one(test_doc)
        
        return jsonify({
            "inserted": True,
            "collection": "connection_tests",
            "id": str(result.inserted_id)
        }), 200
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return jsonify({
            "message": f"Connection error: {str(e)}"
        }), 500
    except WriteError as e:
        return jsonify({
            "message": f"Write error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "message": f"Error: {str(e)}"
        }), 500

