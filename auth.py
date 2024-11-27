import jwt
import datetime
import secrets

# JWT 비밀 키
SECRET_KEY = secrets.token_hex(32)

def create_jwt_token(student_id: str, token_type: str, expires_delta: int):
    """
    JWT 토큰 생성 함수.
    :param student_id: 사용자 ID
    :param token_type: 'access' 또는 'refresh'
    :param expires_delta: 만료 시간 (시간 단위)
    :return: 생성된 JWT 토큰
    """
    expiration = datetime.datetime.utcnow()
    if token_type == "access":
        expiration += datetime.timedelta(hours=expires_delta)
    elif token_type == "refresh":
        expiration += datetime.timedelta(days=expires_delta)

    payload = {
        "sub": student_id,
        "type": token_type,
        "exp": expiration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
