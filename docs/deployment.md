# RupeeRadar — Production Deployment Guide

This guide explains how to build, containerize, run, and deploy the **RupeeRadar** application for production.

---

## 1. Production Architecture Overview

In a development environment, the application runs on two separate ports:
*   **Vite Dev Server (Frontend):** `http://localhost:5173`
*   **FastAPI Dev Server (Backend):** `http://localhost:8000`

For **production deployment**, the frontend assets are compiled into optimized static HTML, CSS, and JS bundles, and served directly by the **FastAPI backend** on a single port (e.g., `8000` or `80`). 

Benefits of single-port serving:
1.  **Simplified Architecture:** Only one container/service needs to be hosted.
2.  **No CORS Issues:** Since frontend and backend share the same origin, browser CORS restrictions do not apply.
3.  **Low Latency:** Assets are loaded from the same server handling database queries.

---

## 2. Environment Variables reference

The application reads configurations from the environment (e.g., variables in Docker or a `.env` file).

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `groq` | Options: `groq` (cloud model), `ollama` (local model), `none` (no AI, rule-only) |
| `GROQ_API_KEY` | *(None)* | Required when `LLM_PROVIDER=groq`. Get one free at [console.groq.com](https://console.groq.com/) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | The cloud LLM model used. |
| `OLLAMA_MODEL` | `llama3.3` | The model name if using Ollama. |
| `OLLAMA_HOST` | *(None)* | Custom Ollama host URL (e.g. `http://host.docker.internal:11434` for Docker). |
| `DB_PATH` | `./data/rupeeradar.db` | Path where the persistent SQLite file will be saved. |
| `FRONTEND_DIST_DIR` | `../frontend/dist` | Path pointing to Vite's static build output directory. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Comma-separated list of additional allowed CORS origins (for development/separate hosting). |
| `MAX_UPLOAD_MB` | `10` | Maximum file size allowed for bank statements. |

---

## 3. Running Production Mode Locally

To run the unified application locally in production mode (without Docker):

### Step 1: Build the Frontend Assets
Compile the React/Vite/TypeScript assets:
```bash
cd frontend
npm install
npm run build
```
This outputs compiled assets to `frontend/dist/`.

### Step 2: Start the Backend Server
Set environment variables and launch the FastAPI server using Uvicorn:
```bash
cd ../backend

# Windows (PowerShell):
$env:FRONTEND_DIST_DIR="../frontend/dist"
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000

# macOS / Linux (Terminal):
export FRONTEND_DIST_DIR="../frontend/dist"
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open `http://localhost:8000` in your web browser. You will see the React dashboard loaded directly from the FastAPI server.

---

## 4. Containerized Deployments with Docker

### Using Docker Compose (Recommended for local tests)
We provide a [docker-compose.yml](../docker-compose.yml) file to orchestrate the build, persistent SQLite volume, and variables.

1.  **Configure environment variables:**
    Create or edit a `.env` file in the root workspace folder, setting your api credentials:
    ```env
    LLM_PROVIDER=groq
    GROQ_API_KEY=your_groq_api_key_here
    ```
2.  **Spin up the container:**
    ```bash
    docker compose up --build -d
    ```
3.  **Access the application:**
    Open `http://localhost:8000`.
4.  **Stop the container:**
    ```bash
    docker compose down
    ```

### Building the Docker Image Manually
If you want to build and run the Docker image independently:

```bash
# Build the image
docker build -t rupee-radar:latest .

# Run the container with persistent host database path
docker run -d \
  -p 8000:8000 \
  -v /path/to/host/data:/app/data \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY="your_groq_api_key" \
  --name rupee-radar-instance \
  rupee-radar:latest
```

---

## 5. Deploying to Cloud Platforms

Because RupeeRadar is packaged as a single-port Docker container, you can deploy it to any container hosting service.

### A. Deploying to Render
1.  **Sign in** to [Render](https://render.com/).
2.  Click **New +** and select **Web Service**.
3.  Connect your Git Repository.
4.  Choose **Docker** as the Runtime.
5.  In the service configuration:
    *   Add **Environment Variables**:
        *   `LLM_PROVIDER=groq`
        *   `GROQ_API_KEY=gsk_...`
6.  **SQLite Persistence (Crucial):**
    *   SQLite databases are local files. If you restart a Render container, files are deleted unless you use a Disk.
    *   Scroll down to the **Disks** section in Render.
    *   Add a Disk:
        *   **Name:** `rupeeradar-data`
        *   **Mount Path:** `/app/data`
        *   **Size:** `1 GB` (More than enough for thousands of transactions).
    *   Add an environment variable `DB_PATH=/app/data/rupeeradar.db` to point the database to the mounted disk path.
7.  Click **Deploy Web Service**.

### B. Deploying to Fly.io
Fly.io provides excellent support for containerized systems and persistent volumes.

1.  Install the Fly CLI and log in.
2.  Initialize the app:
    ```bash
    fly launch
    ```
    *Fly will auto-detect the Dockerfile and configure settings.*
3.  Create a persistent volume for the SQLite database:
    ```bash
    fly volumes create rupee_radar_volume --size 1 --region your_region
    ```
4.  Configure the volume mount in `fly.toml`:
    ```toml
    [[mounts]]
      source = "rupee_radar_volume"
      destination = "/app/data"
    ```
5.  Set your secrets:
    ```bash
    fly secrets set GROQ_API_KEY="gsk_..." LLM_PROVIDER="groq" DB_PATH="/app/data/rupeeradar.db"
    ```
6.  Deploy:
    ```bash
    fly deploy
    ```

---

## 6. Database Backups

Because SQLite uses a single file format, backing up your data is extremely simple:
*   **Backup:** Simply copy the `rupeeradar.db` file from the host volume (e.g., `/app/data/rupeeradar.db`) to your backup destination.
*   **Restore:** Copy the backup database file back to the `/app/data/` mount point before booting the container.
