from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models.database import get_db, User
from auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "researcher"
    department: str = ""
    institution: str = ""

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        name=req.name,
        role=req.role,
        department=req.department,
        institution=req.institution,
        hashed_password=get_password_hash(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": {
        "id": user.id, "name": user.name, "email": user.email,
        "role": user.role, "department": user.department, "institution": user.institution
    }}

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": {
        "id": user.id, "name": user.name, "email": user.email,
        "role": user.role, "department": user.department, "institution": user.institution
    }}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id, "name": current_user.name,
        "email": current_user.email, "role": current_user.role,
        "department": current_user.department, "institution": current_user.institution
    }
