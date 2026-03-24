# Setup Guide

## Prerequisites
- **Python**: 3.10+
- **Node.js**: 18+

## Environment Variables
Create a `.env` file in the root directory and add the following keys:
```env
PINECONE_API_KEY=your_pinecone_key
GROQ_API_KEY=your_groq_key
# Optional, if utilizing anthropic fallback
ANTHROPIC_API_KEY=your_anthropic_key
PINECONE_INDEX=clauseai
```

## Installation & Running

1. **Backend Setup**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   
   # Start the FastAPI server
   python src/api.py
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.
