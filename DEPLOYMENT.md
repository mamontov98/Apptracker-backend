# 🚀 Deployment Guide - AppTracker Backend

This guide covers deploying the AppTracker Backend API to various cloud platforms.

## Prerequisites

- MongoDB Atlas account (recommended) or MongoDB instance
- Git repository
- Account on your chosen cloud platform

## 📋 Pre-Deployment Checklist

- [ ] MongoDB Atlas cluster created and connection string ready
- [ ] Environment variables documented
- [ ] CORS configured for your frontend domain
- [ ] All dependencies in `requirements.txt`

## 🎯 Quick Deploy Options

### Heroku

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create apptracker-backend`
4. Set config:
   ```bash
   heroku config:set ENV=production
   heroku config:set DEBUG=False
   heroku config:set MONGO_URI=your_mongodb_atlas_uri
   heroku config:set MONGO_DB_NAME=analytics
   ```
5. Add Procfile: `web: gunicorn app:app`
6. Add gunicorn to requirements.txt: `gunicorn==21.2.0`
7. Deploy: `git push heroku main`

### Railway

1. Connect GitHub repository to Railway
2. Set environment variables:
   - `ENV=production`
   - `DEBUG=False`
   - `MONGO_URI=your_mongodb_atlas_uri`
   - `MONGO_DB_NAME=analytics`
3. Railway auto-detects and deploys

### Render

1. Create new Web Service
2. Connect repository
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app`
5. Set environment variables (same as Railway)

## 🔐 Environment Variables

All platforms require these production variables:

```env
ENV=production
DEBUG=False
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=analytics
```

## 🌐 CORS Configuration

After deployment, update `app.py` CORS settings:

```python
CORS(app, origins=[
    "https://your-frontend-domain.com",
    "https://apptracker-frontend.onrender.com",  # Example
])
```

## ✅ Post-Deployment

1. Test health endpoint: `https://your-api.com/health`
2. Test Swagger: `https://your-api.com/swagger`
3. Create a test project via API
4. Verify MongoDB connection

## 📚 Additional Resources

- [MongoDB Atlas Setup](https://www.mongodb.com/docs/atlas/getting-started/)
- [Heroku Python Guide](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Railway Docs](https://docs.railway.app/)
