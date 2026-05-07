import os
import jwt
import bcrypt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-muito-segura-123")

def hash_password(password: str) -> str:
    """Gera o hash da senha usando bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica se a senha coincide com o hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Gera um Token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7) # Token dura 7 dias por padrão
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def decode_token(token: str):
    """Decodifica e valida o Token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None # Token expirado
    except jwt.InvalidTokenError:
        return None # Token inválido
