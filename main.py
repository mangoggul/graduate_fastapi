from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database.connect import get_db_connection
from auth import create_jwt_token
from views.user_info import get_user_info, UserInfoResponse
from views.get_csv import read_excel_from_file
import mysql.connector
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CourseReview 모델 정의
class CourseReview(BaseModel):
    course_id: str
    student_id: str
    review_text: str
    rating: int

@app.post("/course/review", tags=['Course'])
async def create_review(review: CourseReview):
    """
    강의 후기 작성 API
    """
    if not (1 <= review.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO course_review (course_id, user_id, comment, rating)
            VALUES (%s, %s, %s, %s)
            """,
            (review.course_id, review.student_id, review.review_text, review.rating),
        )
        connection.commit()
    except mysql.connector.Error as err:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    return {"status": "success", "message": "Review submitted successfully."}

@app.get("/courses", tags=['Course'])
async def get_all_courses():
    """
    데이터베이스에서 모든 강의 정보를 가져오는 API
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM course")  # `course` 테이블에서 모든 데이터를 가져오는 쿼리
        courses = cursor.fetchall()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    if not courses:
        raise HTTPException(status_code=404, detail="No courses found.")

    return {"status": "success", "data": courses}

@app.get("/courses/{course_id}/comments", tags=["Course"])
async def get_comments_by_course_id(course_id: int):
    """
    특정 강의 ID(course_id)에 해당하는 모든 댓글을 가져오는 API
    """
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 댓글 데이터를 가져오는 SQL 쿼리
        query = "SELECT * FROM course_review WHERE course_id = %s"
        cursor.execute(query, (course_id,))
        comments = cursor.fetchall()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    if not comments:
        raise HTTPException(status_code=404, detail="No comments found for the given course ID.")

    return {"status": "success", "data": comments}

@app.post("/login", tags=['Auth'])
async def login(student_id: str = Form(...), password: str = Form(...)):
    """
    로그인 API
    """
    user_info = get_user_info(id=student_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid student ID or password.")

    access_token = create_jwt_token(student_id, "access", expires_delta=1)
    refresh_token = create_jwt_token(student_id, "refresh", expires_delta=7)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@app.get("/user_info/{user_id}", response_model=UserInfoResponse, tags=["user_info"])
async def get_user_info_endpoint(user_id: str, password: str):
    """
    사용자 정보 조회 API
    """
    user_info = get_user_info(id=user_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_info

@app.post("/upload-excel", tags=['user_info'])
async def upload_excel(file: UploadFile = File(...)):
    """
    엑셀 파일 업로드 및 읽기 API
    """
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    data = read_excel_from_file(file)
    return {"status": "success", "data": data}
