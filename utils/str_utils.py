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
    주어진 문자열 또는 문자열 리스트를 마크다운 이미지 토큰과 텍스트 조각으로 분리하여 반환합니다.
    반환 형식: [{"type": "text"|"img", "content": "..."} ...] 입니다.
    - 지원 형식:
      Markdown 이미지:  ![alt](url "optional title")
    
    Args:
        s: 처리할 문자열 또는 문자열 리스트
        
    Returns:
        List[ContentChunk]: 분리된 텍스트와 마크다운 이미지 조각들의 리스트
    """
    # 입력이 리스트인 경우 문자열로 합치기
    if isinstance(s, list):
        input_text = '\n'.join(s)
    else:
        input_text = s
    
    # Markdown 이미지: ![alt](url "title")
    md_img = r'!\[[^\]]*?\]\([^\s)]+(?:\s+"[^"]*")?\)'

    # 분리용 패턴 (마크다운 이미지 토큰을 캡처 그룹으로 포함해 split)
    splitter = re.compile(rf'({md_img})', flags=re.IGNORECASE)

    # 전체 매치 판별용 패턴 (조각이 마크다운 이미지 자체인지 확인)
    md_full = re.compile(rf'^{md_img}$')

    parts = [p for p in splitter.split(input_text) if p and p.strip()]

    out: List[ContentChunk] = []
    for p in parts:
        piece = p.strip()
        if md_full.match(piece):
            out.append({"type": "img", "content": piece})
        else:
            out.append({"type": "text", "content": piece})
    return out


def extract_image_url_from_markdown(markdown_img: str) -> Optional[str]:
    """
    마크다운 이미지 태그에서 이미지 URL을 추출합니다.
    
    Args:
        markdown_img: 마크다운 이미지 태그 (예: "![alt text](https://example.com/image.png)")
        
    Returns:
        str: 추출된 이미지 URL (예: "https://example.com/image.png")
        None: URL 추출 실패 시
    """
    try:
        # 마크다운 이미지 패턴: ![alt](url "optional title")
        pattern = r'!\[[^\]]*?\]\(([^\s)]+)(?:\s+"[^"]*")?\)'
        match = re.search(pattern, markdown_img)
        
        if match:
            return match.group(1)
        
        return None
        
    except Exception:
        return None


def replace_image_url_in_markdown(markdown_img: str, new_url: str) -> str:
    """
    마크다운 이미지 태그의 URL을 새로운 URL로 대체합니다.
    
    Args:
        markdown_img: 마크다운 이미지 태그 (예: "![alt text](https://old.com/image.png)")
        new_url: 새로운 이미지 URL (예: "https://new.com/image.png")
        
    Returns:
        str: URL이 대체된 마크다운 이미지 태그 (예: "![alt text](https://new.com/image.png)")
    """
    try:
        # 마크다운 이미지 패턴: ![alt](url "optional title")
        pattern = r'(!\[[^\]]*?\]\()([^\s)]+)((?:[^)]*)?\))'
        match = re.search(pattern, markdown_img)
        
        if match:
            prefix = match.group(1)  # ![alt](
            suffix = match.group(3)  # "title") 또는 )
            return f"{prefix}{new_url}{suffix}"
        
        # 매치되지 않으면 원본 반환
        return markdown_img
        
    except Exception:
        return markdown_img