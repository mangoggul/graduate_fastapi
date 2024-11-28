import jwt
from datetime import datetime, timedelta
import secrets
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"

def create_jwt_token(sub: str, token_type: str, expires_delta: int):
    expire = datetime.utcnow() + timedelta(days=expires_delta)
    payload = {
        "sub": sub,
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_refresh_token(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type.")
    return payload
