from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.database import get_db, Student, Milestone, Grant
from auth import get_current_user
from services.claude_service import generate_student_followup, get_grant_opportunities, generate_grant_section

# ── STUDENTS ──
students_router = APIRouter()

class StudentCreate(BaseModel):
    name: str
    email: str = ""
    program: str = "PhD"
    year: int = 1
    thesis_title: str = ""
    progress_percent: int = 0
    notes: str = ""

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    thesis_title: Optional[str] = None
    thesis_status: Optional[str] = None
    progress_percent: Optional[int] = None
    notes: Optional[str] = None
    last_meeting: Optional[str] = None
    next_meeting: Optional[str] = None

@students_router.get("/")
def get_students(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    students = db.query(Student).filter(Student.supervisor_id == current_user.id).all()
    return [serialize_student(s) for s in students]

@students_router.post("/")
def create_student(body: StudentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    s = Student(**body.dict(), supervisor_id=current_user.id)
    db.add(s); db.commit(); db.refresh(s)
    return serialize_student(s)

@students_router.put("/{sid}")
def update_student(sid: int, body: StudentUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == sid, Student.supervisor_id == current_user.id).first()
    if not s: raise HTTPException(404)
    data = body.dict(exclude_none=True)
    for k, v in data.items():
        if k in ('last_meeting', 'next_meeting') and v:
            try: v = datetime.fromisoformat(v)
            except: v = None
        setattr(s, k, v)
    db.commit()
    return serialize_student(s)

@students_router.delete("/{sid}")
def delete_student(sid: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == sid, Student.supervisor_id == current_user.id).first()
    if not s: raise HTTPException(404)
    db.delete(s); db.commit()
    return {"ok": True}

@students_router.post("/{sid}/followup")
def followup(sid: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == sid, Student.supervisor_id == current_user.id).first()
    if not s: raise HTTPException(404)
    email = generate_student_followup(serialize_student(s), current_user.name)
    return {"email": email}

@students_router.post("/{sid}/milestones")
def add_milestone(sid: int, body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == sid, Student.supervisor_id == current_user.id).first()
    if not s: raise HTTPException(404)
    due = None
    if body.get("due_date"):
        try: due = datetime.fromisoformat(body["due_date"])
        except: pass
    m = Milestone(student_id=sid, title=body.get("title",""), due_date=due, notes=body.get("notes",""))
    db.add(m); db.commit()
    return {"id": m.id, "title": m.title}

@students_router.put("/{sid}/milestones/{mid}")
def update_milestone(sid: int, mid: int, body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    m = db.query(Milestone).filter(Milestone.id == mid).first()
    if not m: raise HTTPException(404)
    m.completed = body.get("completed", m.completed)
    db.commit()
    return {"ok": True}

def serialize_student(s):
    return {
        "id": s.id, "name": s.name, "email": s.email,
        "program": s.program, "year": s.year,
        "thesis_title": s.thesis_title, "thesis_status": s.thesis_status,
        "progress_percent": s.progress_percent, "notes": s.notes,
        "last_meeting": s.last_meeting.isoformat() if s.last_meeting else None,
        "next_meeting": s.next_meeting.isoformat() if s.next_meeting else None,
        "milestones": [{"id": m.id, "title": m.title, "completed": m.completed,
                        "due_date": m.due_date.isoformat() if m.due_date else None} for m in s.milestones]
    }

# ── GRANTS ──
grants_router = APIRouter()

class GrantCreate(BaseModel):
    title: str
    agency: str
    program: str = ""
    deadline: str = ""
    amount: str = ""
    description: str = ""
    url: str = ""
    is_opportunity: bool = False

@grants_router.get("/")
def get_grants(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    grants = db.query(Grant).filter(Grant.owner_id == current_user.id).order_by(Grant.deadline).all()
    return [serialize_grant(g) for g in grants]

@grants_router.post("/")
def create_grant(body: GrantCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    deadline = None
    if body.deadline:
        try: deadline = datetime.fromisoformat(body.deadline)
        except: pass
    g = Grant(title=body.title, agency=body.agency, program=body.program,
              deadline=deadline, amount=body.amount, description=body.description,
              url=body.url, is_opportunity=body.is_opportunity,
              owner_id=current_user.id, draft_content={})
    db.add(g); db.commit(); db.refresh(g)
    return serialize_grant(g)

@grants_router.put("/{gid}/status")
def update_status(gid: int, body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = db.query(Grant).filter(Grant.id == gid, Grant.owner_id == current_user.id).first()
    if not g: raise HTTPException(404)
    g.status = body.get("status", g.status)
    db.commit()
    return serialize_grant(g)

@grants_router.delete("/{gid}")
def delete_grant(gid: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = db.query(Grant).filter(Grant.id == gid, Grant.owner_id == current_user.id).first()
    if not g: raise HTTPException(404)
    db.delete(g); db.commit()
    return {"ok": True}

@grants_router.post("/{gid}/write")
def write_section(gid: int, body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = db.query(Grant).filter(Grant.id == gid, Grant.owner_id == current_user.id).first()
    if not g: raise HTTPException(404)
    section = body.get("section", "aims")
    profile = f"{current_user.name}, {current_user.role} at {current_user.institution}, Department of {current_user.department}. {body.get('profile', '')}"
    content = generate_grant_section(section, profile, serialize_grant(g), body.get("existing", ""))
    draft = g.draft_content or {}
    draft[section] = content
    g.draft_content = draft
    db.commit()
    return {"section": section, "content": content}

@grants_router.post("/find-opportunities")
def find_opportunities(body: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    profile = body.get("profile", f"{current_user.role} at {current_user.institution}, {current_user.department}")
    opportunities = get_grant_opportunities(profile)
    saved = []
    for opp in opportunities:
        deadline = None
        if opp.get("deadline"):
            try: deadline = datetime.fromisoformat(opp["deadline"])
            except: pass
        g = Grant(title=opp.get("title",""), agency=opp.get("agency",""),
                  program=opp.get("program",""), deadline=deadline,
                  amount=opp.get("amount",""), description=opp.get("relevance",""),
                  url=opp.get("url",""), is_opportunity=True,
                  owner_id=current_user.id, status="identified", draft_content={})
        db.add(g)
        saved.append(opp)
    db.commit()
    return saved

def serialize_grant(g):
    return {
        "id": g.id, "title": g.title, "agency": g.agency,
        "program": g.program, "status": g.status,
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "amount": g.amount, "description": g.description,
        "url": g.url, "is_opportunity": g.is_opportunity,
        "draft_content": g.draft_content or {}
    }
