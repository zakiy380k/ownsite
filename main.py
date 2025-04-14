#Daniil Chumakov 
#Библиотеки

from fastapi import FastAPI, HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Response
from fastapi import status
from fastapi import UploadFile, File
import shutil
from fastapi import Request, Form
import bcrypt
import os

# Database setup
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI app setup
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


#База данных
# Таблица пользователей
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    birth_date = Column(String)

Base.metadata.create_all(bind=engine)

# Таблица постов
class PostDB(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    author = Column(String)
    image_path = Column(String)

#Комментарии
Base.metadata.create_all(bind=engine)
class CommentDB(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer)
    author = Column(String)
    content = Column(String)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Маршруты
# Главная страница
@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/posts")


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Авторизация
@app.post("/login", response_class=None)
def login(request: Request,login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(login=login).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        response = RedirectResponse(url="/posts", status_code=303)
        response.set_cookie(key="user", value=user.login)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login or password"}) # Если пользователь не найден, возвращаем ошибку


@app.get("/user/add", response_class=HTMLResponse)
def add_user_form(request: Request):
    return templates.TemplateResponse("add_user.html", {"request": request})

# Регистрация
@app.post("/user/add", response_class=HTMLResponse)
def add_user(login: str = Form(...), password: str = Form(...), first_name: str = Form(...),
             last_name: str = Form(...), birth_date: str = Form(...), db: Session = Depends(get_db)):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = UserDB(login=login, password=hashed_password, first_name=first_name, last_name=last_name, birth_date=birth_date)
    db.add(user)# Добавляем пользователя в базу данных
    db.commit()# Сохраняем изменения в базе данных
    print(db.query(UserDB).all())# Выводим всех пользователей в консоль
    return RedirectResponse(url="/login", status_code=303)

#Доп страница(отключена) со всеми пользователями
@app.get("/user/view", response_class=HTMLResponse)
def view_users(request: Request, db: Session = Depends(get_db)):
    user_login = request.cookies.get("user")  # Получаем логин из куки
    if not user_login: # Если логин не найден, перенаправляем на страницу входа
        return RedirectResponse(url="/login", status_code=303) 
    users = db.query(UserDB).all() 
    return templates.TemplateResponse("view_user.html", {"request": request, "users": users})

#Функция выхода из аккаунта
@app.post("/logout")
def logout(response: Response):
    redirect_response = RedirectResponse(url="/login", status_code=303) # Перенаправляем на страницу входа
    redirect_response.delete_cookie("user") # Удаляем куки с логином
    return redirect_response

# Функция для получения всех постов
@app.get("/posts", response_class=HTMLResponse)
def show_posts(request: Request, db: Session = Depends(get_db), page: int = 1, limit: int = 5):
    total_posts = db.query(PostDB).count()
    posts = db.query(PostDB).offset((page - 1) * limit).limit(limit).all()
    comments = db.query(CommentDB).all()
    
    return templates.TemplateResponse("posts.html", {
        "request": request,
        "posts": posts,
        "comments": comments,
        "page": page,
        "limit": limit,
        "total_posts": total_posts
    })

@app.get("/post/new", response_class=HTMLResponse)
def new_post_form(request: Request):
    return templates.TemplateResponse("new_post.html", {"request": request})

#Создание поста
@app.post("/post/new", response_class=HTMLResponse)
def create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),  # <-- обработка файла
    db: Session = Depends(get_db)
):
    user_login = request.cookies.get("user")
    if not user_login:
        return RedirectResponse(url="/login", status_code=303)

    image_path = None
    if image and image.filename: # Если файл загружен
        # Сохранение файла на сервере
        file_location = f"static/uploads/{image.filename}"
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = file_location

    post = PostDB(title=title, content=content, author=user_login, image_path=image_path)
    db.add(post)
    db.commit()
    return RedirectResponse(url="/posts", status_code=303)

#Лень дальше писать коменты, но там все изи
#Удаление поста
@app.post("/post/delete/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), request: Request = None):
    user_login = request.cookies.get("user")
    if not user_login:
        return RedirectResponse(url="/login", status_code=303)

    post = db.query(PostDB).filter(PostDB.id == post_id).first()
    if post:
        db.delete(post)
        db.commit()
    return RedirectResponse(url="/posts", status_code=303)

#Профиль пользователя
@app.get("/profile", response_class=HTMLResponse)
def user_profile(request: Request, db: Session = Depends(get_db)):
    user_login = request.cookies.get("user")
    if not user_login:
        return RedirectResponse(url="/login", status_code=303)
    
    comments = db.query(CommentDB).filter(CommentDB.author == user_login).all()
    user_posts = db.query(PostDB).filter(PostDB.author == user_login).all()
    user = db.query(UserDB).filter(UserDB.login == user_login).first()
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "posts": user_posts,
        "comments" : comments
    })

#Коментарий к посту
@app.post("/comment/add/{post_id}")
def add_comment(post_id: int, request: Request, content: str = Form(...), db: Session = Depends(get_db)):
    user_login = request.cookies.get("user")
    if not user_login:
        return RedirectResponse(url="/login", status_code=303)

    comment = CommentDB(post_id=post_id, author=user_login, content=content)
    db.add(comment)
    db.commit()
    return RedirectResponse(url="/posts", status_code=303)  