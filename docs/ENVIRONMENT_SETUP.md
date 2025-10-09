# Environment Setup

## API Keys and Configuration

All sensitive configuration should be stored in `.env` file at the project root.

**The `.env` file is in `.gitignore` and will NOT be committed to Git.**

## Required Variables

### OpenAI API Key (Required)
```bash
OPENAI_API_KEY=sk-your-openai-key-here
```

### LangSmith API Key (Optional - for monitoring)
```bash
LANGSMITH_API_KEY=lsv2_pt_your-key-here
LANGSMITH_PROJECT=estimai-takeoff
LANGSMITH_TRACING=true
```

Get your LangSmith API key at: https://smith.langchain.com/settings

### Apryse License (Optional - for vector extraction)
```bash
APRYSE_LICENSE_KEY=your-apryse-license-key
```

## Feature Flags

### Detection Mode
```bash
# Use GPT-4o vision (recommended)
ESTIMAI_USE_VISION=1

# Or use Apryse vector extraction + LLM classification
ESTIMAI_USE_VISION=0
APR_USE_APRYSE=1
```

### Other Settings
```bash
ESTIMAI_USE_DEMO=0              # 0=Production, 1=Demo mode
ESTIMAI_TEXT_BACKEND=pymupdf    # pymupdf or pdfnet
ESTIMAI_PIPE_MIN_CONF=0.35      # Confidence threshold
ESTIMAI_DEBUG=0                 # 0=Normal, 1=Verbose logging
ESTIMAI_SEED=42                 # For deterministic LLM calls
```

## Complete .env Example

Create `/Users/williamholt/estimai/.env` with:

```bash
# OpenAI (Required)
OPENAI_API_KEY=sk-your-key-here

# LangSmith (Optional - for monitoring)
LANGSMITH_API_KEY=lsv2_pt_your-key-here
LANGSMITH_PROJECT=estimai-takeoff
LANGSMITH_TRACING=true

# Apryse (Optional)
APRYSE_LICENSE_KEY=your-key-here

# Feature Flags
ESTIMAI_USE_VISION=1
APR_USE_APRYSE=0
ESTIMAI_USE_DEMO=0
ESTIMAI_TEXT_BACKEND=pymupdf
ESTIMAI_PIPE_MIN_CONF=0.35
ESTIMAI_DEBUG=0
ESTIMAI_SEED=42

# Database
DATABASE_URL=sqlite:///./estimai.db

# CORS
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

## Verifying Setup

### Check if variables are loaded:
```bash
cd /Users/williamholt/estimai
source backend/.venv/bin/activate
python -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
python -c "import os; print('LANGSMITH_API_KEY:', 'SET' if os.getenv('LANGSMITH_API_KEY') else 'NOT SET')"
```

### Test LangSmith connection:
```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-key
./scripts/run_benchmarks.sh
```

Then check https://smith.langchain.com to see your traces!

## Security Notes

- ✅ `.env` is in `.gitignore` - safe from Git
- ✅ Never commit API keys to code
- ✅ Use environment variables for all secrets
- ✅ Share `.env.example` (without real keys) with team
- ⚠️ Don't log API keys in application logs
- ⚠️ Rotate keys if accidentally exposed
