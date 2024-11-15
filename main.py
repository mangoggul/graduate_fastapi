from fastapi import FastAPI, File, HTTPException, UploadFile
from views.user_info import get_user_info, UserInfoResponse  # user_info.py에서 가져오기
import pandas as dp
from views.get_csv import read_excel_from_file
app = FastAPI()

# FastAPI 엔드포인트 정의
@app.get("/user_info/{user_id}", response_model=UserInfoResponse)
async def get_user_info_endpoint(user_id: str, password: str):
    # 사용자 정보를 가져오는 함수 호출
    user_info = get_user_info(id=user_id, pw=password)
    return user_info

@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """
    사용자가 업로드한 엑셀 파일을 읽어 JSON 형식으로 반환하는 API 엔드포인트입니다.
    """
    # 파일 확장자 확인
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    # 엑셀 파일 읽기
    data = read_excel_from_file(file)
    return {"status": "success", "data": data}