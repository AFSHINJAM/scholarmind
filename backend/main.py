from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from models.database import create_tables
from routers.auth_router import router as auth_router
from routers.papers_router import router as papers_router
from routers.reviews_router import router as reviews_router
from routers.students_grants_router import students_router, grants_router
from routers.dashboard_router import router as dashboard_router

app = FastAPI(title="ScholarMind API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(papers_router, prefix="/api/papers", tags=["papers"])
app.include_router(reviews_router, prefix="/api/reviews", tags=["reviews"])
app.include_router(students_router, prefix="/api/students", tags=["students"])
app.include_router(grants_router, prefix="/api/grants", tags=["grants"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def root():
    index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"message": "ScholarMind API running"}

@app.on_event("startup")
def startup():
    create_tables()
    print("✅ ScholarMind started — database ready")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
