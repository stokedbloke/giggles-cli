# 🎭 Giggles - AI-Powered Laughter Tracker

Giggles is a secure, AI-powered web application that automatically detects and tracks your daily laughter using audio analysis from the Limitless AI Pendant API.

## Features

- 🎤 **Automatic Laughter Detection**: Uses YAMNet AI model to analyze audio and detect laughter events
- 🔒 **Secure Authentication**: Email/password authentication with Supabase Auth
- 🔐 **Encrypted Storage**: API keys are encrypted using AES-256-GCM
- 📊 **Daily Dashboard**: View laughter counts and summaries by day
- 🎵 **Audio Playback**: Listen to detected laughter clips
- 🗑️ **Data Management**: Delete detections and manage your data
- 📱 **Mobile-Responsive**: Works seamlessly on desktop and mobile devices

## Tech Stack

- **Backend**: Python 3.9+ with FastAPI
- **Frontend**: Vanilla JavaScript (ES6+)
- **Authentication**: Supabase Auth with JWT
- **Database**: Supabase (PostgreSQL with Row Level Security)
- **AI Model**: YAMNet (TensorFlow Hub)
- **API Integration**: Limitless AI Pendant API
- **Encryption**: AES-256-GCM

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Supabase account and project
- Limitless AI Pendant API key
- 8GB RAM recommended for TensorFlow workloads
- 2GB RAM is sufficient in production when audio is processed in 30-minute chunks

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/giggles-cli.git
cd giggles-cli
```

### 2. Set Up Python Virtual Environment

```bash
cd laughter-detector
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the `laughter-detector` directory:

```bash
cp env.example .env
```

Edit `.env` with your actual values:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Database
DATABASE_URL=your_postgresql_connection_string

# Encryption
ENCRYPTION_KEY=your_64_character_hex_key

# JWT
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256

# YAMNet Model
YAMNET_MODEL_URL=https://tfhub.dev/google/yamnet/1
```

**Important**: Generate a secure encryption key:

```python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Set Up Database

Run the database setup script in your Supabase SQL editor:

```bash
cat setup_database.sql
```

Copy and paste the SQL into your Supabase SQL editor and run it.

### 6. Run the Application

```bash
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

The application will be available at `http://localhost:8001`

## Usage

### First Time Setup

1. Navigate to `http://localhost:8001` in your browser
2. Create an account with email and password
3. Enter your Limitless AI Pendant API key
4. Click "Update Today's Count" to process audio

### Daily Usage

- View your daily laughter summary on the main dashboard
- Click on any day to see detailed laughter detections
- Listen to audio clips of detected laughter
- Add notes to laughter detections
- Delete individual detections or all data

## Operational Notes

- **Chunk size matters**: The Limitless API downloads are processed in 30-minute chunks. Larger windows risk OOM kills on small VPS instances.
- **Limitless 404s are normal**: A `404` from `/v1/download-audio` simply means the pendant has no audio for that window. The app logs the skip and moves on.
- **Supabase clients**: All Supabase access is centralized via `src/services/supabase_client.py` so that RLS policies and HTTPX proxy patches are consistently applied.
- **Dependency pins**: `cryptography==41.0.7`, `httpx==0.25.2`, and `supabase==2.4.0` are required together (the `src/utils/httpx_patch.py` shim allows `proxy` kwargs).

## Project Structure

```
giggles-cli/
├── laughter-detector/
│   ├── src/
│   │   ├── api/              # FastAPI routes
│   │   ├── auth/             # Authentication logic
│   │   ├── config/           # Configuration
│   │   ├── models/           # Pydantic models
│   │   └── services/         # Business logic
│   ├── static/               # Frontend assets
│   ├── templates/            # HTML templates
│   ├── uploads/              # Audio files (gitignored)
│   ├── requirements.txt      # Python dependencies
│   ├── setup_database.sql    # Database schema
│   └── main.py              # Application entry point
├── docs/                     # Documentation
├── examples/                 # Example files
├── PRPs/                     # Project requirement plans
└── README.md                # This file
```

## Security Features

- **Row Level Security (RLS)**: Database-level access control
- **JWT Authentication**: Secure token-based authentication
- **Encrypted API Keys**: All sensitive data encrypted at rest
- **HTTPS Ready**: Can be deployed with SSL/TLS
- **No Client-Side Secrets**: All sensitive operations on server

## API Endpoints

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user
- `GET /daily-summary` - Get daily laughter summaries
- `GET /laughter-detections/{date}` - Get detections for date
- `POST /process-daily-audio` - Manually trigger audio processing
- `DELETE /laughter-detections/{id}` - Delete a detection
- `DELETE /user-data` - Delete all user data

## Deployment

See `docs/deployment.md` for deployment instructions to various platforms.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- YAMNet by Google for audio classification
- Limitless AI for the wearable microphone API
- Supabase for authentication and database hosting

## Support

For issues and questions, please open an issue on GitHub.
