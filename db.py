from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import (
    MONGO_URI,
    MONGO_DB_NAME,
    MONGO_CONNECT_TIMEOUT_MS,
    MONGO_SERVER_SELECTION_TIMEOUT_MS
)

# Global MongoDB client instance
_client = None


def init_db():
    """Initialize MongoDB connection"""
    global _client
    if _client is None:
        _client = MongoClient(
            MONGO_URI,
            connectTimeoutMS=MONGO_CONNECT_TIMEOUT_MS,
            serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS
        )
    return _client


def get_db():
    """Get MongoDB database instance"""
    if _client is None:
        init_db()
    return _client[MONGO_DB_NAME]


def close_db():
    """Close MongoDB connection"""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def create_indexes():
    """Create MongoDB indexes on application startup"""
    try:
        db = get_db()
        
        # Indexes for projects collection
        projects_collection = db['projects']
        # Unique index on projectKey
        projects_collection.create_index("projectKey", unique=True)
        
        # Indexes for events collection
        events_collection = db['events']
        # Index on projectKey + receivedAt (for internal ingestion monitoring)
        events_collection.create_index([("projectKey", 1), ("receivedAt", -1)])
        # Index on projectKey + eventName + receivedAt (for internal ingestion monitoring)
        events_collection.create_index([("projectKey", 1), ("eventName", 1), ("receivedAt", -1)])

        # Indexes used by reports (filter by event timestamp - stored as ISO string)
        events_collection.create_index([("projectKey", 1), ("timestamp", 1)])
        events_collection.create_index([("projectKey", 1), ("eventName", 1), ("timestamp", 1)])
        
    except Exception as e:
        # Log error but don't fail startup
        print(f"Warning: Failed to create indexes: {str(e)}")

