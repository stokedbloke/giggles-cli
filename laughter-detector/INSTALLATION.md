# 🚀 Installation Guide - Giggles

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Supabase account (free tier available)

## Step-by-Step Installation

### 1. Install Python and pip (if not already installed)

**macOS:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**Windows:**
- Download Python from [python.org](https://python.org)
- Make sure to check "Add Python to PATH" during installation

### 2. Run the Setup Script

```bash
cd laughter-detector
python3 setup.py
```

This script will:
- ✅ Check Python version compatibility
- ✅ Verify pip is available
- ✅ Create necessary directories
- ✅ Generate secure encryption keys
- ✅ Create .env configuration file
- ✅ Install all required dependencies

### 3. Set Up Supabase

#### 3.1 Create Supabase Account
1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub or email

#### 3.2 Create New Project
1. Click "New Project"
2. Choose your organization
3. Enter project details:
   - **Name**: `giggles`
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to your location
4. Click "Create new project"

#### 3.3 Get API Credentials
1. Go to **Settings → API** in your Supabase dashboard
2. Copy these values:
   - **Project URL** (starts with `https://`)
   - **anon public** key
   - **service_role** key (keep this secret!)

#### 3.4 Set Up Database Tables
1. Go to **SQL Editor** in your Supabase dashboard
2. Click "New Query"
3. Copy and paste the contents of `setup_database.sql`
4. Click "Run" to execute the script

### 4. Configure Environment

Edit your `.env` file with your Supabase credentials:

```env
# Replace these with your actual Supabase values
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_public_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Update database URL with your password
DATABASE_URL=postgresql://postgres:your_password@db.your-project-id.supabase.co:5432/postgres
```

### 5. Start the Application

```bash
python3 -m uvicorn src.main:app --reload
```

### 6. Access the Application

Open your browser and go to: **http://localhost:8000**

## Troubleshooting

### "command not found: pip"

**macOS:**
```bash
# Try python3 -m pip instead
python3 -m pip install -r requirements.txt
```

**Ubuntu/Debian:**
```bash
sudo apt install python3-pip
```

**Windows:**
```bash
# Try python -m pip instead
python -m pip install -r requirements.txt
```

### "ModuleNotFoundError: No module named 'fastapi'"

This means dependencies aren't installed. Run:
```bash
python3 -m pip install -r requirements.txt
```

### Database Connection Issues

1. Check your `.env` file has correct Supabase credentials
2. Verify your Supabase project is active
3. Ensure you've run the `setup_database.sql` script

### Port Already in Use

If port 8000 is busy, use a different port:
```bash
python3 -m uvicorn src.main:app --reload --port 8001
```

## Verification

To verify everything is working:

1. **Check the application loads**: Visit http://localhost:8000
2. **Check API health**: Visit http://localhost:8000/api/health
3. **Try registration**: Create a test account
4. **Check Supabase**: Verify user appears in Supabase Auth

## Next Steps

Once the application is running:

1. **Register an account** with email and password
2. **Add your Limitless API key** (get this from your Limitless AI pendant)
3. **Wait for nightly processing** or trigger manual processing
4. **View your daily laughter summaries**

## Security Notes

- 🔐 Keep your `.env` file secure and never commit it to version control
- 🔐 Your Supabase service role key is sensitive - keep it secret
- 🔐 The encryption keys in `.env` are generated securely - don't change them
- 🔐 Use strong passwords for your Supabase database

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify all steps were completed correctly
3. Check the application logs for error messages
4. Ensure your Supabase project is active and accessible
