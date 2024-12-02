import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from typing import List, Dict



def read_course_data(file_path: str) -> List[Document]:
    """
    텍스트 파일에서 코스 데이터를 읽어 Document 객체 리스트로 변환
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # 텍스트를 적절한 크기로 나누어 Document 객체로 변환
            documents = [Document(page_content=content)]
        return documents
    except FileNotFoundError:
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        raise Exception(f"파일 읽기 중 오류 발생: {str(e)}")

def create_qa_chain(documents: List[Document]) -> RetrievalQA:
    """
    QA 체인 생성
    """
    # OpenAI 임베딩 생성
    embeddings = OpenAIEmbeddings()
    
    # FAISS 벡터 저장소 생성
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # 프롬프트 템플릿 정의
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
    
    # QA 체인 생성
    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model="gpt-4o", temperature=0),  # 모델명 수정
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
    
    return qa_chain

def generate_schedule(qa_chain: RetrievalQA) -> Dict:
    """
    시간표 생성
    """
    print("사용자 맞춤 시간표 생성 중...")
    question = "사용자 맞춤 시간표를 작성해주세요!"
    try:
        response = qa_chain.invoke({"query": question})
        return response
    except Exception as e:
        print(f"시간표 생성 중 오류 발생: {str(e)}")
        return None

def ask_questions(qa_chain: RetrievalQA, questions: List[str]) -> None:
    """
    여러 질문에 대한 응답 생성
    """
    for q in questions:
        try:
            print(f"\n질문: {q}")
            response = qa_chain({"query": q})
            print(f"응답: {response}")
            print("-" * 80)
        except Exception as e:
            print(f"질문 처리 중 오류 발생: {str(e)}")

def main():
    try:
        # 파일 경로 설정
        file_path = "../txt/course.txt"
        
        # 코스 데이터 읽기
        documents = read_course_data(file_path)
        
        # QA 체인 생성
        qa_chain = create_qa_chain(documents)
        
        # 시간표 생성
        schedule = generate_schedule(qa_chain)
        if schedule:
            print("\n생성된 시간표:")
            print(schedule)
        
        
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()