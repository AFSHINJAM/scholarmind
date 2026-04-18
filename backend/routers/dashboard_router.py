from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.database import get_db, Paper, Review, Student, Grant, Task
from auth import get_current_user

router = APIRouter()

@router.get("/")
def get_dashboard(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    now = datetime.utcnow()
    soon = now + timedelta(days=14)

    papers = db.query(Paper).filter(Paper.owner_id == current_user.id).all()
    reviews = db.query(Review).filter(Review.reviewer_id == current_user.id).all()
    students = db.query(Student).filter(Student.supervisor_id == current_user.id).all()
    grants = db.query(Grant).filter(Grant.owner_id == current_user.id).all()

    pending_reviews = [p for p in papers if p.status in ("pending", "in_progress")]
    overdue = [p for p in papers if p.due_date and p.due_date < now and p.status != "completed"]
    due_soon = [p for p in papers if p.due_date and now <= p.due_date <= soon and p.status != "completed"]
    upcoming_grants = [g for g in grants if g.deadline and now <= g.deadline <= soon + timedelta(days=60)]
    students_no_checkin = [s for s in students if not s.last_meeting or (now - s.last_meeting).days > 21]

    urgent_tasks = []
    for p in overdue:
        urgent_tasks.append({"type": "overdue_review", "title": f"OVERDUE: {p.title[:50]}", "id": p.id, "priority": "high"})
    for p in due_soon:
        days_left = (p.due_date - now).days
        urgent_tasks.append({"type": "review_due", "title": f"Due in {days_left}d: {p.title[:50]}", "id": p.id, "priority": "high" if days_left <= 7 else "medium"})
    for g in upcoming_grants:
        days_left = (g.deadline - now).days
        urgent_tasks.append({"type": "grant_deadline", "title": f"Grant deadline in {days_left}d: {g.title[:40]}", "id": g.id, "priority": "high" if days_left <= 14 else "medium"})
    for s in students_no_checkin:
        days = (now - s.last_meeting).days if s.last_meeting else 999
        urgent_tasks.append({"type": "student_checkin", "title": f"No check-in with {s.name} for {days}d", "id": s.id, "priority": "medium"})

    return {
        "stats": {
            "total_papers": len(papers),
            "pending_reviews": len(pending_reviews),
            "completed_reviews": len([r for r in reviews if r.status == "completed"]),
            "total_students": len(students),
            "active_grants": len([g for g in grants if g.status in ("identified", "drafting")]),
        },
        "urgent_tasks": urgent_tasks[:10],
        "recent_papers": [{"id": p.id, "title": p.title, "journal": p.journal, "status": p.status,
                           "paper_type": p.paper_type, "due_date": p.due_date.isoformat() if p.due_date else None}
                          for p in sorted(papers, key=lambda x: x.created_at, reverse=True)[:5]],
        "upcoming_grants": [{"id": g.id, "title": g.title, "agency": g.agency, "status": g.status,
                             "deadline": g.deadline.isoformat() if g.deadline else None}
                            for g in sorted(upcoming_grants, key=lambda x: x.deadline)[:4]],
        "students_summary": [{"id": s.id, "name": s.name, "program": s.program,
                              "progress_percent": s.progress_percent,
                              "last_meeting": s.last_meeting.isoformat() if s.last_meeting else None}
                             for s in students]
    }
