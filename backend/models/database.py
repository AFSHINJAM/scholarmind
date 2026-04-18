from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./scholarmind.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String, default="researcher")  # researcher, professor, admin
    department = Column(String)
    institution = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    papers = relationship("Paper", back_populates="owner")
    reviews = relationship("Review", back_populates="reviewer")
    students = relationship("Student", back_populates="supervisor")
    grants = relationship("Grant", back_populates="owner")

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    authors = Column(String)
    journal = Column(String)
    year = Column(Integer)
    paper_type = Column(String)  # journal_review, thesis_msc, thesis_phd, grant
    status = Column(String, default="pending")  # pending, in_progress, completed
    file_path = Column(String)
    supp_files = Column(JSON, default=[])
    extracted_text = Column(Text)
    due_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="papers")
    review = relationship("Review", back_populates="paper", uselist=False)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    summary = Column(Text, default="")
    major_concerns = Column(Text, default="")
    minor_concerns = Column(Text, default="")
    recommendation = Column(String, default="")
    score_novelty = Column(Float, nullable=True)
    score_methodology = Column(Float, nullable=True)
    score_clarity = Column(Float, nullable=True)
    score_statistics = Column(Float, nullable=True)
    claude_analysis = Column(Text, default="")
    claude_checklist = Column(JSON, default=[])
    status = Column(String, default="draft")  # draft, completed, exported
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paper = relationship("Paper", back_populates="review")
    reviewer = relationship("User", back_populates="reviews")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    program = Column(String)  # PhD, MSc, PostDoc
    year = Column(Integer)
    thesis_title = Column(String, nullable=True)
    thesis_status = Column(String, default="in_progress")
    last_meeting = Column(DateTime, nullable=True)
    next_meeting = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    progress_percent = Column(Integer, default=0)
    supervisor_id = Column(Integer, ForeignKey("users.id"))
    supervisor = relationship("User", back_populates="students")
    milestones = relationship("Milestone", back_populates="student")

class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    title = Column(String)
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    student = relationship("Student", back_populates="milestones")

class Grant(Base):
    __tablename__ = "grants"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    agency = Column(String)  # CIHR, NSERC, NIH, etc.
    program = Column(String)
    deadline = Column(DateTime)
    amount = Column(String, nullable=True)
    status = Column(String, default="identified")  # identified, drafting, submitted, awarded, rejected
    description = Column(Text, nullable=True)
    draft_content = Column(JSON, default={})
    is_opportunity = Column(Boolean, default=False)  # external opportunity vs user's own grant
    url = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="grants")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)  # user, assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    task_type = Column(String)  # review, thesis, grant, student, other
    priority = Column(String, default="medium")  # high, medium, low
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)
