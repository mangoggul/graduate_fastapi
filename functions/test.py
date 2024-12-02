import random
import pandas as pd


def parse_courses(file_path, category):
    """
    파일에서 특정 학과의 강의를 파싱합니다.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    courses = []
    for line in lines:
        if line.startswith(category):
            parts = line.split(",")
            if len(parts) >= 7:  # 최소 데이터 검증
                try:
                    courses.append({
                        "department": parts[0].strip(),
                        "course_name": parts[1].strip(),
                        "type": parts[2].strip(),
                        "credits": float(parts[3].strip()),
                        "time": parts[4].strip(),
                        "location": parts[5].strip(),
                        "professor": parts[6].strip()
                    })
                except ValueError:
                    continue  # 학점이 비어 있는 경우 스킵
    return courses


def select_courses(courses, num_courses, target_credits):
    """
    주어진 강의 목록에서 일정 개수와 학점을 만족하도록 랜덤 선택.
    """
    selected_courses = []
    total_credits = 0
    while len(selected_courses) < num_courses and total_credits < target_credits:
        course = random.choice(courses)
        if course not in selected_courses:
            selected_courses.append(course)
            total_credits += course["credits"]
    return selected_courses


def generate_timetable(file_path):
    """
    강의 데이터를 파싱하고, 랜덤으로 강의를 선택해 시간표를 생성합니다.
    """
    humanity_courses = parse_courses(file_path, "대양휴머니티칼리지")
    cs_courses = parse_courses(file_path, "컴퓨터공학과")
    sw_courses = parse_courses(file_path, "소프트웨어학과")

    selected_humanity = select_courses(humanity_courses, num_courses=3, target_credits=9.0)
    selected_cs = select_courses(cs_courses, num_courses=2, target_credits=6.0)
    selected_sw = select_courses(sw_courses, num_courses=2, target_credits=6.0)

    combined_timetable = selected_humanity + selected_cs + selected_sw
    return combined_timetable


def generate_timetables(file_path, count):
    """
    여러 개의 시간표를 생성합니다.
    """
    timetables = []
    for _ in range(count):
        timetable = generate_timetable(file_path)
        timetables.append(timetable)
    return timetables


if __name__ == "__main__":
    # 테스트 실행
    file_path = "files.txt"  # 강의 데이터가 담긴 파일 경로
    count = 3  # 생성할 시간표 수
    timetables = generate_timetables(file_path, count)

    # 결과 출력
    for idx, timetable in enumerate(timetables, start=1):
        print(f"\n=== Generated Timetable {idx} ===")
        df = pd.DataFrame(timetable)
        print(df)
