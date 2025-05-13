from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional
import sqlite3
import os

# Configurações
SECRET_KEY = "ITZORO1890@SENHA"  # Em produção.
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Modelos Pydantic
class User(BaseModel):
    username: str

class UserCreate(User):
    password: str

class Habit(BaseModel):
    id: int
    name: str
    date: str
    done: bool
    user_id: int

class HabitCreate(BaseModel):
    name: str
    date: str

# Inicialização do FastAPI
app = FastAPI(title="Habit Tracker API", version="1.0.0")

# Segurança
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Banco de dados
def get_db():
    conn = sqlite3.connect('habits.db')
    conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    return conn

def init_db():
    if not os.path.exists('habits.db'):
        conn = sqlite3.connect('habits.db')
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Tabela de hábitos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                done BOOLEAN DEFAULT FALSE,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()

# Utilitários
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", 
        (username,)
    ).fetchone()
    conn.close()
    
    if user is None:
        raise credentials_exception
        
    return {"username": user["username"]}

# Rotas
@app.post("/register", response_model=User)
def register(user: UserCreate):
    conn = get_db()
    try:
        # Verifica se usuário já existe
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (user.username,)
        ).fetchone()
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Username already registered"
            )
        
        # Cria novo usuário
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (user.username, get_password_hash(user.password))
        )
        conn.commit()
        
        return {"username": user.username}
    finally:
        conn.close()

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", 
            (form_data.username,)
        ).fetchone()
        
        if not user or not verify_password(form_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(
            data={"sub": user["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        conn.close()

@app.get("/habitos", response_model=List[Habit])
def read_habits(current_user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (current_user["username"],)
        ).fetchone()
        
        habits = conn.execute(
            "SELECT id, name, date, done, user_id FROM habits WHERE user_id = ?",
            (user["id"],)
        ).fetchall()
        
        return [
            {
                "id": habit["id"],
                "name": habit["name"],
                "date": habit["date"],
                "done": bool(habit["done"]),
                "user_id": habit["user_id"]
            }
            for habit in habits
        ]
    finally:
        conn.close()

@app.post("/habitos", response_model=Habit)
def create_habit(habit: HabitCreate, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (current_user["username"],)
        ).fetchone()
        
        cursor = conn.execute(
            "INSERT INTO habits (name, date, user_id) VALUES (?, ?, ?)",
            (habit.name, habit.date, user["id"])
        )
        conn.commit()
        
        new_habit = conn.execute(
            "SELECT id, name, date, done, user_id FROM habits WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()
        
        return {
            "id": new_habit["id"],
            "name": new_habit["name"],
            "date": new_habit["date"],
            "done": bool(new_habit["done"]),
            "user_id": new_habit["user_id"]
        }
    finally:
        conn.close()

@app.patch("/habitos/{habit_id}/feito", response_model=Habit)
def mark_habit_done(habit_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (current_user["username"],)
        ).fetchone()
        
        conn.execute(
            "UPDATE habits SET done = TRUE WHERE id = ? AND user_id = ?",
            (habit_id, user["id"])
        )
        conn.commit()
        
        habit = conn.execute(
            "SELECT id, name, date, done, user_id FROM habits WHERE id = ?",
            (habit_id,)
        ).fetchone()
        
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        
        return {
            "id": habit["id"],
            "name": habit["name"],
            "date": habit["date"],
            "done": bool(habit["done"]),
            "user_id": habit["user_id"]
        }
    finally:
        conn.close()

@app.delete("/habitos/{habit_id}")
def delete_habit(habit_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?", 
            (current_user["username"],)
        ).fetchone()
        
        result = conn.execute(
            "DELETE FROM habits WHERE id = ? AND user_id = ?",
            (habit_id, user["id"])
        )
        conn.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Habit not found")
        
        return {"message": "Habit deleted successfully"}
    finally:
        conn.close()

# Inicializa o banco de dados
init_db()
from sqlite3 import connect

# Cria a tabela se não existir
def init_db():
    conn = connect("seu_banco.db")  # Ou o nome do seu arquivo SQLite
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

# Chame a função no início do app
init_db()