"""
MongoDB 서비스 모듈

Author: Minseok kim
"""

import os
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import logging
from datetime import datetime
from type import PaperData

logger = logging.getLogger(__name__)


class MongoService:
    """논문 데이터베이스 레포지토리"""
    
    def __init__(self):
        """
        레포지토리 초기화
        
        Args:
            mongo_db_url: MongoDB 연결 URL (기본값: 환경변수에서 가져옴)
        """
        # MongoDB 연결 URL 설정
        mongo_db_url = os.getenv("MONGODB_URL")
        
        # 데이터베이스 이름 추출 또는 환경변수에서 가져오기
        database_name = os.getenv("MONGODB_DATABASE")
        
        # MongoDB 클라이언트 연결
        self.client = MongoClient(mongo_db_url)
        self.db = self.client[database_name]
        self.collection = self.db.papers
        self.user_collection = self.db.user_paper_abstracts
        # 연결 테스트
        try:
            self.client.admin.command('ping')
            logger.info(f"MongoDB 연결 성공: {database_name}")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise
    
    
    def save_paper(self, paper_data: PaperData) -> Optional[str]:
        """
        논문 데이터를 저장합니다.
        
        Args:
            paper_data: 논문 데이터 (PaperData 타입)
            
        Returns:
            str: 저장된 문서의 ID 또는 None
        """
        try:
            # 저장할 문서 구성
            document = {
                "title": paper_data.get("title", ""),
                "summary": paper_data.get("summary", ""),
                "contentBlocks": paper_data.get("contentBlocks", []),
                "url": paper_data.get("url", ""),
                "authors": paper_data.get("authors", []),
                "categories": paper_data.get("categories", []),
                "abstract": paper_data.get("abstract", ""),
                "lastPublishDate": paper_data.get("lastPublishDate"),
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            

            # 새 문서 삽입
            result = self.collection.insert_one(document)
            logger.info(f"논문 저장됨: {paper_data.get('title', 'Unknown')}")
            return result.inserted_id
                
        except Exception as e:
            logger.error(f"논문 저장 실패: {e}")
            return None
    
    def is_paper_exists(self, arxiv_id: str) -> bool:
        """
        ArXiv ID로 논문이 존재하는지 확인합니다. (URL 기반 체크)
        
        Args:
            arxiv_id: ArXiv 논문 ID
            
        Returns:
            id: 논문의 ObjectId
        """
        try:
            # ArXiv ID로 URL 생성
            url = f"https://arxiv.org/abs/{arxiv_id}"
            
            # URL로 논문 존재 확인
            paper = self.collection.find_one({"url": url})
            
            exists = paper is not None
            if exists:
                logger.info(f"논문 존재함: {arxiv_id} (URL: {url})")
            else:
                logger.info(f"논문 존재하지 않음: {arxiv_id} (URL: {url})")
            
            return paper["_id"] if paper else None
            
        except Exception as e:
            logger.error(f"논문 존재 확인 실패: {e}")
            return False
    
    def save_user_paper_abstract(self, user_id: str, paper_id: str) -> Optional[str]:
        """    
        사용자 논문 초록 추가 정보를 저장합니다.
        
        Args:
            user_id: 사용자 ID
            paper_id: 논문 ID
            abstract: 논문 초록
        """    
        try:
            self.user_collection.insert_one({"user_id": user_id, "paper_id": paper_id})
            logger.info(f"사용자 논문 초록 추가 정보 저장됨: {user_id} (논문 ID: {paper_id})")
            return True
        except Exception as e:
            logger.error(f"사용자 논문 초록 추가 정보 저장 실패: {e}")
            return False


    def close(self):
        """MongoDB 연결 종료"""
        if self.client:
            self.client.close()
            logger.info("MongoDB 연결 종료됨")
    
