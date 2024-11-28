from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database.connect import get_db_connection
from auth import create_jwt_token, verify_refresh_token
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
    assignment : int
    group_work : int
    grading : int

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
        # 새로운 리뷰 삽입
        cursor.execute(
            """
            INSERT INTO Course_Review (course_id, user_id, comment, rating, assignment, group_work, grading)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (review.course_id, review.student_id, review.review_text, review.rating, review.assignment, review.group_work, review.grading),
        )

        # 평균 평점 계산
        cursor.execute(
            """
            SELECT AVG(rating) AS avg_rating
            FROM Course_Review
            WHERE course_id = %s
            """,
            (review.course_id,)
        )
        avg_rating = cursor.fetchone()[0]

        # Course 테이블의 avg_rating 필드 업데이트
        cursor.execute(
            """
            UPDATE Course
            SET avg_rating = %s
            WHERE course_id = %s
            """,
            (avg_rating, review.course_id)
        )

        # 변경 사항 커밋
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
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM Course")
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
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 댓글 데이터 가져오기
        query_comments = "SELECT * FROM Course_Review WHERE course_id = %s"
        cursor.execute(query_comments, (course_id,))
        comments = cursor.fetchall()

        # 평균 평점 가져오기 (DECIMAL/FLOAT 타입 유지)
        query_avg_rating = """
            SELECT avg_rating AS avg_rating 
            FROM Course 
            WHERE course_id = %s
        """
        cursor.execute(query_avg_rating, (course_id,))
        avg_rating_row = cursor.fetchone()
        avg_rating = float(avg_rating_row['avg_rating']) if avg_rating_row and avg_rating_row['avg_rating'] is not None else None
        avg_rating = float(f"{avg_rating:.2f}")
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    if not comments:
        raise HTTPException(status_code=404, detail="No comments found for the given course ID.")

    return {"status": "success", "data": comments, "avg_rating": avg_rating}


#AUTHENTICATION

@app.post("/login", tags=['Auth'])
async def login(student_id: str = Form(...), password: str = Form(...)):
    """
    로그인 API (Refresh Token만 반환)
    """
    user_info = get_user_info(id=student_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid student ID or password.")

    refresh_token = create_jwt_token(student_id, "refresh", expires_delta=7)

    return {
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@app.post("/token/refresh", tags=['Auth'])
async def refresh_access_token(refresh_token: str = Form(...)):
    """
    Refresh Token을 사용해 Access Token을 발급하는 API
    """
    try:
        payload = verify_refresh_token(refresh_token)
        student_id = payload.get("sub")
        if not student_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token.")

        access_token = create_jwt_token(student_id, "access", expires_delta=1)
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}")

@app.get("/user_info/{user_id}", response_model=UserInfoResponse, tags=["user_info"])
async def get_user_info_endpoint(user_id: str, password: str):
    user_info = get_user_info(id=user_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_info

@app.post("/upload-excel", tags=['user_info'])
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    data = read_excel_from_file(file)
    return {"status": "success", "data": data}
