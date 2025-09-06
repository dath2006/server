# Render Deployment Guide

This guide explains how to deploy your FastAPI backend to Render.

## Prerequisites

1. A GitHub account with this repository
2. A Render account (free tier available)

## Deployment Steps

### Option 1: Using Render Blueprint (Recommended)

1. **Fork or push this repository to GitHub**

2. **Go to Render Dashboard**

   - Visit [render.com](https://render.com)
   - Sign up/Login with your GitHub account

3. **Create New Blueprint**

   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file

4. **Configure Environment Variables**

   - Review and update the environment variables in the Render dashboard
   - Update `FRONTEND_URL` to match your frontend domain
   - Add any optional services (Google OAuth, Cloudinary) if needed

5. **Deploy**
   - Click "Apply" to deploy your services
   - Render will create both the web service and PostgreSQL database

### Option 2: Manual Web Service Creation

1. **Create PostgreSQL Database**

   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Choose a name (e.g., `chyrp-lite-db`)
   - Select the free plan
   - Note down the database connection details

2. **Create Web Service**

   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - **Name**: `chyrp-lite-api`
     - **Environment**: `Python 3`
     - **Build Command**: `./build.sh`
     - **Start Command**: `./start.sh`
     - **Plan**: Free

3. **Set Environment Variables**
   ```
   PYTHON_VERSION=3.11
   ENVIRONMENT=production
   DATABASE_URL=<your-postgres-connection-string>
   SECRET_KEY=<generate-a-strong-secret-key>
   FRONTEND_URL=https://your-frontend-domain.onrender.com
   ```

## Important Configuration Notes

### Health Check

The backend includes an automatic self-health-check that calls `/health` every 50 seconds to prevent the service from sleeping on the free tier.

### Database Connection

Make sure to use the internal database URL provided by Render for the `DATABASE_URL` environment variable.

### CORS Configuration

Update the `allowed_origins` in your configuration to include your production frontend domain.

### Production vs Development

The `base_url` for health checks automatically uses `RENDER_EXTERNAL_URL` when deployed on Render.

## Post-Deployment

1. **Run Database Migrations** (if using Alembic)

   ```bash
   # In Render web service shell
   alembic upgrade head
   ```

2. **Test the API**

   - Your API will be available at `https://your-service-name.onrender.com`
   - Test the health endpoint: `https://your-service-name.onrender.com/health`

3. **Monitor Logs**
   - Check the Render dashboard for deployment logs and runtime logs
   - Look for the "Health check successful" messages every 50 seconds

## Troubleshooting

### Common Issues

1. **Build Fails**

   - Check if all dependencies are in `requirements.txt`
   - Verify Python version compatibility

2. **Database Connection Issues**

   - Verify `DATABASE_URL` is correctly set
   - Check if database migrations need to be run

3. **CORS Issues**

   - Update `allowed_origins` in config.py
   - Ensure frontend URL is correctly configured

4. **Health Check Fails**
   - Check if the service URL is accessible
   - Verify the health endpoint returns 200 status

## Free Tier Limitations

- Services sleep after 15 minutes of inactivity (health check prevents this)
- 750 hours per month of runtime
- PostgreSQL database has storage limits

## Scaling

For production use, consider upgrading to paid plans for:

- Always-on services
- More resources
- Better database performance
- Custom domains
