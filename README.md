# ScholarMind — Local Setup Guide

## What This Is
A full-stack academic intelligence platform for researchers and professors.
- Upload papers/theses → Claude reads and reviews them
- Manage students and track their progress
- Track and write grants with AI assistance
- Dashboard showing all urgent tasks and deadlines

## Quick Start

### 1. Install Python dependencies
```bash
pip install fastapi uvicorn sqlalchemy aiosqlite anthropic python-multipart aiofiles "python-jose[cryptography]" "passlib[bcrypt]" pymupdf python-docx pydantic-settings httpx
```

### 2. Get your Anthropic API key
- Go to https://console.anthropic.com
- Create an account and get an API key
- It costs ~$0.003 per paper analysis (very cheap)

### 3. Run the app
```bash
export ANTHROPIC_API_KEY=your-key-here
bash start.sh
```
Or on Windows:
```cmd
set ANTHROPIC_API_KEY=your-key-here
cd backend
python main.py
```

### 4. Open in browser
Go to: http://localhost:8000

Login with: demo@mcgill.ca / demo1234
(or register your own account)

## Features

### 📄 Papers
- Upload any PDF (journal articles, theses, grant proposals)
- Upload supplementary materials alongside
- Set due dates for reviews
- Claude extracts full text automatically

### ✍️ Review Studio
- Claude analyzes the full paper automatically
- Generates: summary, major concerns, minor concerns
- Auto-checklist: multiple testing, power, ethics, etc.
- Scores: novelty, methodology, clarity, statistics
- Chat with Claude about any aspect of the paper
- Export finished review as Word document (.docx)

### 🎓 Students
- Track all your students in one place
- Progress bars, thesis status, notes
- Record meeting dates — get alerts for overdue check-ins
- Add milestones and track completion
- Generate AI follow-up emails with one click

### 💰 Grants
- Track your own grants (deadlines, status, drafts)
- Find opportunities: Claude suggests relevant grants (CIHR, NSERC, NIH, etc.)
- Grant Writing Studio: Claude writes any section (aims, significance, approach, etc.)
- Track status: identified → drafting → submitted → awarded

### 📊 Dashboard
- All urgent tasks in one place
- Overdue reviews highlighted in red
- Upcoming grant deadlines
- Students with no recent check-in

## File Structure
```
scholarmind/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── auth.py              # JWT authentication
│   ├── models/
│   │   └── database.py      # SQLite database + all models
│   ├── routers/
│   │   ├── auth_router.py
│   │   ├── papers_router.py
│   │   ├── reviews_router.py
│   │   ├── students_grants_router.py
│   │   └── dashboard_router.py
│   ├── services/
│   │   └── claude_service.py  # All Claude API calls
│   └── uploads/               # Uploaded PDFs stored here
├── frontend/
│   └── index.html             # Complete single-file frontend
├── start.sh                   # Startup script
└── README.md
```

## Database
Uses SQLite locally (file: `backend/scholarmind.db`)
- No setup needed — created automatically on first run
- To reset: delete `scholarmind.db` and restart

## API Documentation
When running, visit: http://localhost:8000/docs
(Swagger UI with all endpoints)

## Moving to Cloud (when ready)
Replace SQLite with PostgreSQL, host on AWS:
- Frontend: AWS Amplify or Vercel (~$0/month)
- Backend: AWS EC2 t3.small (~$15/month)
- Database: AWS RDS PostgreSQL (~$15/month)
- Files: AWS S3 (~$5/month)
- Total: ~$35/month → charge universities $20k/year

## Cost per User
- Claude API: ~$0.003 per paper analysis
- 100 papers/month per user = ~$0.30/month in API costs
- Very profitable at any subscription price
