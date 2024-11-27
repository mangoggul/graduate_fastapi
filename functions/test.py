import pandas as pd
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate

class CourseRecommender:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)
        self.user_preferences = {}
        self.setup_qa_chain()
    
    def create_document_content(self, row):
        content = []
        for column in self.df.columns:
            content.append(f"{column}: {row[column]}")
        return "\n".join(content)

    def setup_qa_chain(self):
        # Document 객체 생성
        documents = [
            Document(
                page_content=self.create_document_content(row),
                metadata={"source": "sejong_data.csv", "index": idx}
            ) for idx, row in self.df.iterrows()
        ]

        # 임베딩 및 벡터 저장소 설정
        embeddings = OpenAIEmbeddings()
        self.vector_store = FAISS.from_documents(documents, embeddings)

        # 프롬프트 템플릿 수정 - 사용자 선호도 정보 포함
        prompt_template = """
다음 context 정보와 사용자 선호도 정보를 사용하여 질문에 답변해주세요.

Context: {context}

사용자 선호도 정보:
{user_preferences}

질문: {question}

답변 형식:
1. 검색된 강의 수
2. 각 강의의 상세 정보 (사용자 선호도를 고려하여 추천 순위 부여)
3. 추천 이유 (사용자 선호도와의 연관성 포함)

답변:
"""
        self.PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question", "user_preferences"]
        )

        # QA 체인 설정
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model="gpt-4o", temperature=0),
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 5}),
            chain_type_kwargs={"prompt": self.PROMPT}
        )

    def add_user_preference(self, question, answer, weight=1.0):
        """사용자의 응답을 preferences에 추가"""
        self.user_preferences[question] = {
            "answer": answer,
            "weight": weight
        }
        
    def format_user_preferences(self):
        """사용자 선호도 정보를 문자열로 포맷팅"""
        if not self.user_preferences:
            return "사용자 선호도 정보가 없습니다."
        
        formatted = []
        for question, data in self.user_preferences.items():
            formatted.append(f"질문: {question}")
            formatted.append(f"답변: {data['answer']}")
            formatted.append(f"가중치: {data['weight']}")
        return "\n".join(formatted)

    def generate_recommendations(self, query):
        """사용자 선호도를 반영한 추천 생성"""
        try:
            response = self.qa_chain({
                "query": query,
                "user_preferences": self.format_user_preferences()
            })
            return response
        except Exception as e:
            print(f"추천 생성 중 에러 발생: {str(e)}")
            return None

# 사용 예시
def main():
    # 추천 시스템 초기화
    recommender = CourseRecommender("sejong_data.csv")
    
    # 사용자 선호도 수집 예시
    sample_questions = [
        ("당신의 선호하는 수업 시간대는 언제인가요?", "오전 9시-12시", 0.8),
        ("선호하는 강의 형식은 무엇인가요? (온라인/오프라인)", "오프라인", 0.9),
        ("특정 교수님의 강의를 선호하시나요?", "김교수님", 0.7),
        ("선호하는 과목 분야가 있나요?", "프로그래밍", 1.0)
    ]
    
    # 사용자 선호도 정보 추가
    for question, answer, weight in sample_questions:
        recommender.add_user_preference(question, answer, weight)
    
    # 추천 생성
    recommendations = recommender.generate_recommendations(
        "내 선호도에 맞는 시간표를 추천해주세요."
    )
    
    if recommendations:
        print("\n추천 결과:")
        print(recommendations)

if __name__ == "__main__":
    main()