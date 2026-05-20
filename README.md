
# Pathfinder: Your personal Career guide

Pathfinder is a fullstack web application that leverages Modern generative models to provide personalized career counseling. Built with Flask and Google Gemini API, it dynamically generates structured career roadmaps based on user metrics and stores historical state in a relational database.

## Overview

This project demonstrates the ability to integrate modern Large Language Models (LLMs) into a full stack MVC web framework. Rather than a simple chatbot, the application collects qualitative user data (interests, values, work styles), constructs a highly specific context window, and forces the LLM to return actionable, structured data (Job Title, Match Reason, and a Step-by-Step Roadmap). 

## Technology Stack

* **Backend:** Python 3.8+, Flask 3.1, Werkzeug
* **Database & ORM:** SQLite (Dev) / PostgreSQL (Prod), Flask-SQLAlchemy 3.1 on supabase
* **Authentication:** Flask-Login
* **AI Integration:** Google Generative AI SDK (`gemini-1.5-flash` / `gemini-1.5-pro`)
* **Frontend:** HTML5, Jinja2 Templating, Tailwind CSS (Custom Configured via CDN)
* **Deployment:** Vercel Serverless Functions

## Database Architecture

The application relies on a relational model managed by SQLAlchemy ORM:

**`User` Table**
* `id` (Integer, PK): Unique identifier.
* `email` (String, Unique): User's login credential.
* `password_hash` (String): PBKDF2 hashed password.
* *Relationship:* One-to-Many with `Assessment`.

**`Assessment` Table**
* `id` (Integer, PK): Unique identifier.
* `user_id` (Integer, FK): Reference to the user who took the assessment.
* `subjects`, `hobbies`, `style`, `value` (Strings): Raw psychometric input data.
* `careers_json` (Text): The stringified JSON payload returned by the Gemini API.
* `created_at` (DateTime): Auto-generated timestamp.

## Local Development Setup

**1. Clone & Environment Setup**
```bash
git clone <your-repo-url>
cd fsd_project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

```

**2. Install Dependencies**

```bash
pip install -r requirements.txt

```

**3. Environment Variables (`.env`)**
Create a `.env` file in the root directory. The application will dynamically use SQLite if `DATABASE_URL` is omitted.

```env
SECRET_KEY=your_secure_development_key
GEMINI_API_KEY=your_google_gemini_api_key
MODEL_NAME=gemini-1.5-flash
# DATABASE_URL=postgresql://user:pass@host/db  # Uncomment for production DB

```

**4. Initialize & Run**

```bash
python app.py

```

*Note: SQLAlchemy will automatically call `db.create_all()` within the app context on the first run, provisioning the SQLite database (`instance/app.db`).*

## Serverless Deployment (Vercel)

This repository is pre-configured for Vercel deployment via `vercel.json`.

1. Ensure you have a cloud PostgreSQL database provisioned (e.g., Supabase, Neon).
2. Connect your GitHub repository to Vercel.
3. In the Vercel project settings, configure your Environment Variables (`SECRET_KEY`, `GEMINI_API_KEY`, `MODEL_NAME`, `DATABASE_URL`).
4. The `app.py` logic automatically intercepts Supabase connection strings (`postgres://`) and converts them to the SQLAlchemy-compliant `postgresql://` protocol, appending required SSL modes.
5. Deploy.
