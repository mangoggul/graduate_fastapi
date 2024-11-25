from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from views.user_info import get_user_info, UserInfoResponse
from views.get_csv import read_excel_from_file
import datetime
import jwt
import secrets
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware  # CORS 미들웨어 import

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173",
                   
        ],  # 모든 오리진 허용, 필요시 특정 도메인으로 제한 가능
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# JWT를 위한 비밀 키
SECRET_KEY = secrets.token_hex(32)

@app.get("/user_info/{user_id}", response_model=UserInfoResponse, tags=["get_user_info"])
async def get_user_info_endpoint(user_id: str, password: str):
    """
    사용자 정보를 가져오는 API 엔드포인트입니다.
    """
    user_info = get_user_info(id=user_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_info

def create_access_token(student_id: str, expires_delta: int = 1):
    """
    Access 토큰 생성 함수
    """
    payload = {
        "sub": student_id,  # 사용자 ID
        "type": "access",  # type을 'access'로 설정하여 access token임을 구분
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=expires_delta),  # 1시간 후 만료
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def create_refresh_token(student_id: str, expires_delta: int = 7):
    """
    Refresh 토큰 생성 함수
    """
    payload = {
        "sub": student_id,  # 사용자 ID
        "type": "refresh",  # type을 'refresh'로 설정하여 refresh token임을 구분
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=expires_delta),  # 7일 후 만료
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


@app.post("/login")
async def login(student_id: str = Form(...), password: str = Form(...)):
    """
    로그인 API: student_id와 password를 받아 인증 후 JWT 토큰을 반환합니다.
    """
    # 사용자 정보 가져오기
    user_info = get_user_info(id=student_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid student ID or password.")
    
    # JWT 토큰 생성
    access_token = create_access_token(student_id)  # 1시간 만료된 access token 생성
    refresh_token = create_refresh_token(student_id)  # 7일 만료된 refresh token 생성
    
    return {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_type": "bearer",
        "Connection": "Succeed"
    }


@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """
    사용자가 업로드한 엑셀 파일을 읽어 JSON 형식으로 반환하는 API 엔드포인트입니다.
    """
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    # 엑셀 파일 읽기
    data = read_excel_from_file(file)
    return {"status": "success", "data": data}
