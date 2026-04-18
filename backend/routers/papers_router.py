from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os, shutil
from models.database import get_db, Paper, Review, ChatMessage
from auth import get_current_user
from services.claude_service import extract_text_from_file, chat_with_paper, analyze_paper_for_review

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_paper(
    title: str = Form(...),
    authors: str = Form(""),
    journal: str = Form(""),
    paper_type: str = Form("journal_review"),
    due_date: str = Form(""),
    file: UploadFile = File(...),
    supp_files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Save main file — accept ANY file type
    safe_filename = file.filename.replace(" ", "_")
    file_path = f"{UPLOAD_DIR}/{current_user.id}_{safe_filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text from any file type
    extracted = extract_text_from_file(file_path, file.filename)

    # Save supplementary files
    supp_paths = []
    for sf in supp_files:
        if sf.filename:
            safe_sf = sf.filename.replace(" ", "_")
            sp = f"{UPLOAD_DIR}/{current_user.id}_supp_{safe_sf}"
            with open(sp, "wb") as f:
                shutil.copyfileobj(sf.file, f)
            supp_paths.append({"path": sp, "name": sf.filename})

    due = None
    if due_date:
        try:
            due = datetime.fromisoformat(due_date)
        except:
            pass

    paper = Paper(
        title=title,
        authors=authors,
        journal=journal,
        paper_type=paper_type,
        file_path=file_path,
        supp_files=[s["path"] for s in supp_paths],
        extracted_text=extracted,
        due_date=due,
        owner_id=current_user.id,
        status="pending"
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return {"id": paper.id, "title": paper.title, "status": paper.status,
            "text_length": len(extracted), "filename": file.filename}

@router.get("/")
def get_papers(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    papers = db.query(Paper).filter(Paper.owner_id == current_user.id).order_by(Paper.created_at.desc()).all()
    return [serialize_paper(p) for p in papers]

@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    return serialize_paper(paper)

@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    # Delete files
    try:
        if paper.file_path and os.path.exists(paper.file_path):
            os.remove(paper.file_path)
        for sp in (paper.supp_files or []):
            if os.path.exists(sp):
                os.remove(sp)
    except:
        pass
    db.delete(paper)
    db.commit()
    return {"ok": True}

@router.post("/{paper_id}/chat")
def chat(paper_id: int, body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    history = db.query(ChatMessage).filter(
        ChatMessage.paper_id == paper_id
    ).order_by(ChatMessage.created_at).all()
    messages = [{"role": m.role, "content": m.content} for m in history]

    question = body.get("message", "")
    response = chat_with_paper(paper.extracted_text or "", messages, question, paper.title)

    db.add(ChatMessage(paper_id=paper_id, user_id=current_user.id, role="user", content=question))
    db.add(ChatMessage(paper_id=paper_id, user_id=current_user.id, role="assistant", content=response))
    db.commit()
    return {"response": response}

@router.get("/{paper_id}/chat/history")
def chat_history(paper_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    msgs = db.query(ChatMessage).filter(
        ChatMessage.paper_id == paper_id
    ).order_by(ChatMessage.created_at).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]

@router.post("/{paper_id}/analyze")
def analyze(paper_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == current_user.id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    supp_text = ""
    for sp in (paper.supp_files or []):
        if os.path.exists(sp):
            supp_text += extract_text_from_file(sp, sp)

    analysis = analyze_paper_for_review(
        paper.extracted_text or "", supp_text, paper.paper_type, paper.journal
    )

    review = db.query(Review).filter(Review.paper_id == paper_id).first()
    if not review:
        review = Review(paper_id=paper_id, reviewer_id=current_user.id)
        db.add(review)

    review.claude_analysis = analysis.get("summary", "")
    review.claude_checklist = analysis.get("checklist", [])
    review.summary = analysis.get("summary", "")
    review.major_concerns = analysis.get("major_concerns", "")
    review.minor_concerns = analysis.get("minor_concerns", "")
    review.recommendation = analysis.get("recommendation", "")
    review.score_novelty = analysis.get("score_novelty")
    review.score_methodology = analysis.get("score_methodology")
    review.score_clarity = analysis.get("score_clarity")
    review.score_statistics = analysis.get("score_statistics")
    paper.status = "in_progress"
    db.commit()
    return analysis

def serialize_paper(p):
    return {
        "id": p.id, "title": p.title, "authors": p.authors,
        "journal": p.journal, "paper_type": p.paper_type,
        "status": p.status,
        "due_date": p.due_date.isoformat() if p.due_date else None,
        "created_at": p.created_at.isoformat(),
        "has_review": p.review is not None,
        "supp_count": len(p.supp_files or []),
        "file_path": p.file_path
    }
