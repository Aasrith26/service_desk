# 🚀 Render Deployment Guide for Service Desk

This repository contains **two services** that need to be deployed separately on Render:

1.  **API Server** (`server.py`): Handles the Dashboard, Flutter App API, and Admin Database.
2.  **Voice Service** (`voice_service.py`): Handles the AI Voice Agent via WebSocket (Exotel/Twilio).

---

## 🛠️ Step 1: Deploy the API Server

1.  Log in to [Render Dashboard](https://dashboard.render.com).
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository: `service_desk`.
4.  Configure the service:
    *   **Name:** `service-desk-api` (or similar)
    *   **Branch:** `working`
    *   **Runtime:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables:**
    *   `DATABASE_URL`: `postgresql://...` (Your Railway Public PostgreSQL URL)
    *   `PYTHON_VERSION`: `3.11.0` (Recommended)

6.  **Deploy!**
    *   **URL:** `https://service-desk-api.onrender.com`
    *   **Use this URL for:** Flutter Frontend (`API_BASE_URL`)

---

## 🎙️ Step 2: Deploy the Voice Service

1.  Go back to Render Dashboard.
2.  Click **New +** -> **Web Service** (AGIAN, using the SAME repository).
3.  Connect the SAME GitHub repository: `service_desk`.
4.  Configure the service:
    *   **Name:** `service-desk-voice` (distinct name)
    *   **Branch:** `working`
    *   **Runtime:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn voice_service:app --host 0.0.0.0 --port $PORT`
        *   *(Note: different start command pointing to `voice_service:app`)*
5.  **Environment Variables:**
    *   `DATABASE_URL`: `postgresql://...` (Same as above)
    *   `AZURE_REALTIME_ENDPOINT`: `wss://...`
    *   `AZURE_API_KEY`: `...`
    *   `EXOTEL_API_KEY` / `EXOTEL_API_TOKEN`: (If used)
    *   `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`: (If used)

6.  **Deploy!**
    *   **URL:** `https://service-desk-voice.onrender.com`
    *   **Get WebSocket URL:** replace `https://` with `wss://` and add `/stream/exotel`
    *   **Final WS URL:** `wss://service-desk-voice.onrender.com/stream/exotel`

---

## 🔗 Final Configuration

### Update Exotel
Go to Exotel Dashboard -> App Settings.
*   **WebSocket URL:** `wss://service-desk-voice.onrender.com/stream/exotel`

### Update Frontend
Rebuild Flutter web app with the **API Server** URL:
```bash
flutter build web --dart-define=API_BASE_URL=https://service-desk-api.onrender.com
```
