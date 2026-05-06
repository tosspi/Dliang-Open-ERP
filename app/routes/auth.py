"""Authentication routes for Dliang-ERP"""
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    User,
    UserRole,
    create_access_token,
    ensure_admin_user,
    get_current_user,
    get_db,
    verify_password,
)
from app.database import SessionLocal

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/ui", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login form submission."""
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "用户名或密码错误"
            },
            status_code=401
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    
    response = RedirectResponse(url="/ui", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout():
    """Handle logout."""
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render register page (admin only)."""
    user = get_current_user(request)
    if not user or user.role != UserRole.admin:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request, "user": user})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("employee"),
    db: Session = Depends(get_db)
):
    """Handle user registration (admin only)."""
    user = get_current_user(request)
    if not user or user.role != UserRole.admin:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    # Check if username exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "user": user,
                "error": "用户名已存在"
            },
            status_code=400
        )
    
    # Create new user
    from app.auth import get_password_hash
    new_user = User(
        username=username,
        hashed_password=get_password_hash(password),
        role=UserRole.admin if role == "admin" else UserRole.employee,
        full_name=full_name,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/ui/users" if user.role == UserRole.admin else "/ui", status_code=303)


@router.get("/users", response_class=HTMLResponse)
async def list_users(request: Request):
    """List all users (admin only)."""
    user = get_current_user(request)
    if not user or user.role != UserRole.admin:
        return RedirectResponse(url="/auth/login", status_code=303)
    
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return templates.TemplateResponse(
            request=request,
            name="users.html",
            context={"request": request, "user": user, "users": users}
        )
    finally:
        db.close()
