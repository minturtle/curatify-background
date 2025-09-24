from redis_subscriber import RedisSubscriber
import os
from dotenv import load_dotenv
from type import PaperMessage, PaperData
import logging
import json
from arxiv_runner import ArXivRunner
from mongo_service import MongoService
from typing import Optional
from bson import ObjectId
from utils.paper import convert_arxiv_url_to_pdf

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



def confirm_paper_abstract(message: PaperMessage) -> Optional[str]:
    """
    논문 초록 요약 정보를 확인하고 저장하는 함수입니다.
    
    Args:
        message: 논문 초록 요약 정보를 확인하고 저장합니다.
        이미 존재 하는 경우: paper_object_id를 반환합니다.
        존재하지 않는 경우: 논문 초록 요약 정보를 저장하고 paper_object_id를 반환합니다.
    Returns:
        doc_id: 저장된 논문 초록 요약 정보의 ID
    """
    paper_object_id = mongo_service.is_paper_exists(message["paper_id"])
    if paper_object_id:
        logging.info(f"논문이 이미 존재함 - 논문 파싱 진행하지 않음.: {message['paper_id']}")
        return paper_object_id

    # ArXiv에서 논문 메타데이터 조회
    paper_metadata = arxiv_runner.get_metadata(message["paper_id"])
    if not paper_metadata:
        logging.error(f"논문 메타데이터 조회 실패: {message['paper_id']}")
        return None
    
    # 논문 초록 요약
    summary = arxiv_runner._summary_abstract(paper_metadata["abstract"], paper_metadata["title"])
    if not summary:
        logging.error(f"논문 요약 실패: {message['paper_id']}")
        return None
    
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
    return doc_id

@subscriber.subscribe("paper:abstract")
def handle_abstract_queue(msg: str):
    try:
        data = json.loads(msg)
        message: PaperMessage = {**data}
        
        paper_object_id = confirm_paper_abstract(message)
        
        if paper_object_id:
            mongo_service.save_user_paper_abstract(ObjectId(message["user_id"]), paper_object_id)

        logging.info(f"논문 초록 요약 정보 저장 완료: {message['paper_id']}")

    except Exception as e:
        logging.error(f"논문 처리 중 오류 발생: {e}")

@subscriber.subscribe("paper:analysis")
def handle_content_queue(msg: str):
    try:
        data = json.loads(msg)
        message: PaperMessage = {**data}
        paper_data = mongo_service.find_by_id(message["paper_id"])
        
        if not paper_data:
            logging.info(f"논문 데이터 조회 실패: {message['paper_id']}")
            return
        paper_content = arxiv_runner.analyze_paper_content(convert_arxiv_url_to_pdf(paper_data["url"]))
        
        logging.info(paper_content)
        if not paper_content:
            logging.error(f"논문 콘텐츠 요약 실패: {message['paper_id']}")
            return

    except Exception as e:
        logging.error(f"논문 처리 중 오류 발생: {e}")


subscriber.start()