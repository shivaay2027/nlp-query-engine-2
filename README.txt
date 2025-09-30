
NLP Query Engine — Full Demo (Windows-friendly)
===============================================

What's included:
- backend/: FastAPI application implementing required endpoints
- frontend/: single-file HTML/JS UI with database connect, document upload, query input, results, schema view
- requirements.txt
- run_server.bat (Windows helper)
- demo SQLite DB at backend/demo.db pre-populated with several schemas (employees, staff, personnel)
- uploads/ contains a sample resume file

Quick start (Windows):
1. Install Python 3.9+
2. Open Command Prompt in this folder
3. (Optional) python -m venv venv
4. venv\Scripts\activate.bat   (if using venv)
5. pip install -r requirements.txt
6. double-click run_server.bat OR run: uvicorn backend.main:app --reload
7. Open frontend/index.html in your browser (double-click)

Notes & Limitations:
- This demo focuses on engineering requirements in the assignment: dynamic schema discovery, mapping natural language tokens to schema columns, document ingestion+search (with embeddings if sentence-transformers available), caching, ingestion status, and UI features.
- Embeddings require downloading a model; if offline, the system falls back to token overlap search for documents.
- This is a single-machine demo. For production you'd add background workers, persistent vector store, proper auth, and robust monitoring.
- The frontend is plain HTML/JS for maximum compatibility (no Node required).

Files: ['backend', 'frontend', 'requirements.txt', 'run_server.bat', 'uploads']
