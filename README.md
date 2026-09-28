# TriCoach AI — Architectural Endurance & Triathlon Engine

![TriCoach AI Demo](./demo.gif)

**TriCoach AI** is an intelligent, high-performance AI assistant built for multi-sport athletes (swimming, cycling, running, and triathlon). Built with Google's **Agent Development Kit (ADK)** and deployed on **Agent Platform / Agent Engine**, TriCoach AI combines real-time data lookups, specialized endurance calculations, multi-session memory, multimodal visual and video generation, and rich declarative UI (A2UI).

---

## ⚡ Key Features & Implemented Capabilities

Every capability listed below is fully implemented and active in `app/`:

*   **🏆 Workout Catalog & Firestore Persistence (`app/tools.py`)**:
    *   `list_workouts`: Query structured workouts filtered by discipline (`swimming`, `cycling`, `running`, `brick`).
    *   `get_workout`: Retrieve workout targets, intervals, and difficulty ratings by ID.
    *   `add_workout`: Store custom training sessions dynamically into Google Cloud Firestore.
*   **📊 Heart Rate & Power Zone Calculator (`app/tools.py`)**:
    *   `calculate_training_zones`: Calculates Karvonen HR zones (Zone 1 Recovery to Zone 5 Anaerobic) and 7-zone Coggan Cycling FTP power zones based on athlete metrics.
*   **🌤 Outdoor Training Weather (`app/tools.py`)**:
    *   `get_outdoor_workout_weather`: Fetches live weather conditions (temperature, wind speed, weather codes) via Open-Meteo API to recommend optimal outdoor gear and training safety.
*   **📍 Location & Venue Search (`app/tools.py`)**:
    *   `geocode_address`: Geocodes key endurance hubs (e.g., Kona, Boulder, Nice, San Francisco).
    *   `find_nearby_training_places`: Recommends 50m lap pools, cycling velodromes, and running tracks near target locations.
*   **🎨 Multimodal Visual Generation (`Imagen 3`)**:
    *   `generate_workout_visual`: Generates motivational goal visuals using Google's `imagen-3.0-generate-002`. Saves artifacts locally and uploads generated image bytes directly to a public Google Cloud Storage bucket (`gs://tricoach-ai-media-...`).
*   **🎬 Multimodal Video Generation (`Gemini Omni`)**:
    *   `generate_workout_video`: Generates short workout motion clips using Google's `gemini-omni-flash-preview` on Vertex AI (global region), saving artifacts and returning public Cloud Storage HTTPS URLs.
*   **🧠 Cross-Session Long-Term Memory (`Vertex AI Memory Bank`)**:
    *   Uses `PreloadMemoryTool` and `add_session_to_memory` callbacks to persist athlete preferences, injury histories, dietary restrictions, and allergy constraints across sessions.
*   **💻 Code Sandbox Executor (`AgentEngineSandboxCodeExecutor`)**:
    *   Executes dynamic Python scripts securely within Google Agent Engine's isolated code execution sandbox.
*   **📱 Declarative UI (`A2UI v0.8`)**:
    *   Renders structured responses (cards, columns, rows, images) natively in a custom minimalist monochrome frontend via `a2ui_utils.py`.

---

## 🏗 System Architecture

```
[ Web Browser ]
      │
      │ HTTP / EventStream
      ▼
[ FastAPI Proxy ] (frontend/main.py)
      │
      │ Agent-to-Agent (A2A) Protocol
      ▼
[ Agent Engine Runtime ] (Google Cloud Vertex AI)
      │
      ├─► Gemini 2.5 Flash Model
      ├─► Vertex AI Memory Bank (Long-Term Cross-Session Memory)
      ├─► Google Firestore Database (Workouts & Athlete Profiles)
      ├─► Google Cloud Storage (Media Artifacts)
      ├─► Imagen 3 & Gemini Omni Models (Visuals & Videos)
      └─► Agent Engine Code Execution Sandbox
```

---

## 🚀 Local Setup & Development Instructions

### Prerequisites
*   Python 3.10+
*   Google Cloud SDK (`gcloud` CLI) authenticated with access to a GCP project.
*   Firestore database initialized.

### 1. Clone & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/your-username/tricoach-ai.git
cd tricoach-ai

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install agent dependencies
pip install -r requirements.txt

# Install frontend dependencies
pip install -r frontend/requirements.txt
```

### 2. Environment Variables
Set the required environment variables:
```bash
export GCP_PROJECT="your-gcp-project-id"
export LOCATION="us-east1"
export AGENT_ENGINE_RESOURCE_NAME="projects/YOUR_PROJECT/locations/us-east1/reasoningEngines/YOUR_ENGINE_ID"
export AGENT_DIRECTORY="app"
```

### 3. Run Agent & Frontend Locally
```bash
# Start the FastAPI proxy and web frontend locally
cd frontend
python main.py
```
Open your browser to `http://localhost:8080` (or `http://127.0.0.1:8080`).

---

## ☁ Deployment

### Deploying the Agent to Agent Engine
```bash
agents-cli deploy --service-name tricoach-ai --project $GCP_PROJECT
```

### Deploying the Frontend to Cloud Run
```bash
gcloud run deploy tricoach-ai-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="$AGENT_ENGINE_RESOURCE_NAME",AGENT_DIRECTORY="app"
```

---

## 📜 License
Licensed under the Apache 2.0 License.
