# DayMate

**DayMate**, an AI-powered daily planner that combines weather + news to produce a short daily plan and recommendations with a Lightweight FastAPI backend.

> Live backend: **[https://daymate-bitmascot-backend.onrender.com](https://daymate-bitmascot-backend.onrender.com)**
> API docs (Swagger UI): **[https://daymate-bitmascot-backend.onrender.com/docs](https://daymate-bitmascot-backend.onrender.com/docs)**

---

# Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Repository structure](#repository-structure)
4. [Requirements](#requirements)
5. [Local setup & run](#local-setup--run)
6. [Environment variables](#environment-variables)
7. [Available endpoints & examples](#available-endpoints--examples)
8. [LLM integration & fallback behavior](#llm-integration--fallback-behavior)
9. [Deploying to Render (how I deployed)](#deploying-to-render-how-i-deployed)
10. [Troubleshooting & common gotchas](#troubleshooting--common-gotchas)
11. [Future Plan](#future-plan)

---

# Overview

This backend exposes a small set of APIs that:

* fetch current weather (OpenWeather API)
* fetch top headlines (GNews)
* generate a short daily plan using either:

  * an LLM via Groq/OpenAI-compatible API (if `GROQ_API_KEY` is set), **or**
  * a deterministic fallback "manual" planner when no LLM key is present.

The codebase is intentionally small, so it is easy to run locally and deploy.

---

# Features

* `/weather` — current weather using OpenWeather.
* `/news` — top headlines (GNews).
* `/plan` — POST endpoint that aggregates weather + headlines and either:

  * forwards a prompt to the configured LLM (Groq/OpenAI-compatible) **or**
  * runs a simple fallback planner (no LLM required).
* `/` shows info and status, and `/docs` will show Swagger UI.

---

# Repository structure

```
daymate/
├─ backend/
│ ├─ main.py
│ ├─ requirements.txt
│ └─ .env.example
├─ frontend/    (frontend still pending)
└─ README.md
```

`backend/main.py` contains the FastAPI app and all endpoint logic.

---

# Requirements

* Python 3.11+ recommended (code was tested with pyenv 3.11.x)
* Packages (see `backend/requirements.txt`):

  * fastapi, uvicorn, httpx, pydantic, langchain-openai, python-dotenv

---

# Local setup & run

1. Clone repository and change to backend directory:

```bash
git clone https://github.com/raihan822/daymate-bitmascot.git
cd daymate-bitmascot/backend
```

2. Create a virtual environment and install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in keys (see Environment variables section below):

```bash
cp .env.example .env
# edit .env with your API keys
```

4. Run the app (development):

```bash
# recommended during development - auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. Open docs in your browser:

```
http://127.0.0.1:8000/docs
```

---

# Environment variables

Use `.env` locally or set them in your deployment environment.

Example `.env` (see `backend/.env.example`):

```env
OPENWEATHER_KEY=_openweather_key_
GNEWS_API_KEY=_gnews_key_
OPENAI_API_KEY=_openai_key_    # optional - helpful for some LLM setups
GROQ_API_KEY=_groq_key_      # optional - if set, LLM path will be used
PORT=8000
```

**Security note:** do not commit your real keys to git. Use Render/Heroku/Netlify secrets or OS environment variables in production.

---

# Available endpoints & examples

All endpoints are under the deployed host: `https://daymate-bitmascot-backend.onrender.com/docs`

## 1) Swagger UI

`GET /docs` — interactive API docs.

## 2) / root

`GET /` — Shows Information, and Status (default behavior in `main.py`).

## 3) Get weather

```
GET /weather?lat={lat}&lon={lon}
```

Example:

```bash
curl "https://daymate-bitmascot-backend.onrender.com/weather?lat=23.7104&lon=90.40744"
```

Successful response: JSON returned from OpenWeather (see OpenWeather API for schema).

## 4) Get news

```
GET /news?country=bd&q=optional_query
```

Default `country` is `bd`. Example:

```bash
curl "https://daymate-bitmascot-backend.onrender.com/news?country=bd"
```

## 5) Generate plan (POST)

`POST /plan` — body contains `{ lat, lon, location_name? }`

Example curl:

```bash
curl -X POST "https://daymate-bitmascot-backend.onrender.com/plan" \
  -H "Content-Type: application/json" \
  -d '{"lat": 23.7104, "lon": 90.40744, "location_name":"bd"}'
```

* If `GROQ_API_KEY` (or a valid LLM env configured) is present, the backend will call the LLM and return `"planning"` text and the `"prompt"` used.
* If no LLM key, a deterministic fallback planner is returned.

---

# LLM integration & fallback behavior

* The code uses a small helper `load_llm(...)` built around `langchain_openai.ChatOpenAI`.
* To enable LLM (RAG) behavior set `GROQ_API_KEY` (or other configured key) in your environment.
* If LLM is present: a prompt combining location, weather description and top headlines is sent to the LLM and the LLM's full text is returned.
* If LLM is **not** present: the app will produce a simple, deterministic plan using keywords (e.g., if `"rain"` in weather → umbrella suggestion).

**Note:** the `langchain-openai` package and the remote LLM provider may require additional configuration (model name, base URL, API usage limits). See `main.py` for the implementation details.

---

# Deploying to Render — how I deployed

The backend is already deployed at: **[https://daymate-bitmascot-backend.onrender.com](https://daymate-bitmascot-backend.onrender.com)**

If you want to deploy yourself, follow these steps:

1. Create a new **Web Service** on Render.
2. Connect the GitHub repository `raihan822/daymate-bitmascot`.
3. **Root Directory**: set to `backend` (so Render knows where `main.py` lives).
4. **Start Command**:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

5. **Environment**: set environment variables in Render's **Environment** → **Environment Variables** (add `OPENWEATHER_KEY`, `GNEWS_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY` as required).
6. Select a Python runtime (Render will auto-detect if `requirements.txt` is present). Optionally set the Python version to 3.11.
7. Deploy.

**Logs & Diagnostics:** use Render's live logs for build/runtime errors. If an endpoint returns `500` or `502`, open the logs to inspect the stack trace and any messages printed by `httpx` / `uvicorn`.

---

# Troubleshooting & common gotchas

* **General:**

    1. Check Render's **Root Directory** — must be `backend`.
    2. Confirm the **Start Command** is `uvicorn main:app --host 0.0.0.0 --port $PORT`.
    3. Verify the deployed commit contains `main.py` with the `/` route (check repository branch).
    4. Inspect Render logs for import errors or exceptions during startup (missing dependencies, syntax errors).
    5. If a different route behavior is desired, edit `main.py` to return custom JSON (uncomment the alternate root in `main.py`).
* **HTTP 502 / third-party API errors**

  * If the app returns `502` for `/weather` or `/news`, check the upstream API keys and whether the external API is reachable from Render. Confirm the env var names exactly match (`OPENWEATHER_KEY`, `GNEWS_API_KEY`).
* **LLM errors or timeouts**

  * LLM calls may time out depending on the provider. Increase `timeout` in the `load_llm` call or check provider logs/quotas.
* **Missing dependencies**

  * Make sure Render installs all items from `requirements.txt`. If you use wheels or system-specific packages, install them or choose compatible alternatives.

---

# Future Plan:

* **Frontend** is pending; the repo contains a `frontend/` scaffold. When the frontend is ready, I will update the README and CORS settings if needed.
* will add a `/health` or `/ping` endpoint for uptime checks (for load balancers/uptime monitors).
* Will add unit tests for the fallback planner and input validation.
* will add rate-limiting / caching of 3rd-party responses to avoid hitting API quotas.
* The LLM prompt and chaining will be moved later to a separate module for easier testing and more advanced RAG.

---

# Contributing

1. Fork the repo.
2. Create a feature branch.
3. Open a PR with tests and a clear description.

---

© Raihan Sarker

---

If you want, I can:

* add a short `curl` + example response section for each endpoint (with sample output), or
* patch the root route to return a custom JSON message (instead of redirect), and provide the exact `git` commands to push this fix to the branch you deploy. Which would you prefer?


