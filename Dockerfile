# ==========================================
# Stage 1: Build the React frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy dependency definitions
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend codebase
COPY frontend/ ./

# Compile Vite + TypeScript distribution assets
RUN npm run build

# ==========================================
# Stage 2: Prepare the Python backend runner
# ==========================================
FROM python:3.11-slim AS backend-runner
WORKDIR /app

# Install system dependencies required for WeasyPrint/Cairo PDF compilation
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info && rm -rf /var/lib/apt/lists/*

# Copy backend dependency requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create persistence directory for SQLite database
RUN mkdir -p /app/data

# Copy backend application code
COPY backend/ /app/backend/

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set production environment defaults
ENV PORT=8000
ENV FRONTEND_DIST_DIR=/app/frontend/dist
ENV DB_PATH=/app/data/rupeeradar.db
ENV PYTHONPATH=/app/backend

# Expose server port
EXPOSE 8000

# Start FastAPI application via Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
