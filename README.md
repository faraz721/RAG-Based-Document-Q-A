# RAG Based Document Q&A

Upload documents and ask questions about them. Answers are generated using **RAG (Retrieval-Augmented Generation)** so the AI responds from *your* file content, not from random knowledge.

**Supported files:** PDF · DOC · DOCX · TXT

---

## What this project does

1. You upload one or more documents  
2. The app extracts text, creates embeddings, and stores them in FAISS  
3. You select **one** document for Q&A  
4. You ask a question in the chat  
5. Relevant chunks are retrieved **only from that document** and sent to a Groq LLM  
6. You get a clear, structured answer in the chat  

Ideal for resumes, research papers, notes, manuals, and study material.

---

## Features

- Upload PDF, DOC, DOCX, TXT  
- Select one document at a time for questions  
- Multi-document delete with confirmation  
- WhatsApp-style chat (user on the right, AI on the left)  
- Structured AI answers (summary, steps, key points, etc.)  
- Light and dark theme  
- Session-based temporary files (auto-cleanup after inactivity)  
- Fully responsive UI  
- Groq API key stays on the server only  

---

## Tech stack

| Part | Technology |
|------|------------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python, Flask |
| Embeddings | Sentence Transformers |
| Vector DB | FAISS |
| LLM | Groq API |

---

## Project structure

```text
rag-based-document-qa/
├── backend/
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── rag/
│   └── utils/
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── data/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Requirements

- Python 3.10 or higher  
- pip  
- A free [Groq API key](https://console.groq.com/)  

---

## Local setup

### 1. Open the project folder

```powershell
cd path\to\rag-based-document-qa
```

### 2. Create and activate virtual environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install packages

```powershell
pip install -r requirements.txt
pip install "httpx>=0.25.0,<0.28.0"
```

### 4. Configure environment

```powershell
copy .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b
FLASK_SECRET_KEY=change-this-secret
MAX_UPLOAD_SIZE_MB=20
SESSION_TTL_MINUTES=45
```

### 5. Run the app

```powershell
python backend/app.py
```

Open in browser: **http://127.0.0.1:5000**

---

## How to use

1. Click the **+** button and upload a document  
2. Select the document with the radio button  
3. Type your question and press Enter  
4. Use the sun/moon icon to switch light/dark theme  
5. Open **About** for project info and GitHub link  

---

## Sessions (temporary storage)

- Each browser has its own session  
- Your uploaded files are only visible in your session  
- After inactive time (`SESSION_TTL_MINUTES`, default 45), files are removed automatically  
- Other users cannot see your documents  

---

## Deploy on Render

1. Push this project to GitHub (**do not** commit `.env`)  
2. On [Render](https://render.com), create a **Web Service**  
3. **Build command:** `pip install -r requirements.txt`  
4. **Start command:** `gunicorn -w 1 -b 0.0.0.0:$PORT backend.app:app`  
5. Add environment variables in the Render dashboard:
   - `GROQ_API_KEY`
   - `GROQ_MODEL`
   - `FLASK_SECRET_KEY`
   - `SESSION_TTL_MINUTES`  

### Optional: reduce sleep with UptimeRobot

Create a free monitor at [UptimeRobot](https://uptimerobot.com):

- Type: HTTP(s)  
- URL: `https://YOUR-APP.onrender.com/health`  
- Interval: 5 minutes  

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Unexpected keyword `proxies` | Run `pip install "httpx>=0.25.0,<0.28.0"` |
| Invalid API key | Check `GROQ_API_KEY` in `.env` |
| Model not found | Set a valid `GROQ_MODEL` from Groq docs |
| Empty document | Use a text-based PDF (not image-only scan) |
| Port already in use | Stop the other app or change the port |

---

## License

Free for learning and personal use.
