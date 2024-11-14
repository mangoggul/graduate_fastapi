from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from fastapi import FastAPI, Depends

# Setup database URL (replace with your own database URL)
DATABASE_URL = "postgresql://user:password@localhost/dbname"

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# ------------------------------------- ( 테스트용 테이블 ) -------------------------------------

class TestTable(Base):
    __tablename__ = 'test_table'

    num = Column(Integer, primary_key=True, index=True)
    text = Column(String(45))

class TestAllLecture(Base):
    __tablename__ = 'test_all_lecture'

    subject_num = Column(String(10), primary_key=True)
    subject_name = Column(String(70))
    classification = Column(String(45))
    selection = Column(String(45), nullable=True)
    grade = Column(Integer)

class TestNewLecture(Base):
    __tablename__ = 'test_new_lecture'

    subject_num = Column(String(10), primary_key=True)

# ------------------------------------- ( 회원 정보 테이블 ) -------------------------------------

class NewUserInfo(Base):
    __tablename__ = 'new_user_info'

    student_id = Column(String(10), primary_key=True)
    last_update_time = Column(String(45), nullable=True)
    register_time = Column(String(45))
    password = Column(String(100))
    year = Column(Integer)
    major = Column(String(45))
    sub_major = Column(String(45), nullable=True)
    major_status = Column(String(10))
    name = Column(String(45))
    book = Column(String(45))
    eng = Column(String(45))
    mypage_json = Column(JSONB, nullable=True)
    result_json = Column(JSONB, nullable=True)
    en_result_json = Column(JSONB, nullable=True)

class UserGrade(Base):
    __tablename__ = 'user_grade'

    index = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(10))
    major = Column(String(45), nullable=True)
    year = Column(String(10))
    semester = Column(String(45))
    subject_num = Column(String(10))
    subject_name = Column(String(70))
    classification = Column(String(45))
    selection = Column(String(45), nullable=True)
    grade = Column(Float)

class DeleteAccountLog(Base):
    __tablename__ = 'delete_account_log'

    index = Column(Integer, primary_key=True, index=True)
    major = Column(String(45))
    year = Column(Integer)
    name = Column(String(45))
    register_time = Column(String(45))
    delete_time = Column(String(45))

class UserInfo(Base):
    __tablename__ = 'user_info'

    student_id = Column(String(10), primary_key=True)
    year = Column(Integer)
    major = Column(String(45))
    name = Column(String(45))
    book = Column(String(45))
    eng = Column(Integer)

# ------------------------------------- ( 검사 기준 테이블 ) -------------------------------------

class Standard(Base):
    __tablename__ = 'standard'

    index = Column(Integer, primary_key=True, index=True)
    user_year = Column(Integer)
    user_dep = Column(String(50))
    sum_score = Column(Integer)
    major_essential = Column(Integer)
    major_selection = Column(Integer)
    core_essential = Column(Integer)
    core_selection = Column(Integer)
    la_balance = Column(Integer)
    basic = Column(Integer)
    ce_list = Column(String(100))
    cs_list = Column(String(100))
    b_list = Column(String(100))
    english = Column(JSONB)
    sum_eng = Column(Integer)
    pro = Column(Integer, nullable=True)
    bsm = Column(Integer, nullable=True)
    eng_major = Column(Integer, nullable=True)
    build_sel_num = Column(Integer, nullable=True)
    pro_ess_list = Column(String(100), nullable=True)
    bsm_ess_list = Column(String(100), nullable=True)
    bsm_sel_list = Column(String(100), nullable=True)
    build_start = Column(String(10), nullable=True)
    build_sel_list = Column(String(100), nullable=True)
    build_end = Column(String(10), nullable=True)
    eng_major_list = Column(String(200), nullable=True)

# ------------------------------------- ( 강의 정보 테이블 ) -------------------------------------

class AllLecture(Base):
    __tablename__ = 'all_lecture'

    subject_num = Column(String(10), primary_key=True)
    subject_name = Column(String(70))
    classification = Column(String(45))
    selection = Column(String(45), nullable=True)
    grade = Column(Float)

class NewLecture(Base):
    __tablename__ = 'new_lecture'

    subject_num = Column(String(10), primary_key=True)

# ------------------------------------- ( 브라우저 세션/쿠키 ) -------------------------------------

class DjangoSession(Base):
    __tablename__ = 'django_session'

    session_key = Column(String(40), primary_key=True)
    session_data = Column(String)
    expire_date = Column(DateTime)

class VisitorCount(Base):
    __tablename__ = 'visitor_count'

    visit_date = Column(String(45), primary_key=True)
    visit_count = Column(Integer)
    user_count = Column(Integer, nullable=True)
    signup_count = Column(Integer, nullable=True)
    delete_count = Column(Integer, nullable=True)

# ------------------------------------- ( 매핑 테이블 ) -------------------------------------

class Major(Base):
    __tablename__ = 'major'

    index = Column(Integer, primary_key=True)
    college = Column(String(45))
    department = Column(String(45), nullable=True)
    major = Column(String(45))
    sub_major = Column(String(45), nullable=True)

class SubjectGroup(Base):
    __tablename__ = 'subject_group'

    subject_num = Column(String(10), primary_key=True)
    group_num = Column(String(10))

class ChangedClassification(Base):
    __tablename__ = 'changed_classification'

    index = Column(Integer, primary_key=True)
    subject_num = Column(String(10))
    year = Column(Integer)
    classification = Column(String(10))

# Create tables in the database
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
