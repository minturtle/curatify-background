"""
논문 관련 유틸리티 함수들

Author: Minseok kim
"""

import re
from typing import Optional


def convert_arxiv_url_to_pdf(arxiv_url: str) -> Optional[str]:
    """
    ArXiv 논문 URL을 PDF 다운로드 URL로 변환합니다.
    
    Args:
        arxiv_url: ArXiv 논문 URL (예: "https://arxiv.org/abs/2301.00001")
        
    Returns:
        str: PDF 다운로드 URL (예: "https://arxiv.org/pdf/2301.00001.pdf")
        None: 변환 실패 시
    """
    try:
        # ArXiv URL 패턴 매칭
        abs_pattern = r'https://arxiv\.org/abs/([^/]+)'
        match = re.search(abs_pattern, arxiv_url)
        
        if match:
            paper_id = match.group(1)
            # 버전 번호 제거 (v1, v2 등)
            clean_id = paper_id.split('v')[0]
            return f"https://arxiv.org/pdf/{clean_id}.pdf"
        
        # 이미 PDF URL인 경우 그대로 반환
        if arxiv_url.endswith('.pdf'):
            return arxiv_url
            
        return None
        
    except Exception:
        return None
