## UniHub

UniHub is a full-stack reference platform that lets students upload academic documents, explore curated resources, and leverage built-in AI tooling for summarization, keyword extraction, and quiz generation. The backend is powered by FastAPI, MongoDB (Beanie ODM) for document content, and Microsoft SQL Server (via aioodbc) for user accounts. The frontend is a static SPA served from `public/` with vanilla JavaScript modules for auth, search, quiz, exploration, and profile management.

### Features
- Document lifecycle: authenticated users upload PDFs with rich metadata, browse by university/course, preview with PDF.js, and download original assets.
- Community signals: voting and commenting with per-user tracking stored in MongoDB collections (Votes, Comments, Favorites, Downloads).
- AI workflows: PDF processing pipelines generate summaries, keywords, and interactive quizzes using bespoke generators defined in `make_quiz.py`, `summarizer.py`, and `keywords.py`.
- Quiz experience: users configure question count, review auto-generated content, take quizzes in a modal experience, and see score analytics.
- Account management: registration/login, JWT-based auth, profile editing (including avatar uploads), password changes, and dark-mode preferences.

### Tech Stack
- Backend: FastAPI, Uvicorn, Beanie, Motor, aioodbc/pyodbc, passlib, python-jose.
- Datastores: MongoDB (`UniHub_Courses` for documents & interactions) and SQL Server (`users` table for identities).
- Frontend: Static HTML (`public/*.html`), CSS (`public/css/styles.css`), JS modules (`public/js/*.js`) plus PDF.js CDN for previews.

### Prerequisites
- Python 3.10+ (matching `venv` already checked in).
- MongoDB and Microsoft SQL Server instances. Update connection settings via environment variables (`SQL_SERVER_*`, `MONGO_CONNECTION_STRING`) or `.env`.
- Optional: `PyPDF2` or `pdfplumber` for PDF parsing; install both for best coverage.

### Local Setup
1. **Clone & virtual env**
   ```bash
   git clone https://github.com/namviet157/UniHub.git
   cd UniHub
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   Add optional extras as needed:
   ```bash
   pip install PyPDF2 pdfplumber
   ```
3. **Configure environment**
   - `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
   - `MONGO_CONNECTION_STRING`, `DB_NAME`
   - `SQL_SERVER_HOST`, `SQL_SERVER_PORT`, `SQL_SERVER_USER`, `SQL_SERVER_PASSWORD`, `SQL_SERVER_DATABASE`, `SQL_SERVER_DRIVER`
   You can export them or use a `.env` loader before launching FastAPI.
4. **Create storage directories**
   - Ensure `uploads/` exists and is writable (the app auto-creates but verify permissions).
5. **Run the backend**
   ```bash
   uvicorn app:app --reload
   ```
   The FastAPI server will mount the `public/` directory for static assets and expose JSON APIs (e.g., `/documents/`, `/uploadfile/`, `/api/documents/{id}/comments`, `/auth/login`, `/auth/register`, quiz endpoints, etc.).
6. **Open the frontend**
   Visit `http://localhost:8000` (or your configured host). Pages like `index.html`, `explorer.html`, `upload.html`, and `quiz.html` interact with the API via relative paths.

### Testing & QA
- No automated tests are included yet; exercise critical flows manually:
  - Register/login → verify JWT stored in localStorage.
  - Upload PDF → ensure MongoDB `Courses` collection stores metadata and file saved under `uploads/`.
  - Generate quiz → confirm summarizer/keyword/quizzes appear and quiz modal works end-to-end.
  - Vote/comment → check MongoDB `Votes`/`Comments` collections update and UI reflects counts.
  - Profile edits → confirm SQL Server rows change accordingly.

### Project Structure Highlights
- `app.py`: FastAPI application, dependency setup, routers for auth, documents, votes, comments, downloads, favorites, profile, AI pipelines.
- `public/`: Static client (HTML, CSS, JS). Each JS file maps to a page/feature (e.g., `quiz.js`, `explore.js`, `profile.js`).
- `uploads/`: Persisted user files (Git-ignored, keep secure).
- `make_quiz.py`, `summarizer.py`, `keywords.py`: AI helper classes instantiated lazily in `app.py`.
- `requirements.txt`: Core Python dependencies.

### Deployment Notes
- Use a production server (Gunicorn/Uvicorn workers) behind reverse proxy.
- Protect `SECRET_KEY` and database credentials through environment variables or secret managers.
- Configure CORS origins appropriately (`allow_origins` is currently `*` for dev).
- Set up scheduled backups for MongoDB and SQL Server data, especially `uploads/`.

### Contributing
1. Fork the repo, create a feature branch.
2. Keep JS free of console logs/comments (current coding standard).
3. Run linting/tests (to be added) and open a PR describing changes & manual test steps.

### License
Specify the project’s license here (MIT, Apache 2.0, proprietary, etc.). Update this section with the actual license text or link as needed.

