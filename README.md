# Clinic Voice Assistant - Backend

A voice-enabled AI assistant for clinic appointment management. Built with FastAPI, Azure GPT-Realtime, and integrated with Exotel for voice calls and Twilio for WhatsApp notifications.

## 🏗️ Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Exotel Call   │────▶│  Voice Service   │────▶│ Azure GPT-RT    │
│   (WebSocket)   │◀────│  (FastAPI WS)    │◀────│ (Realtime AI)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  Dashboard API   │
                        │  (FastAPI REST)  │
                        └──────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐        ┌──────────────┐
            │   SQLite DB  │        │ Twilio WA    │
            │ (clinic.db)  │        │ Notifications│
            └──────────────┘        └──────────────┘
```

## 📋 Features

- **Voice AI Assistant**: Natural language appointment booking in English & Telugu
- **Exotel Integration**: Voice calls via WebSocket streaming
- **Dashboard API**: REST endpoints for frontend dashboard
- **Token/Queue System**: Patient queue management with token numbers
- **WhatsApp Notifications**: Appointment confirmations via Twilio
- **Multi-clinic Support**: Handle multiple clinics and doctors

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Azure OpenAI account with GPT-Realtime deployment
- Exotel account (for voice calls)
- Twilio account (for WhatsApp - optional)
- ngrok (for local development tunneling)

### 1. Clone the Repository

```bash
git clone https://github.com/Aasrith26/service_desk.git
cd service_desk
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Azure GPT-Realtime Configuration
AZURE_API_KEY=your_azure_api_key_here
AZURE_HOST=your-resource-name.openai.azure.com
AZURE_DEPLOYMENT=gpt-realtime
AZURE_API_VERSION=2024-10-01-preview

# Optional: Full WebSocket endpoint (overrides above)
# AZURE_REALTIME_ENDPOINT=wss://your-endpoint.openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=gpt-realtime

# Twilio WhatsApp (Optional)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Debug
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 5. Initialize the Database

```bash
# Seed sample clinic data
python db/seed_sample_clinic.py
```

### 6. Start the Services

**Option A: Run Both Services Together**
```bash
python main.py
```

**Option B: Run Services Separately**
```bash
# Terminal 1 - Dashboard API (port 8000)
python server.py

# Terminal 2 - Voice Service (port 8001)
python voice_service.py
```

### 7. Expose to Internet (for Exotel)

```bash
# Start ngrok tunnel
ngrok http 8001
```

Copy the ngrok URL (e.g., `https://abc123.ngrok-free.dev`) and configure it in Exotel:
- Applet: **Voicebot** (bidirectional streaming)
- WebSocket URL: `wss://abc123.ngrok-free.dev/stream/exotel`

---

## 📁 Project Structure

```
clinic_voice_assistant/
├── config/
│   └── settings.py          # Configuration and environment variables
├── core/
│   ├── routers/
│   │   └── dashboard_router.py  # Dashboard API endpoints
│   ├── services/
│   │   ├── token_service.py     # Token/queue management
│   │   ├── whatsapp_service.py  # Twilio WhatsApp integration
│   │   └── cached_clinic_service.py
│   ├── database.py           # Database operations
│   ├── db_engine.py          # SQLModel engine
│   ├── models_sql.py         # Database models
│   ├── realtime_client.py    # Azure GPT-Realtime client
│   ├── exotel_bridge.py      # Exotel WebSocket handler
│   └── context_retriever.py  # AI context builder
├── db/
│   ├── seed_sample_clinic.py # Sample data seeder
│   └── init_postgres.py      # PostgreSQL migration (optional)
├── server.py                 # Dashboard API server (port 8000)
├── voice_service.py          # Voice WebSocket server (port 8001)
├── main.py                   # Combined entry point
├── requirements.txt          # Python dependencies
└── .env                      # Environment variables (not in git)
```

---

## 🔌 API Endpoints

Base URL: `http://localhost:8000/dashboard`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Authenticate user |
| GET | `/clinics` | List all clinics |
| GET | `/doctors` | List doctors (filter by clinic_id) |
| GET | `/sessions` | Get clinic sessions |
| GET | `/stats` | Dashboard statistics |
| GET | `/appointments` | List appointments |
| POST | `/appointments` | Create appointment |
| GET | `/calls` | Get call logs |
| GET | `/queue` | Get queue status |
| POST | `/queue/status` | Update token status |
| POST | `/queue/next` | Call next patient |

> 📖 See `API_CONTRACT.md` in frontend repo for full documentation

---

## 🗄️ Database Models

### Clinic
```python
- id: UUID
- name: str
- phone: str
- address: str
```

### Doctor
```python
- id: UUID
- name: str
- specialization: str
- clinic_id: UUID (FK)
```

### Appointment
```python
- id: UUID
- patient_name: str
- patient_phone: str
- date: str
- estimated_time: datetime
- token_number: int
- status: str (BOOKED, SERVING, VISITED, SKIPPED, NO_SHOW)
- doctor_id: UUID (FK)
- clinic_id: UUID (FK)
```

### ClinicSession
```python
- id: UUID
- name: str (MORNING, EVENING)
- start_time: str
- end_time: str
- clinic_id: UUID (FK)
```

---

## 🎙️ Voice Service Flow

1. **Exotel connects** via WebSocket to `/stream/exotel`
2. **Start event** received with caller phone number
3. **AI greeting** sent to caller
4. **Bidirectional audio streaming**:
   - Caller audio → Azure GPT-Realtime
   - AI response → Exotel → Caller
5. **Function calls** for:
   - `check_slot_availability`
   - `book_appointment`
   - `get_available_slots`
   - `end_call`
6. **WhatsApp confirmation** sent after booking

---

## 🔧 Configuration Options

### Audio Settings (config/settings.py)
```python
AUDIO_SAMPLE_RATE = 24000      # Azure requires 24kHz
AUDIO_CHUNK_SIZE = 512         # Samples per frame
SILENCE_THRESHOLD = 100        # Voice activity detection
```

### WebSocket Settings
```python
WEBSOCKET_TIMEOUT = 30         # Connection timeout
WEBSOCKET_RECONNECT_ATTEMPTS = 3
```

---

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test with sample call
python tests/test_booking_flow.py
```

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG_MODE=false`
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up proper SSL certificates
- [ ] Configure Exotel production webhooks
- [ ] Move to Twilio WhatsApp production (business verification required)
- [ ] Set up monitoring and logging

### Docker (Optional)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8001
CMD ["python", "main.py"]
```

---

## 🤝 Related Repositories

- **Frontend**: [service_desk_frontend](https://github.com/Aasrith26/service_desk_frontend) - Flutter dashboard

---

## 📝 License

MIT License

---

## 👥 Contributors

- Backend & AI: [Your Name]
- Frontend: Aasrith26
