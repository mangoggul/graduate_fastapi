from fastapi import FastAPI, HTTPException
from views.user_info import get_user_info, UserInfoResponse  # user_info.py에서 가져오기
app = FastAPI()

# FastAPI 엔드포인트 정의
@app.get("/user_info/{user_id}", response_model=UserInfoResponse)
async def get_user_info_endpoint(user_id: str, password: str):
    # 사용자 정보를 가져오는 함수 호출
    user_info = get_user_info(id=user_id, pw=password)
    return user_info
