from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database.connect import get_db_connection
from auth import create_jwt_token, verify_refresh_token
from views.user_info import get_user_info, UserInfoResponse
from views.get_csv import read_excel_from_file
from fastapi import Header
import jwt
import mysql.connector
from functions.test import generate_timetables
import os
import traceback
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate 
from langchain.schema import SystemMessage, HumanMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
    

    
    try:
        # 엑셀 파일의 각 행을 데이터베이스에 삽입
        for i in range(3,len(data)) :

            cursor.execute(
                """
                INSERT INTO course_data (
                    user_id, year, semester, course_code, 
                    course_name, course_type, credit, grade, choice, grade_detail
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    data[i]['비고2'],
                    data[i]['성적등급']
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


class QuestionSelection(BaseModel):
    student_id: int
    selected_questions: List[int]


# 요청 데이터 모델 정의
class QuestionSelection(BaseModel):
    student_id: int
    selected_questions: List[int]

@app.post("/submit-questions", tags=["AI generate TimeTable"])
async def submit_questions(selection: QuestionSelection):

    """
    사용자는 질문에 대한 답을 하고 여기서 바로 ciffy comment ai로 만들어버림
    반드시 이 API 사용 후에 하단 API 이용해야됨 반드시 !!!!
    """
    # 1~5 범위 검증
    if not all(1 <= question <= 5 for question in selection.selected_questions):
        raise HTTPException(
            status_code=400,
            detail="Each selected question must be between 1 and 5."
        )
    
    # 질문 개수 검증 (10개 고정)
    if len(selection.selected_questions) != 10:
        raise HTTPException(
            status_code=400,
            detail="You must select exactly 10 questions."
        )
    
    # 질문 내용
    questions = [
        "팀플 수업이 많았으면 좋겠다.",
        "시험보단 과제로 평가가 되었으면 좋겠다.",
        "수업 내용이 실제 업무에 도움이 되는 수업을 선호한다.",
        "수업이 이론보다는 실습 위주로 진행되면 좋겠다.",
        "영어 수업을 선호한다.",
        "후기가 많은 과목이 좋다.",
        "졸업을 위한 필수 과목을 많이 들어야한다.",
        "교양이 많았으면 좋겠다.",
        "시험이 어려운 수업이 좋다.",
        "교수님이 학생들과의 소통을 중요시하는 수업을 선호한다."
    ]
    
    # 선택된 질문의 텍스트 생성
    selected_questions_text = [questions[q - 1] for q in selection.selected_questions]
    prompt_text = (
        "다음은 학생의 선호도를 나타내는 질문 목록입니다. "
        
        "이 학생의 선호도를 요약하여 한국어로 한줄평을 작성해주세요:\n\n" +
        "\n".join(f"{i + 1}. {text}" for i, text in enumerate(selected_questions_text))
    )
    
    # LangChain Chat 모델 초기화
    ai_model = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        openai_api_key=OPENAI_API_KEY
    )
    
    # 3개의 댓글 생성
    ai_comments = []
    try:
        for _ in range(3):
            # 메시지 생성
            messages = [
                SystemMessage(content="당신은 학생의 선호도를 요약하여 한국어로 한줄평을 작성하는 AI입니다."),
                HumanMessage(content=prompt_text)
            ]
            
            # LangChain 모델을 통해 응답 생성
            response = ai_model(messages)
            ai_comments.append(response.content.strip())
    except Exception as e:
        # 에러 처리
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Error communicating with GPT: {e}\nDetails: {error_details}")
    
    # DB 저장
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        # Questions 테이블에 저장
        cursor.execute(
            """
            INSERT INTO Questions (
                user_id, firstQ, secondQ, thirdQ, fourthQ, fifthQ, sixthQ, seventhQ, eighthQ, ninthQ, tenthQ
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                selection.student_id,
                selection.selected_questions[0],
                selection.selected_questions[1],
                selection.selected_questions[2],
                selection.selected_questions[3],
                selection.selected_questions[4],
                selection.selected_questions[5],
                selection.selected_questions[6],
                selection.selected_questions[7],
                selection.selected_questions[8],
                selection.selected_questions[9],
            )
        )
        question_id = cursor.lastrowid
        # ciffy_comment 테이블에 댓글 3개 저장
        for comment in ai_comments:
            cursor.execute(
                """
                INSERT INTO ciffy_comment (question_id, comment)
                VALUES (%s, %s)
                """,
                (question_id, comment)
            )
        
        # 변경 사항 커밋
        connection.commit()
    except mysql.connector.Error as err:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        cursor.close()
        connection.close()

    return {
        "message": "Questions submitted successfully",
        "user_id": selection.student_id,
        "selected_questions": selection.selected_questions,
        "ai_comments": ai_comments
    }

@app.get("/generate-timetable/{student_id}", tags=["AI generate TimeTable"])
async def generate_timetable_api(student_id: int):
    """
    학생 ID 던지면 그거에 맞는 테이블 DB 에 저장
    이거 먼저 쓰면 절대 안됨 위에 API 먼저 사용하고 이거 사용해야됨 둘이 햄버거와 콜라임
    """
    file_path = "txt/course.txt"  # 학생 ID별 강의 데이터 경로

    try:
        # 3개의 시간표를 생성
        timetables = generate_timetables(file_path, count=3)

        # DB 연결 및 데이터 삽입
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            # 기존 최대 course_set_id 확인
            cursor.execute("SELECT IFNULL(MAX(course_set_id), 0) FROM timetables")
            max_course_set_id = cursor.fetchone()[0]
            max_course_set_id  = int(max_course_set_id)
            next_course_set_id = max_course_set_id + 1

            # 생성된 시간표 데이터 삽입
            for timetable in timetables:
                current_course_set_id = next_course_set_id
                next_course_set_id += 1  # course_set_id를 순차적으로 증가
                
                for course in timetable:
                    cursor.execute(
                        """
                        INSERT INTO timetables (
                            student_id, course_set_id, department, course_name, type, credits, time, location, professor
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            student_id,
                            current_course_set_id,
                            course["department"],
                            course["course_name"],
                            course["type"],
                            course["credits"],
                            course["time"],
                            course["location"],
                            course["professor"],
                        )
                    )
            connection.commit()

        except Exception as e:
            connection.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            cursor.close()
            connection.close()

        # 반환 데이터에 course_set_id 추가
        timetables_with_ids = [
            {"course_set_id": index + max_course_set_id + 1, "timetable": timetable}
            for index, timetable in enumerate(timetables)
        ]

        return {
            "student_id": student_id,
            "message" : "success",
            "timetables": timetables_with_ids,
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No course data found for student_id {student_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/get-timetables/{student_id}", tags=["AI generate TimeTable"])
async def get_timetables(student_id: int):
    """
    student_id 를 던지면 그거에 매핑된 course와 CIFFY comment 반환
    """
    # DB 연결
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # timetables 데이터 검색
        cursor.execute(
            """
            SELECT 
                course_set_id, department, course_name, type, credits, time, location, professor
            FROM timetables
            WHERE student_id = %s
            ORDER BY course_set_id
            """,
            (student_id,)
        )
        timetable_results = cursor.fetchall()

        if not timetable_results:
            raise HTTPException(
                status_code=404,
                detail=f"No timetables found for student_id {student_id}"
            )

        # ciffy_comment에서 관련 댓글 검색
        cursor.execute(
            """
            SELECT 
                question_id AS course_set_id, comment
            FROM ciffy_comment
            WHERE question_id IN (
                SELECT DISTINCT course_set_id FROM timetables WHERE student_id = %s
            )
            ORDER BY question_id, comment
            """,
            (student_id,)
        )
        comment_results = cursor.fetchall()
        print(comment_results)
        comment_list = [entry['comment'] for entry in comment_results]
        print(comment_list)
        # course_set_id에 따라 댓글을 순서대로 매핑
        comments_by_course_set_id = {}
        comment_index = 0  # 댓글 순서 트래킹
        for row in timetable_results:
            course_set_id = row["course_set_id"]
            if comment_index < len(comment_results):
                # 각 course_set_id에 하나씩 댓글 매핑
                comment_row = comment_results[comment_index]
                if comment_row["course_set_id"] == course_set_id:
                    comments_by_course_set_id[course_set_id] = [{"comment": comment_row["comment"]}]
                    comment_index += 1
            else:
                # 댓글이 더 이상 없으면 빈 리스트
                comments_by_course_set_id[course_set_id] = []

        # timetables 데이터를 그룹화 (course_set_id 기준)
        grouped_timetables = {}
        for row in timetable_results:
            course_set_id = row["course_set_id"]
            if course_set_id not in grouped_timetables:
                grouped_timetables[course_set_id] = {"timetable": [], "comments": []}
            grouped_timetables[course_set_id]["timetable"].append({
                "department": row["department"],
                "course_name": row["course_name"],
                "type": row["type"],
                "credits": row["credits"],
                "time": row["time"],
                "location": row["location"],
                "professor": row["professor"]
            })
            # 관련 댓글 추가
            grouped_timetables[course_set_id]["comments"] = comments_by_course_set_id.get(course_set_id, [])
        # 그룹화된 데이터 변환
        saved_timetables = [
            {
                "course_set_id": set_id,
                "timetable": data["timetable"],
            }
            for set_id, data in grouped_timetables.items()
        ]

        return {
            "student_id": student_id,
            "timetables": saved_timetables,
            "comments" : comment_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        cursor.close()
        connection.close()


