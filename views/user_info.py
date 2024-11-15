from sejong_univ_auth import auth, ClassicSession
from pydantic import BaseModel
from fastapi import HTTPException

# Pydantic 모델 정의
class UserInfoResponse(BaseModel):
    id: str
    name: str
    major: str
    book: str

# 사용자 정보를 반환하는 함수
def get_user_info(id: str, pw: str) -> dict:
    res = auth(id=id, password=pw, methods=ClassicSession)

    # 대휴칼 사이트 오류
    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Server error")

    # 로그인 오류 (ID/PW 틀림 or 가입불가 재학생)
    if not res.is_auth:
        raise HTTPException(status_code=401, detail="Authentication failed")

    # 사용자 정보
    name = res.body["name"]
    major = res.body["major"]
    
    # 고전독서 인증현황
    status = res.body["status"]
    if status == "대체이수":
        book = "고특통과"
    else:
        read_certification = res.body["read_certification"]
        book = ""
        for num in read_certification.values():
            book += num.replace(" 권", "")

    return {
        "id": id,
        "name": name,
        "major": major,
        "book": book
    }

