from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database.connect import get_db_connection
from auth import create_jwt_token, verify_refresh_token
from views.user_info import get_user_info, UserInfoResponse
from views.get_csv import read_excel_from_file
from fastapi import Header
import jwt
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
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # 사용자 정보 가져오기
        user_info = get_user_info(id=student_id, pw=password)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid student ID or password.")

        # Refresh Token 생성
        refresh_token = create_jwt_token(student_id, "refresh", expires_delta=7)
        
        # User 테이블 업데이트 쿼리
        update_query = """
            INSERT INTO User (user_id, username, refresh_token) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            username = VALUES(username),
            refresh_token = VALUES(refresh_token)
        """
        cursor.execute(update_query, (
            user_info['id'],
            user_info['name'],
            refresh_token
        ))
        connection.commit()

        return {
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()

@app.post("/token/refresh", tags=['Auth'])
async def refresh_access_token(authorization: str = Header(default=None)):
    """
    일단 사용 X
    """
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
            
        refresh_token = authorization.split('Bearer ')[1]
        
        # DB에서 refresh token 확인
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT user_id FROM User WHERE refresh_token = %s"
            cursor.execute(query, (refresh_token,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(status_code=401, detail="Refresh token not found")
                
            # 토큰 검증
            payload = verify_refresh_token(refresh_token)
            student_id = payload.get("sub")
            if not student_id:
                raise HTTPException(status_code=401, detail="Invalid refresh token")

            # 새로운 access token 생성
            access_token = create_jwt_token(student_id, "access", expires_delta=1)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
            }
            
        finally:
            cursor.close()
            connection.close()
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token has expired")
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/user-info/{user_id}", response_model=UserInfoResponse, tags=["user_info"])
async def get_user_info_endpoint(user_id: str, password: str):

    """
    학번과 비밀번호를 입력하면 그거에 관련한 정보 반환 : 학번, 이름, 전공, 고전독서
    """

    user_info = get_user_info(id=user_id, pw=password)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found.")
    return user_info

@app.post("/upload-excel", tags=['Excel'])
async def upload_excel(file: UploadFile = File(...), student_id: str = Query(...)):

    """
    액셀 업로드 후 DB 에 저장
    """

    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    data = read_excel_from_file(file)

    connection = get_db_connection()
    cursor = connection.cursor()
    print(data[3])

    
    try:
        # 엑셀 파일의 각 행을 데이터베이스에 삽입
        for i in range(3,len(data)) :

            cursor.execute(
                """
                INSERT INTO course_data (
                    user_id, year, semester, course_code, 
                    course_name, course_type, credit, grade
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    student_id, # request에서 받은 학번
                    data[i]['년도'],
                    data[i]['학기'],
                    data[i]['과목코드'],
                    data[i]['과목명'],
                    data[i]['이수구분'],
                    data[i]['학점'],
                    data[i]['평점'],
                )
            )

        # 변경 사항 커밋
        connection.commit()

    except mysql.connector.Error as err:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    return {"status": "success", "message": "Data inserted successfully."}



@app.get("/get-course-data", tags=['Excel'])
async def get_course_data(student_id: str = Query(...)):

    """
    학번을 넣고 수강한 과목 전부 반환
    """

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)  # dictionary=True는 결과를 딕셔너리 형식으로 반환

    try:
        # student_id와 연관된 데이터를 조회하는 쿼리
        cursor.execute(
            """
            SELECT *
            FROM course_data
            WHERE user_id = %s
            """,
            (student_id,)
        )
        
        # 조회된 데이터 가져오기
        result = cursor.fetchall()

        # 데이터가 없을 경우
        if not result:
            raise HTTPException(status_code=404, detail="No data found for the provided student ID.")
        
        return {"status": "success", "data": result}
    
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    
    finally:
        cursor.close()
        connection.close()


