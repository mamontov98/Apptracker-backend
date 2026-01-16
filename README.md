# AppTracker Backend API

Flask-based REST API backend for analytics event tracking and reporting, integrated with MongoDB Atlas.

**🏗️ Standalone Repository** - This is an independent repository that can be deployed to cloud services.

## Features

- **Project Management**: Create and manage analytics projects
- **Event Ingestion**: Batch endpoint for receiving analytics events
- **Reports**: Multiple report types (Overview, Top Events, Time Series, Funnel, Conversion)
- **Swagger Documentation**: Interactive API documentation
- **MongoDB Integration**: Efficient data storage with indexes
- **CORS Support**: Configured for frontend integration

## Tech Stack

- **Flask** 3.0.0 - Web framework
- **pymongo** 4.6.0 - MongoDB driver
- **flasgger** 0.9.7.1 - Swagger/OpenAPI documentation
- **flask-cors** 5.0.0 - Cross-Origin Resource Sharing
- **python-dotenv** 1.0.0 - Environment variable management

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
HOST=127.0.0.1
PORT=5000
ENV=development
DEBUG=True
# For local MongoDB: mongodb://localhost:27017
# For MongoDB Atlas: mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=analytics
MONGO_CONNECT_TIMEOUT_MS=5000
MONGO_SERVER_SELECTION_TIMEOUT_MS=5000
```

## Running the Server

```bash
python app.py
```

The server will start on `http://127.0.0.1:5000`

## API Documentation

### Swagger UI

Interactive API documentation available at:
- `http://127.0.0.1:5000/swagger`

### API Spec (JSON)

- `http://127.0.0.1:5000/apispec.json`

## API Endpoints

### Health & Database

- `GET /health` - Server health check
- `GET /db/health` - MongoDB connection check
- `POST /db/test-insert` - Test MongoDB write operation

### Projects

- `POST /v1/projects` - Create a new project
- `GET /v1/projects` - List all projects (optional `projectKey` filter)

### Events

- `POST /v1/events/batch` - Submit batch of analytics events

### Reports

All reports filter by **event `timestamp`** (not `receivedAt`):

- `GET /v1/reports/overview` - Overview metrics (total events, unique users, unique event names)
- `GET /v1/reports/top-events` - Most frequent events (with optional limit)
- `GET /v1/reports/events-timeseries` - Events over time (day/hour intervals)
- `POST /v1/reports/funnel` - User funnel analysis (step-by-step progression)
- `GET /v1/reports/conversion` - Conversion rate for a specific event

## Quick Start

### 1. Create a Project

```bash
curl -X POST http://127.0.0.1:5000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo App"}'
```

Response:
```json
{
  "name": "Demo App",
  "projectKey": "a1b2c3d4e5f6",
  "createdAt": "2025-01-06T10:00:00Z",
  "isActive": true
}
```

### 2. Send Events

```bash
curl -X POST http://127.0.0.1:5000/v1/events/batch \
  -H "Content-Type: application/json" \
  -d '{
    "projectKey": "a1b2c3d4e5f6",
    "events": [
      {
        "eventName": "app_open",
        "timestamp": "2025-01-06T10:00:00Z",
        "anonymousId": "anon-1"
      },
      {
        "eventName": "purchase_success",
        "timestamp": "2025-01-06T10:05:00Z",
        "anonymousId": "anon-1",
        "userId": "user-123"
      }
    ]
  }'
```

### 3. Get Reports

**Overview:**
```bash
curl "http://127.0.0.1:5000/v1/reports/overview?projectKey=a1b2c3d4e5f6"
```

**Top Events:**
```bash
curl "http://127.0.0.1:5000/v1/reports/top-events?projectKey=a1b2c3d4e5f6&limit=10"
```

**Time Series:**
```bash
curl "http://127.0.0.1:5000/v1/reports/events-timeseries?projectKey=a1b2c3d4e5f6&interval=day&from=2025-01-01T00:00:00Z&to=2025-01-10T00:00:00Z"
```

**Funnel:**
```bash
curl -X POST http://127.0.0.1:5000/v1/reports/funnel \
  -H "Content-Type: application/json" \
  -d '{
    "projectKey": "a1b2c3d4e5f6",
    "steps": ["app_open", "screen_view", "login_success", "purchase_success"],
    "from": "2025-01-01T00:00:00Z",
    "to": "2025-01-10T00:00:00Z"
  }'
```

**Conversion:**
```bash
curl "http://127.0.0.1:5000/v1/reports/conversion?projectKey=a1b2c3d4e5f6&eventName=purchase_success&from=2025-01-01T00:00:00Z&to=2025-01-10T00:00:00Z"
```

## MongoDB Indexes

The following indexes are automatically created on startup:

**Projects Collection:**
- Unique index on `projectKey`

**Events Collection:**
- Compound index on `(projectKey, timestamp)`
- Compound index on `(projectKey, eventName, timestamp)`
- Compound index on `(projectKey, receivedAt)` (for internal monitoring)
- Compound index on `(projectKey, eventName, receivedAt)` (for internal monitoring)

## Project Structure

```
.
├── app.py              # Flask application entry point
├── config.py           # Configuration management
├── db.py               # MongoDB connection and indexes
├── requirements.txt    # Python dependencies
├── routes/
│   ├── __init__.py     # Route registration
│   ├── health.py       # Health check endpoints
│   ├── db.py           # Database test endpoints
│   ├── projects.py     # Project management endpoints
│   ├── events.py       # Event ingestion endpoints
│   └── reports.py      # Report endpoints
└── README.md           # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | `127.0.0.1` |
| `PORT` | Server port | `5000` |
| `ENV` | Environment (development/production) | `development` |
| `DEBUG` | Debug mode | `True` |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` (dev only) |
| `MONGO_DB_NAME` | MongoDB database name | `analytics` |
| `MONGO_CONNECT_TIMEOUT_MS` | Connection timeout | `5000` |
| `MONGO_SERVER_SELECTION_TIMEOUT_MS` | Server selection timeout | `5000` |

**Note:** `MONGO_URI` is required in production. In development, it defaults to local MongoDB if not set.

## 🚀 Cloud Deployment

### Deploy to Heroku

1. **Create a Heroku app:**
   ```bash
   heroku create your-apptracker-backend
   ```

2. **Set environment variables:**
   ```bash
   heroku config:set ENV=production
   heroku config:set DEBUG=False
   heroku config:set MONGO_URI=your_mongodb_atlas_connection_string
   heroku config:set MONGO_DB_NAME=analytics
   ```

3. **Deploy:**
   ```bash
   git push heroku main
   ```

4. **Add Procfile:**
   Create `Procfile` in the root directory:
   ```
   web: gunicorn app:app
   ```

5. **Install gunicorn (add to requirements.txt):**
   ```
   gunicorn==21.2.0
   ```

### Deploy to Railway

1. **Connect your repository to Railway**

2. **Set environment variables in Railway dashboard:**
   - `ENV=production`
   - `DEBUG=False`
   - `MONGO_URI=your_mongodb_atlas_connection_string`
   - `MONGO_DB_NAME=analytics`
   - `PORT` (Railway sets this automatically)

3. **Railway will auto-detect Python and deploy**

### Deploy to Render

1. **Create a new Web Service on Render**

2. **Connect your repository**

3. **Configure:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

4. **Set environment variables:**
   - `ENV=production`
   - `DEBUG=False`
   - `MONGO_URI=your_mongodb_atlas_connection_string`
   - `MONGO_DB_NAME=analytics`

### Deploy to AWS (Elastic Beanstalk)

1. **Install EB CLI:**
   ```bash
   pip install awsebcli
   ```

2. **Initialize:**
   ```bash
   eb init -p python-3.11 apptracker-backend
   ```

3. **Set environment variables:**
   ```bash
   eb setenv ENV=production DEBUG=False MONGO_URI=your_mongodb_atlas_connection_string
   ```

4. **Deploy:**
   ```bash
   eb create apptracker-backend-env
   ```

### CORS Configuration for Cloud

Update `app.py` to allow your frontend domain:

```python
if DEBUG:
    CORS(app, origins="*")
else:
    CORS(app, origins=[
        "https://your-frontend-domain.com",
        "http://localhost:5173"  # For local development
    ])
```

**Important:** Replace `your-frontend-domain.com` with your actual frontend deployment URL.

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing/invalid parameters)
- `403` - Forbidden (project not found or inactive)
- `500` - Internal Server Error

Error responses include a JSON object with an `error` field:

```json
{
  "error": "Project with key 'abc123' not found"
}
```

## Notes

- All reports filter events by their **`timestamp`** field (event time), not `receivedAt` (server reception time)
- Events without a valid `timestamp` are ignored in time-based reports
- The `projectKey` must exist and be active (`isActive=true`) for event ingestion and reports
- Swagger documentation is available at `/swagger` endpoint
