"""
논문 관련 유틸리티 함수들

Author: Minseok kim
"""

import re
from typing import Optional, List, Union
from type import ContentChunk


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


def split_text_and_images(s: Union[str, List[str]]) -> List[ContentChunk]:
    """
    주어진 문자열 또는 문자열 리스트를 이미지 토큰과 텍스트 조각으로 분리하여 반환합니다.
    반환 형식: [{"type": "text"|"img", "content": "..."} ...] 입니다.
    - 지원 형식:
      1) Markdown 이미지:  ![alt](url "optional title")
      2) HTML 이미지:     <img src="...">
    
    Args:
        s: 처리할 문자열 또는 문자열 리스트
        
    Returns:
        List[ContentChunk]: 분리된 텍스트와 이미지 조각들의 리스트
    """
    # 입력이 리스트인 경우 문자열로 합치기
    if isinstance(s, list):
        input_text = '\n'.join(s)
    else:
        input_text = s
    
    # Markdown 이미지: ![alt](url "title")
    md_img = r'!\[[^\]]*?\]\([^\s)]+(?:\s+"[^"]*")?\)'
    # HTML 이미지: <img src="...">
    html_img = r'<img\s+[^>]*src=["\'][^"\']+["\'][^>]*>'

    # 분리용 패턴 (이미지 토큰을 캡처 그룹으로 포함해 split)
    splitter = re.compile(rf'({md_img}|{html_img})', flags=re.IGNORECASE)

    # 전체 매치 판별용 패턴 (조각이 이미지 자체인지 확인)
    md_full = re.compile(rf'^{md_img}$')
    html_full = re.compile(rf'^{html_img}$', flags=re.IGNORECASE)

    parts = [p for p in splitter.split(input_text) if p and p.strip()]

    out: List[ContentChunk] = []
    for p in parts:
        piece = p.strip()
        if md_full.match(piece) or html_full.match(piece):
            out.append({"type": "img", "content": piece})
        else:
            out.append({"type": "text", "content": piece})
    return out
