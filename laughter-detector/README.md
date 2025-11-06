# 🎭 Giggles - Laughter Detector and Counter

A secure web application that processes audio from Limitless AI pendant to detect and count laughter using YAMNet, with encrypted storage and mobile-responsive UI.

## 📊 Complete User Flow

For a comprehensive visual diagram of the entire application flow (authentication, processing, UI interactions), see [User Flow Diagram](./docs/USER_FLOW_DIAGRAM.md).

## Features

- 🔐 **Secure Authentication**: Email/password authentication with MFA via Supabase
- 🎵 **Audio Processing**: YAMNet-based laughter detection from Limitless AI audio
- 🔒 **Encrypted Storage**: AES-256-GCM encryption for API keys and sensitive data
- 📱 **Mobile-First UI**: Dead simple responsive design for maximum compatibility
- 🧹 **Secure Cleanup**: Cryptographic file deletion and orphaned file cleanup
- 🔄 **Automated Processing**: Nightly audio processing with incremental updates
- 📊 **Daily Analytics**: Track laughter patterns with timestamps and probabilities

## Security Features

- **Encrypted API Keys**: All Limitless API keys are encrypted with AES-256-GCM
- **Secure File Deletion**: Cryptographic deletion of audio files after processing
- **Row-Level Security**: Supabase RLS policies for user data isolation
- **Input Validation**: Comprehensive validation and sanitization of all inputs
- **Rate Limiting**: API rate limiting to prevent abuse
- **MFA Support**: Multi-factor authentication enabled by default

## Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Authentication**: Supabase Auth with JWT tokens
- **Database**: Supabase PostgreSQL with RLS
- **AI/ML**: TensorFlow Hub YAMNet model
- **Audio Processing**: librosa, soundfile
- **Frontend**: Vanilla JavaScript with mobile-responsive CSS
- **Encryption**: cryptography library with AES-256-GCM
- **Testing**: pytest with comprehensive test coverage

## Installation

### Prerequisites

- Python 3.11 or higher
- Supabase account and project
- Limitless AI pendant with API access
- Docker (optional, for containerized deployment)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd laughter-detector
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Supabase Configuration
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
   
   # Security Configuration
   SECRET_KEY=your_secret_key_for_jwt_tokens_here
   ENCRYPTION_KEY=your_32_byte_encryption_key_here
   
   # Database Configuration
   DATABASE_URL=postgresql://user:password@localhost:5432/laughter_detector
   
   # Application Configuration
   DEBUG=False
   HOST=0.0.0.0
   PORT=8000
   ```

5. **Database Setup**
   ```bash
   # Create database tables (SQLAlchemy models will be created automatically)
   python -c "from src.models import *; print('Models imported successfully')"
   ```

6. **Run the application**
   ```bash
   python -m uvicorn src.main:app --reload
   ```

The application will be available at `http://localhost:8000`.

## Usage

### User Registration and Authentication

1. **Register Account**: Create an account with email and strong password
2. **Enable MFA**: Multi-factor authentication is enabled by default
3. **Login**: Sign in with your credentials

### Limitless API Key Setup

1. **Get API Key**: Obtain your Limitless AI pendant API key
2. **Store Securely**: Enter your API key (it will be encrypted and stored securely)
3. **Validation**: The system validates your API key before storing

### Daily Laughter Tracking

1. **Automatic Processing**: Audio is processed nightly for the previous day
2. **View Daily Summary**: See daily laugh counts on bright, colorful cards
3. **Detailed View**: Click on any day to see individual laughter detections
4. **Audio Playback**: Listen to laughter clips with timestamps and probabilities
5. **Add Notes**: Add personal notes to laughter detections
6. **Filter Results**: Filter detections by probability threshold

### Data Management

1. **Individual Deletion**: Delete specific laughter detections
2. **Daily Cleanup**: Delete all data for a specific day
3. **Complete Reset**: Delete all data and API key
4. **Secure Deletion**: All deletions use cryptographic file deletion

## API Documentation

The application provides a REST API with the following endpoints:

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login

### Limitless API Key Management
- `POST /api/api/limitless-key` - Store encrypted API key
- `DELETE /api/api/limitless-key` - Delete API key and data

### Audio Processing
- `POST /api/api/process-daily-audio` - Process daily audio

### Laughter Detection
- `GET /api/api/daily-summary` - Get daily laughter summaries
- `GET /api/api/laughter-detections/{date}` - Get detections for specific date
- `PUT /api/api/laughter-detections/{id}` - Update detection notes
- `DELETE /api/api/laughter-detections/{id}` - Delete detection

### Data Management
- `DELETE /api/api/user-data` - Delete all user data

### Health Check
- `GET /api/health` - Application health status

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_auth.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
python -m black src/ tests/

# Check linting
python -m ruff check src/ tests/

# Type checking
python -m mypy src/

# Security scan
python -m bandit -r src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Deployment

### Docker Deployment

1. **Build Docker image**
   ```bash
   docker build -t laughter-detector .
   ```

2. **Run container**
   ```bash
   docker run -p 8000:8000 --env-file .env laughter-detector
   ```

### Production Deployment

1. **Set up reverse proxy** (nginx recommended)
2. **Configure SSL/TLS** certificates
3. **Set up monitoring** and logging
4. **Configure backup** for database
5. **Set up automated cleanup** jobs

### Security Considerations

- Use strong encryption keys (32 bytes for AES-256)
- Enable HTTPS in production
- Configure proper CORS policies
- Set up rate limiting
- Monitor for suspicious activity
- Regular security updates

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_KEY` | Supabase anon key | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `ENCRYPTION_KEY` | AES-256 encryption key (32 bytes) | Required |
| `LAUGHTER_THRESHOLD` | YAMNet laughter detection threshold | 0.3 |
| `AUDIO_SAMPLE_RATE` | Audio sample rate for processing | 16000 |
| `CLIP_DURATION` | Duration of extracted clips (seconds) | 4.0 |

### YAMNet Configuration

The application uses TensorFlow Hub's YAMNet model for laughter detection. Key configuration options:

- **Laughter Classes**: 139 (Laughter), 140 (Chuckle), 141 (Giggle)
- **Threshold**: Minimum probability for laughter detection (default: 0.3)
- **Audio Format**: 16kHz mono WAV files
- **Processing**: Real-time inference with timestamp extraction

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Connection**: Check Supabase credentials and network access
3. **Audio Processing**: Verify audio file formats and permissions
4. **Encryption Errors**: Ensure encryption key is exactly 32 bytes
5. **API Rate Limits**: Check Limitless API usage limits

### Logs

Application logs are written to stdout. For production deployment, configure proper logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Performance Optimization

- Use connection pooling for database connections
- Implement caching for frequently accessed data
- Optimize audio processing with batch operations
- Use CDN for static assets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Add unit tests for new features
- Use meaningful variable names

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information
4. Contact the development team

## Changelog

### Version 1.0.0
- Initial release
- Secure authentication with Supabase
- YAMNet-based laughter detection
- Mobile-responsive UI
- Encrypted storage and secure deletion
- Comprehensive test coverage

## Acknowledgments

- [TensorFlow Hub](https://tfhub.dev/) for YAMNet model
- [Supabase](https://supabase.com/) for authentication and database
- [Limitless AI](https://www.limitless.ai/) for audio data API
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
