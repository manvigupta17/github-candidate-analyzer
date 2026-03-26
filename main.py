from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from analysis import full_analysis, compare_users

app = FastAPI(title="GitHub Candidate Analyzer", version="3.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class CompareRequest(BaseModel):
    username1: str
    username2: str

@app.get("/")
def home():
    return {"message": "GitHub Analyzer API v3 🚀", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/analyze/{username}")
def analyze_user(username: str):
    try:
        return full_analysis(username.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis error: {e}")

@app.post("/compare")
def compare_candidates(body: CompareRequest):
    try:
        data1 = full_analysis(body.username1.strip())
        data2 = full_analysis(body.username2.strip())
        return {"comparison": compare_users(data1, data2), "candidate1": data1, "candidate2": data2}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Comparison error: {e}")