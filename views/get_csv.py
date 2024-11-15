import pandas as pd
from fastapi import HTTPException
from typing import Union
from io import BytesIO
from fastapi import UploadFile

def read_excel_from_file(file: UploadFile, sheet_name: Union[str, None] = None):
    """
    업로드된 엑셀 파일을 읽어 지정된 시트를 처리한 후 JSON 형식으로 데이터를 반환합니다.
    시트 이름이 지정되지 않은 경우 첫 번째 시트만 반환합니다.
    """
    try:
        # 엑셀 파일을 데이터프레임으로 읽기
        excel_data = pd.read_excel(BytesIO(file.file.read()), sheet_name=sheet_name)
        
        # Excel 데이터를 DataFrame으로 로드했는지 확인
        if isinstance(excel_data, dict):
            # 여러 시트가 있는 경우 Excel 데이터는 dict로 반환될 수 있음
            if sheet_name is not None:
                # 특정 시트를 지정한 경우, 해당 시트의 DataFrame을 가져오기
                df = excel_data.get(sheet_name)
                if df is None:
                    raise ValueError("지정한 시트 이름을 찾을 수 없습니다.")
            else:
                # 시트 이름을 지정하지 않은 경우 첫 번째 시트를 선택
                first_sheet_name = list(excel_data.keys())[0]
                df = excel_data[first_sheet_name]
        else:
            # 단일 시트만 있는 경우 직접 DataFrame으로 반환됨
            df = excel_data

        # 컬럼 이름 변경
        df.columns = [
            "학기순번",      # 기이수성적
            "년도",          # Unnamed: 1
            "학기",          # Unnamed: 2
            "과목코드",       # Unnamed: 3
            "과목명",        # Unnamed: 4
            "이수구분",       # Unnamed: 5
            "비고1",         # Unnamed: 6
            "비고2",         # Unnamed: 7
            "학점",          # Unnamed: 8
            "성적유형",       # Unnamed: 9
            "성적등급",       # Unnamed: 10
            "평점",          # Unnamed: 11
            "학과코드"       # Unnamed: 12
        ]
        
        # NaN 및 무한대 값을 처리
        df = df.fillna('').replace([float('inf'), float('-inf')], 0)
        
        # JSON으로 변환
        data = df.to_dict(orient="records")
        
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
