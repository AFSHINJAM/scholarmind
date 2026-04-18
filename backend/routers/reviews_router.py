from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import io
from models.database import get_db, Review, Paper
from auth import get_current_user

router = APIRouter()

class ReviewUpdate(BaseModel):
    summary: Optional[str] = None
    major_concerns: Optional[str] = None
    minor_concerns: Optional[str] = None
    recommendation: Optional[str] = None
    score_novelty: Optional[float] = None
    score_methodology: Optional[float] = None
    score_clarity: Optional[float] = None
    score_statistics: Optional[float] = None

@router.get("/")
def get_reviews(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    reviews = db.query(Review).filter(Review.reviewer_id == current_user.id).all()
    result = []
    for r in reviews:
        result.append({
            "id": r.id, "paper_id": r.paper_id,
            "paper_title": r.paper.title if r.paper else "",
            "paper_journal": r.paper.journal if r.paper else "",
            "paper_type": r.paper.paper_type if r.paper else "",
            "recommendation": r.recommendation,
            "status": r.status,
            "score_novelty": r.score_novelty,
            "score_methodology": r.score_methodology,
            "score_clarity": r.score_clarity,
            "score_statistics": r.score_statistics,
            "due_date": r.paper.due_date.isoformat() if r.paper and r.paper.due_date else None,
            "updated_at": r.updated_at.isoformat()
        })
    return result

@router.get("/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == review_id, Review.reviewer_id == current_user.id).first()
    if not review: raise HTTPException(404, "Review not found")
    return serialize_review(review)

@router.put("/{review_id}")
def update_review(review_id: int, body: ReviewUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == review_id, Review.reviewer_id == current_user.id).first()
    if not review: raise HTTPException(404, "Review not found")
    for field, value in body.dict(exclude_none=True).items():
        setattr(review, field, value)
    review.updated_at = datetime.utcnow()
    db.commit()
    return serialize_review(review)

@router.post("/{review_id}/complete")
def complete_review(review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == review_id, Review.reviewer_id == current_user.id).first()
    if not review: raise HTTPException(404)
    review.status = "completed"
    if review.paper: review.paper.status = "completed"
    db.commit()
    return {"ok": True}

@router.get("/{review_id}/export")
def export_review(review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == review_id, Review.reviewer_id == current_user.id).first()
    if not review: raise HTTPException(404)
    
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        # Title
        title_para = doc.add_heading('PEER REVIEW REPORT', 0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Manuscript: {review.paper.title if review.paper else 'Unknown'}")
        doc.add_paragraph(f"Journal: {review.paper.journal if review.paper else 'Unknown'}")
        doc.add_paragraph(f"Review Date: {datetime.utcnow().strftime('%B %d, %Y')}")
        doc.add_paragraph(f"Reviewer: {current_user.name}")
        doc.add_paragraph(f"Recommendation: {review.recommendation or 'Not specified'}")
        doc.add_paragraph("")

        sections = [
            ("SUMMARY", review.summary),
            ("MAJOR CONCERNS", review.major_concerns),
            ("MINOR CONCERNS", review.minor_concerns),
        ]
        for heading, content in sections:
            if content:
                doc.add_heading(heading, level=1)
                doc.add_paragraph(content or "")
                doc.add_paragraph("")

        # Scores table
        doc.add_heading("SCORES", level=1)
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text = 'Criterion'
        hdr[1].text = 'Score (out of 10)'
        scores = [
            ("Novelty", review.score_novelty),
            ("Methodology", review.score_methodology),
            ("Clarity", review.score_clarity),
            ("Statistical Rigor", review.score_statistics),
        ]
        for label, score in scores:
            row = table.add_row().cells
            row[0].text = label
            row[1].text = str(score) if score else "N/A"

        doc.add_paragraph("")
        doc.add_paragraph("Generated by ScholarMind · Powered by Claude AI · Anthropic")
        
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        
        filename = f"review_{review.paper.title[:30] if review.paper else 'manuscript'}.docx".replace(" ", "_")
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")

def serialize_review(r):
    return {
        "id": r.id, "paper_id": r.paper_id,
        "paper_title": r.paper.title if r.paper else "",
        "paper_journal": r.paper.journal if r.paper else "",
        "paper_type": r.paper.paper_type if r.paper else "",
        "summary": r.summary, "major_concerns": r.major_concerns,
        "minor_concerns": r.minor_concerns, "recommendation": r.recommendation,
        "score_novelty": r.score_novelty, "score_methodology": r.score_methodology,
        "score_clarity": r.score_clarity, "score_statistics": r.score_statistics,
        "claude_analysis": r.claude_analysis, "claude_checklist": r.claude_checklist,
        "status": r.status, "updated_at": r.updated_at.isoformat(),
        "due_date": r.paper.due_date.isoformat() if r.paper and r.paper.due_date else None
    }
