# 🔍 GitHub Candidate Analyzer

> Transform raw GitHub activity into structured engineering intelligence — built for recruiters and hiring teams who want data-backed decisions.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=flat-square&logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 📌 What It Does

The **GitHub Candidate Analyzer** is a full-stack web application that evaluates software developers based on their public GitHub activity. Enter a GitHub username and get back:

- A **weighted hiring score** (0–100)
- A **verdict** — from STRONG ACCEPT to STRONG REJECT
- An **AI-written technical narrative** summarizing the candidate
- Deep-dive metrics on commits, code quality, collaboration, and language usage

---

## 🏗️ Architecture

```
User (Browser)
     ↓
Streamlit UI  (Port 8501)
     ↓  HTTP Request
FastAPI Backend  (Port 8000)
     ↓
GitHub REST API
     ↓
Analysis Engine
     ↓
AI Provider (Groq / OpenAI / Gemini)
     ↓
JSON Response → Rendered Report
```

---

## 📁 Project Structure

```
github-candidate-analyzer/
│
├── main.py              # FastAPI app — /analyze and /compare endpoints
├── analysis.py          # Core scoring and metric computation engine (46 KB)
├── github_utils.py      # GitHub REST API communication layer
├── streamlit_app.py     # Streamlit frontend UI
├── requirements.txt     # Python dependencies
├── .env                 # API keys (not committed to Git)
└── .gitignore
```

---

## ⚙️ How the Scoring Works

The final hiring score is a **weighted average** across six dimensions:

| Metric             | Weight |
|--------------------|--------|
| Commit Activity    | 25%    |
| Code Quality       | 25%    |
| Consistency        | 15%    |
| Recency            | 15%    |
| Collaboration      | 10%    |
| Popularity         | 10%    |

**Verdict Thresholds:**

| Score   | Verdict        |
|---------|----------------|
| 80+     | ✅ STRONG ACCEPT |
| 65–79   | ✅ ACCEPT        |
| 45–64   | 🔶 REVIEW        |
| 25–44   | ❌ REJECT        |
| < 25    | ❌ STRONG REJECT |

---

## 🔬 What Gets Analyzed

### Profile & Repository Metrics
- Stars, forks, releases, topics, licenses
- Most starred and largest repositories
- Account age and public repo count

### Commit Behavior
- Active commit span, average commits/month
- Trend detection (Increasing / Stable / Declining based on last 90 days)
- Busiest day/hour, weekend commit ratio
- Conventional commit message quality (`feat:`, `fix:`, `docs:` etc.)

### Code Quality Signals
- README completeness (length, sections, badges, examples)
- Test file detection and test-to-file ratio
- CI/CD presence (`.github/workflows`, Travis, Jenkins)
- Docker configuration detection

### Language Distribution
- Byte-weighted language percentages across all repos
- Developer specialization classification: Frontend / Backend / Full-Stack / Systems

### Collaboration
- Unique collaborators
- Issue resolution rate
- Pull request merge rate

---

## 🤖 AI Summary

The system sends all computed metrics to an AI provider and receives a narrative evaluation. Supported providers:

- **Groq** (Llama 3.3 70B) — recommended for speed
- **Gemini**
- **Anthropic Claude**

If no API key is configured, a template-based fallback summary is generated automatically.

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/github-candidate-analyzer.git
cd github-candidate-analyzer
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key          # optional
GEMINI_API_KEY=your_gemini_api_key      # optional
ANTHROPIC_API_KEY=your_anthropic_key    # optional
```

> 💡 Without a `GITHUB_TOKEN`, you're limited to 60 GitHub API requests/hour. With one, you get 5,000/hour.

### 5. Run the Backend

```bash
uvicorn main:app --reload --port 8000
```

### 6. Run the Frontend (in a new terminal)

```bash
streamlit run streamlit_app.py
```

### 7. Open the App

Go to **http://localhost:8501** in your browser.

---

## 📡 API Endpoints

The FastAPI backend exposes:

| Method | Endpoint                  | Description                        |
|--------|---------------------------|------------------------------------|
| GET    | `/analyze/{username}`     | Full analysis of a GitHub user     |
| POST   | `/compare`                | Side-by-side comparison of users   |
| GET    | `/docs`                   | Auto-generated Swagger UI          |

---

## 🔒 Security

- All API keys are stored in `.env` and loaded via `python-dotenv`
- `.env` is excluded from version control via `.gitignore`
- No secrets are hardcoded anywhere in the source

---

## 🧰 Tech Stack

| Layer     | Technology         |
|-----------|--------------------|
| Backend   | FastAPI, Python    |
| Frontend  | Streamlit          |
| Data      | GitHub REST API    |
| AI        | Groq / Gemini / Anthropic |
| Config    | python-dotenv      |

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙋 Author

Built by [Your Name](https://github.com/YOUR_USERNAME)  
Feel free to open issues or submit PRs!
