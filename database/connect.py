import mysql.connector
import os
from dotenv import load_dotenv, find_dotenv

# 환경 변수 로드
load_dotenv(find_dotenv(), override=True)

# 데이터베이스 연결 정보
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))  # 기본 포트는 3306

def get_db_connection():
    """
    MySQL 데이터베이스 연결을 생성합니다.
    """
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
        )
        return connection
    except mysql.connector.Error as err:
        raise RuntimeError(f"Database connection failed: {err}")
