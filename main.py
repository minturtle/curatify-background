from redis_subscriber import RedisSubscriber
import os
from dotenv import load_dotenv
from type import PaperAbstractMessage, PaperData
import logging
import json
from arxiv_runner import ArXivRunner
from mongo_service import MongoService

logging.basicConfig(level=logging.INFO)  # DEBUG 로그도 보이도록 설정


load_dotenv()
redis_url = os.getenv("REDIS_URL")
redis_username = os.getenv("REDIS_USERNAME")
redis_password = os.getenv("REDIS_PASSWORD")

subscriber_kwargs = {
    "redis_url": redis_url,
}
if redis_username and redis_password:
    subscriber_kwargs["username"] = redis_username
    subscriber_kwargs["password"] = redis_password

subscriber = RedisSubscriber(**subscriber_kwargs)

arxiv_runner = ArXivRunner()
mongo_service = MongoService()

@subscriber.subscribe("paper:abstract")
def handle_abstract_queue(msg: str):
    try:
        data = json.loads(msg)
        message: PaperAbstractMessage = {**data}
        
        # 논문 존재 여부 확인
        if mongo_service.is_paper_exists(message["paper_id"]):
            logging.info(f"논문이 이미 존재함 - 논문 파싱 종료: {message['paper_id']}")
            return
        
        # ArXiv에서 논문 메타데이터 조회
        paper_metadata = arxiv_runner.get_metadata(message["paper_id"])
        if not paper_metadata:
            logging.error(f"논문 메타데이터 조회 실패: {message['paper_id']}")
            return
        
        # 논문 초록 요약
        summary = arxiv_runner.summary_abstract(paper_metadata["abstract"], paper_metadata["title"])
        if not summary:
            logging.error(f"논문 요약 실패: {message['paper_id']}")
            return
        
        # MongoDB에 저장할 논문 데이터 구성
        paper_data: PaperData = {
            "title": paper_metadata["title"],
            "summary": summary,
            "contentBlocks": [],
            "url": f"https://arxiv.org/abs/{paper_metadata['arxiv_id']}",
            "authors": paper_metadata["authors"],
            "categories": paper_metadata["categories"],
            "abstract": paper_metadata["abstract"],
            "lastPublishDate": paper_metadata["updated"]
        }
        
        # MongoDB에 저장
        doc_id = mongo_service.save_paper(paper_data)
        if doc_id:
            logging.info(f"논문 저장 완료: {paper_metadata['title']} (ID: {doc_id})")
        else:
            logging.error(f"논문 저장 실패: {paper_metadata['title']}")
            
    except Exception as e:
        logging.error(f"논문 처리 중 오류 발생: {e}")
subscriber.start()