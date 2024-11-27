import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate

# CSV 파일을 pandas로 읽기
df = pd.read_csv("sejong_data.csv")

# 각 행의 모든 정보를 문자열로 변환
def create_document_content(row):
    content = []
    for column in df.columns:
        content.append(f"{column}: {row[column]}")
    return "\n".join(content)

# 각 행을 Document 객체로 변환
documents = [
    Document(
        page_content=create_document_content(row),
        metadata={"source": "sejong_data.csv", "index": idx}
    ) for idx, row in df.iterrows()
]

# OpenAI 임베딩 생성
embeddings = OpenAIEmbeddings()

# FAISS를 사용하여 벡터 저장소에 데이터 삽입
vector_store = FAISS.from_documents(documents, embeddings)

# 사용자 정의 프롬프트 템플릿 생성
prompt_template = """
다음 context 정보를 사용하여 질문에 답변해주세요.

Context: {context}

질문: {query}

답변 형식:
1. 검색된 강의 수
2. 각 강의의 상세 정보
3. 요약된 정보 (있다면)

답변:
"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "query"]
)

# 질의 응답 체인 만들기
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o", temperature=0),
    chain_type="stuff",
    retriever=vector_store.as_retriever(
        search_kwargs={"k": 5}
    ),
    chain_type_kwargs={
        "prompt": PROMPT,
        "document_variable_name": "context"
    },
    return_source_documents=True
)

def generate_schedule():
    print("사용자 맞춤 시간표 생성 중...")
    question = "사용자 맞춤 시간표를 작성해주세요!"
    # qa_chain을 invoke 메소드로 호출하고 query 키를 사용
    response = qa_chain.invoke({"query": question})
    return response

# 여러 질문 테스트를 위한 함수
def ask_questions(questions):
    for q in questions:
        print(f"\n질문: {q}")
        response = qa_chain.invoke({"query": q})
        print(f"응답: {response}")
        print("-" * 80)

# 실행
schedule = generate_schedule()
print("\n응답:")
print(schedule)