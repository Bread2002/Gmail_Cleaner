# **Gmail Cleaner**

### _Copyright (c) 2026, Rye Stahle-Smith_

---

## 📌 Overview

A local-first inbox management tool built with **React TS + FastAPI**, authenticated through **Google OAuth 2.0**. Sign in with your Google account, kick off a scan, and surface the senders flooding your inbox with unread emails. From there you can bulk-trash all their messages or create Gmail filters to block them permanently — with real-time SSE progress on every action.

---

## ⚙️ Features

- 🔐 **Google OAuth 2.0** — Sign in with your Google account; tokens are stored server-side in memory and expire after 1 hour
- 📬 **Inbox Scanner** — Identifies senders with N+ consecutive unread emails via the Gmail API; real-time progress streamed over SSE
- 🗑️ **Bulk Trash** — Move every message from flagged senders to trash in batches; live deletion progress per sender
- 🚫 **Sender Blocking** — Creates permanent Gmail filters that auto-trash future emails from blocked senders
- 🧪 **Dry Run Mode** — Preview exactly what would be trashed or blocked without making any changes
- ⚙️ **Configurable Settings** — Tune the consecutive-unread threshold, max senders to surface, and messages per sender to inspect

---

## 📂 Repository Structure

```
Gmail_Cleaner/
├── backend/                        # FastAPI Python backend
│   ├── pyproject.toml              # Python dependencies
│   └── app/
│       ├── main.py                 # FastAPI entry point + CORS config
│       ├── config.py               # Pydantic settings (loaded from .env)
│       ├── dependencies.py         # Session + Gmail service injection
│       ├── models/                 # Pydantic request/response models
│       ├── routers/                # API route handlers
│       │   ├── auth.py             # Google OAuth flow
│       │   ├── scan.py             # Inbox scan + SSE stream
│       │   ├── senders.py          # Per-sender and bulk trash/block actions
│       │   └── settings.py         # User settings
│       ├── services/               # Gmail API business logic
│       │   ├── gmail_auth.py       # OAuth URL builder + token exchange
│       │   ├── gmail_scan.py       # Consecutive-unread detection
│       │   ├── gmail_trash.py      # Batch message deletion
│       │   └── gmail_filter.py     # Gmail filter creation (blocking)
│       └── store/                  # In-memory session + job queue store
├── frontend/                       # React + TypeScript (Vite) frontend
│   └── src/
│       ├── App.tsx                 # Root app + routing
│       ├── pages/                  # Login, Dashboard, Settings, Callback pages
│       ├── components/             # UI components (scan, senders, deletion, layout)
│       ├── hooks/                  # useAuth, useScan, useDeletion, useSettings
│       ├── api/                    # Typed API client functions
│       ├── types/                  # Shared TypeScript interfaces
│       └── utils/                  # SSE helper, formatters
└── scripts/
    ├── dev.ps1                     # Windows: opens backend + frontend in separate terminals
    └── dev.sh                      # macOS/Linux: same, using bash
```

---

## 🚀 Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google Cloud](https://console.cloud.google.com) project with the **Gmail API** enabled and **OAuth 2.0 credentials** created

---

### ☁️ Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create or select a project

2. Enable the **Gmail API** under _APIs & Services → Library_

3. Under _APIs & Services → OAuth consent screen_, choose **External** user type and add the following scopes:

   ```
   https://mail.google.com/
   https://www.googleapis.com/auth/gmail.settings.basic
   https://www.googleapis.com/auth/gmail.settings.sharing
   https://www.googleapis.com/auth/userinfo.email
   openid
   ```

   Add your Gmail address as a **test user**

4. Under _APIs & Services → Credentials_, create an **OAuth 2.0 Client ID** (Application type: **Web application**)

5. Add the following to **Authorized redirect URIs**:

   ```
   http://localhost:5173/auth/callback
   ```

6. Note your **Client ID**, **Client Secret**, and **Project ID** — you'll need them next

---

### 🖥️ Run the Backend

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\pip install -e .     # Windows
   # or
   .venv/bin/pip install -e .         # macOS/Linux
   ```

2. Create a `.env` file in `backend/`:

   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_PROJECT_ID=your-project-id
   GOOGLE_REDIRECT_URI=http://localhost:5173/auth/callback
   FRONTEND_ORIGIN=http://localhost:5173
   ```

3. Start the server:

   ```bash
   .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000   # Windows
   # or
   .venv/bin/python -m uvicorn app.main:app --reload --port 8000        # macOS/Linux
   ```

   API runs on `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

### 🌐 Run the Frontend

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Create a `.env` file in `frontend/`:

   ```env
   VITE_SSE_BASE_URL=http://localhost:8000
   ```

   > ⚠️ **Note:** Regular API calls go through the Vite dev proxy (`/api → http://localhost:8000`), which is already configured in `vite.config.ts` — no extra env var needed. SSE must connect directly to the backend because the proxy buffers responses and breaks real-time event streaming.

3. Run:
   ```bash
   npm run dev
   ```
   Frontend runs on `http://localhost:5173`.

---

### ⚡ Quick Start (Dev Script)

Once both `.env` files are in place and dependencies are installed, launch both servers at once from the project root:

```powershell
# Windows
.\scripts\dev.ps1
```

```bash
# macOS/Linux
bash scripts/dev.sh
```

This opens the backend and frontend in separate terminal windows so you can see live logs from each server.

---

## 🔌 API Endpoints

### REST

| Method  | Endpoint                | Description                                                      |
| ------- | ----------------------- | ---------------------------------------------------------------- |
| `GET`   | `/auth/login`           | Returns the Google OAuth authorization URL                       |
| `POST`  | `/auth/callback`        | Exchanges auth code for tokens; creates a server-side session    |
| `POST`  | `/auth/logout`          | Revokes token and destroys the session                           |
| `GET`   | `/auth/me`              | Returns the authenticated user's email                           |
| `POST`  | `/scan/start`           | Starts a background inbox scan; returns a `scan_id`              |
| `GET`   | `/scan/{id}/results`    | Polling fallback for completed scan results                      |
| `GET`   | `/senders/{id}/preview` | Returns subject, snippet, and date of a sender's latest email    |
| `POST`  | `/senders/{id}/trash`   | Starts a batch-trash job for a sender; returns a `job_id`        |
| `POST`  | `/senders/{id}/block`   | Creates a Gmail filter to auto-trash future emails from a sender |
| `POST`  | `/senders/bulk/trash`   | Starts batch-trash jobs for multiple senders; returns `job_id`s  |
| `POST`  | `/senders/bulk/block`   | Creates Gmail filters for multiple senders at once               |
| `POST`  | `/senders/bulk/skip`    | Acknowledges a client-side skip (no Gmail API call made)         |
| `GET`   | `/settings`             | Returns the current user's settings for this session             |
| `PATCH` | `/settings`             | Updates one or more settings fields                              |

### SSE (Server-Sent Events)

Long-lived connections where the backend streams progress events to the client in real time. Token is passed as a `?token=` query parameter since `EventSource` does not support request headers.

| Method | Endpoint                              | Description                                                                                                                                                                     |
| ------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/scan/{id}/stream`                   | Real-time scan progress; fires `sender_found` events as senders are flagged, then `done` when complete                                                                          |
| `GET`  | `/senders/{id}/trash/{job_id}/stream` | Deletion progress for a single trash job; used for both individual and bulk trash — the bulk REST endpoint returns multiple `job_id`s and the frontend opens one stream per job |
