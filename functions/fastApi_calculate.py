import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List, Dict, Any
from collections import defaultdict
from io import BytesIO

app = FastAPI()

# Helper functions
def to_zip_list(list_1, list_2):
    return [[a, b] for a, b in zip(list_1, list_2)]

def list_to_query(list_):
    # Assuming you have a DB model and ORM logic in place
    al = AllLecture.objects.filter(subject_num__in=list_)
    return list(al.values())

def make_dic(my_list):
    my_list.sort()
    dic = defaultdict(lambda: -1)
    for s_num in my_list:
        dic[s_num]
        sg = SubjectGroup.objects.filter(subject_num=s_num)
        if sg.exists():
            dic[s_num] = sg[0].group_num
    return dic

def make_recommend_list(my_dic, dic):
    my_dic_ = my_dic.copy()
    dic_ = dic.copy()
    check = dic.copy()
    for k in check.keys():
        check[k] = 0
    
    for s_num in my_dic_.keys():
        if s_num in dic_.keys():
            check[s_num] = 1
            dic_.pop(s_num)
        else:
            g_num = my_dic_[s_num]
            for k, v in dic_.items():
                if v == g_num:
                    s_num = k
            if g_num != -1 and (g_num in dic_.values()):
                check[s_num] = 1
                dic_.pop(s_num)

    recommend = []
    for s_num in dic_.keys():
        nl = NewLecture.objects.filter(subject_num=s_num)
        if nl.exists():
            recommend.append(nl[0].subject_num)
        else:
            g_num = dic_[s_num]
            if g_num == -1:
                recommend.append(s_num)
            else:
                sg = SubjectGroup.objects.filter(group_num=g_num)
                for s in sg:
                    nl2 = NewLecture.objects.filter(subject_num=s.subject_num)
                    if nl2.exists():
                        recommend.append(nl2[0].subject_num)
    return recommend, list(check.values())

# FastAPI endpoint to read and analyze Excel
@app.post("/analyze-excel/")
async def analyze_excel(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        # Read Excel file into DataFrame
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents), engine='openpyxl')

        # Process your dataframe like you would in Django (adapt as needed)
        data = df[['subject_num', 'subject_name', 'classification', 'selection', 'grade']]

        # Example: Change column names
        data.rename(columns={'subject_num': '학수번호', 'subject_name': '교과목명', 'classification': '이수구분', 'selection': '선택영역', 'grade': '학점'}, inplace=True)
        
        # Add more processing here as needed...
        
        # For example: Filtering
        df_me = data[data['이수구분'].isin(['전필'])]
        df_ms = data[data['이수구분'].isin(['전선'])]
        
        # Return processed data
        return {"message": "File processed successfully", "data": data.to_dict(orient='records')}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred while processing the file: {str(e)}")

# Example endpoint for a recommendation function
@app.post("/recommend-lectures/")
async def recommend_lectures(user_id: str) -> Dict[str, Any]:
    # Replace with real data fetching logic from DB
    # Simulating some logic here
    my_dic = {'subject1': 1, 'subject2': 2}  # Example dictionary
    dic = {'subject1': 1, 'subject3': 3}  # Example dictionary

    recommend, check = make_recommend_list(my_dic, dic)
    
    return {"recommendations": recommend, "check": check}

