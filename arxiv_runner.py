"""
ArXiv 메타데이터 조회 모듈 (공식 arxiv 라이브러리 사용)

Author: Minseok kim
"""

import arxiv
from typing import Dict, Optional
import logging
import os
from prompts import create_summary_user_prompt, create_system_summary_prompt
from langchain_openai import ChatOpenAI
from type import ArXivMetadata

logger = logging.getLogger(__name__)


class ArXivRunner:
    """ArXiv 공식 라이브러리를 사용하여 논문 메타데이터를 조회하는 클래스"""
    
    def __init__(self):
        """ArXivRunner 초기화"""
        self.client = arxiv.Client()
        # OpenAI API 설정
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY", "not-used"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
    
    def get_metadata(self, arxiv_id: str) -> Optional[ArXivMetadata]:
        """
        ArXiv ID로부터 논문 메타데이터를 가져옵니다.
        
        Args:
            arxiv_id: ArXiv 논문 ID (예: "2301.00001" 또는 "cs.AI/2301.00001")
            
        Returns:
            ArXivMetadata: 논문 메타데이터 (title, authors, abstract 포함)
            None: 조회 실패 시
        """
        try:
            # ArXiv ID 정규화 (버전 번호 제거)
            clean_id = arxiv_id.split('v')[0]
            
            # ArXiv 검색 쿼리 생성
            search = arxiv.Search(
                id_list=[clean_id],
                max_results=1
            )
            
            # 논문 검색
            results = list(self.client.results(search))
            
            if not results:
                logger.warning(f"논문을 찾을 수 없습니다: {arxiv_id}")
                return None
            
            paper = results[0]
            
            # 메타데이터 추출
            metadata = {
                'arxiv_id': clean_id,
                'title': paper.title,
                'authors': [author.name for author in paper.authors],
                'abstract': paper.summary,
                'updated': paper.updated.isoformat() if paper.updated else None,
                'categories': paper.categories
            }
            
            logger.info(f"메타데이터 조회 성공: {arxiv_id}")
            return metadata
            
        except arxiv.ArxivError as e:
            logger.error(f"ArXiv API 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"메타데이터 조회 중 오류 발생: {e}")
            return None

    def summary_abstract(self, abstract: str, title: str) -> Optional[str]:
        """
        논문 초록을 요약합니다.
        
        Args:
            abstract: 논문 초록
            title: 논문 제목
            
        Returns:
            str: 요약된 초록 또는 None
        """
        try:
            # 프롬프트 생성
            user_prompt = create_summary_user_prompt(abstract, title)
            system_prompt = create_system_summary_prompt()
            
            # 메시지 구성
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # OpenAI API 호출
            response = self.llm.invoke(messages)
            
            logger.info("초록 요약 완료")
            return response.content
            
        except Exception as e:
            logger.error(f"초록 요약 중 오류 발생: {e}")
            return None
