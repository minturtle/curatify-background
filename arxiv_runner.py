"""
ArXiv 메타데이터 조회 모듈 (공식 arxiv 라이브러리 사용)

Author: Minseok kim
"""

import arxiv

from typing import Optional, Dict, Any, List
import logging
import os
import tempfile
from pathlib import Path
from prompts import create_summary_user_prompt, create_system_summary_prompt, create_analyze_paper_content_prompt
from langchain_openai import ChatOpenAI
from type import ArXivMetadata, ContentChunk, ContentAnalysisResult
import requests
from io import BytesIO

from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat, DocumentStream

from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
import markdown_to_json
from uuid import uuid4
from utils.str_utils import split_text_and_images
from file_service import upload_file_to_oci
from utils.str_utils import extract_image_url_from_markdown, replace_image_url_in_markdown

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

    def analyze_paper_content(self, pdf_url: str) -> List[ContentAnalysisResult]:
        """
        논문 본문을 요약/정리합니다.
        
        Args:
            pdf_url: 논문 PDF 파일 URL
            
        Returns:
            List[ContentAnalysisResult]: 논문 본문 요약/정리 결과
        """
        try:

            logging.info(f"논문 본문 요약/정리 시작: {pdf_url}")

            pdf_bytes = self._read_pdf_to_binary(pdf_url)

            temp_file_name = str(uuid4()) + ".pdf"
            doc_stream = DocumentStream(
                name=temp_file_name,
                stream=pdf_bytes,
            )

            json_data = self._parse_pdf_to_json(doc_stream)


            result_list: List[ContentAnalysisResult] = [
                {
                    "order": idx + 1,
                    "contentTitle": title,
                    "content": self._create_analyzed_content(split_text_and_images(content))
                }
                for idx, (title, content) in enumerate(json_data.items())
            ]
            return result_list

        except Exception as e:
            logger.error(f"논문 본문 요약/정리 중 오류 발생: {e}")
            return []
        finally:
            logging.info(f"논문 본문 요약/정리 완료: {pdf_url}")



    def _read_pdf_to_binary(self, pdf_url: str) -> BytesIO:
        """
        웹으로 부터 PDF 파일을 바이트 스트림으로 읽어옵니다.
        
        Args:
            pdf_url: PDF 파일 URL
            
        Returns:
            BytesIO: PDF 파일 바이트 스트림
        """
        response = requests.get(pdf_url)
        response.raise_for_status()
        
        if response.headers.get('content-type') != 'application/pdf':
            logger.error(f"PDF가 아닌 콘텐츠 타입: {response.headers.get('content-type')}")
            raise ValueError("PDF 파일이 아닙니다")

        pdf_bytes = BytesIO(response.content)
        return pdf_bytes

    def _parse_pdf_to_json(self, doc_stream: DocumentStream) -> Dict[str, Any]:
        """
        PDF를 JSON으로 변환합니다.
        
        Args:
            doc_stream: DocumentStream
            
        Returns:
            Dict[str, Any]: JSON 데이터
        """
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            temp_md_file_name = str(uuid4()) + ".md"

            # 이미지 생성 옵션 (페이지/그림/표 이미지 생성)
            pipe_opts = PdfPipelineOptions()
            pipe_opts.images_scale = 2.0                  # 해상도(1 ~= 72 DPI)
            pipe_opts.generate_page_images = True
            pipe_opts.generate_picture_images = True

            conv = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipe_opts)}
            )
            res = conv.convert(doc_stream)

            # doc_stream의 name을 사용하여 stem 생성
            stem = Path(doc_stream.name).stem

            # 1) 페이지 이미지 저장
            for page_no, page in res.document.pages.items():
                with (out_dir / f"{stem}-{page.page_no}.png").open("wb") as fp:
                    page.image.pil_image.save(fp, format="PNG")

            # 2) 표/그림 이미지 저장
            t, p = 0, 0
            for elem, _ in res.document.iterate_items():
                if isinstance(elem, TableItem):
                    t += 1
                    with (out_dir / f"{stem}-table-{t}.png").open("wb") as fp:
                        elem.get_image(res.document).save(fp, "PNG")
                if isinstance(elem, PictureItem):
                    p += 1
                    with (out_dir / f"{stem}-picture-{p}.png").open("wb") as fp:
                        elem.get_image(res.document).save(fp, "PNG")
            

            # 3) md 파일 export
            res.document.save_as_markdown(out_dir / temp_md_file_name, image_mode=ImageRefMode.REFERENCED)

            # 4)JSON 변환
            json_data = self._md_file_to_json(out_dir / temp_md_file_name)

            return json_data


    def _md_file_to_json(self, md_file_name: str) -> Dict[str, Any]:
        """
        MD 파일을 JSON으로 변환합니다.
        
        Args:
            md_file_name: MD 파일 이름
            
        Returns:
            Dict[str, Any]: JSON 데이터
        """
        with open(md_file_name, "r", encoding="utf-8") as f:
            md_content = f.read()
            return markdown_to_json.dictify(md_content)

    def _summary_abstract(self, abstract: str, title: str) -> Optional[str]:
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

    def _create_analyzed_content(self, content: List[ContentChunk]) -> Optional[str]:
        """
        논문 본문을 요약합니다.
        
        Args:
            content: 논문 본문 (ContentChunk 리스트)
        Returns:
            str: 요약된 본문 또는 None
        """
        try:
            tmp = []
            for chunk in content:
                if chunk["type"] == "img":
                    image_url = self._convert_local_image_to_fs(chunk["content"])
                    tmp.append(f"\n{image_url}\n")
                else:
                    user_prompt = create_analyze_paper_content_prompt(chunk["content"]) 
                    response = self.llm.invoke(user_prompt)
                    tmp.append(response.content)
            return "\n".join(tmp)
        except Exception as e:
            logger.error(f"논문 본문 요약 중 오류 발생: {e}")
            return None

    def _convert_local_image_to_fs(self, image_url: str) -> str:
        """
        로컬 이미지를 s3 호환 파일 시스템에 저장합니다.
        
        Args:
            image_url: 파일 시스템 이미지 URL(마크다운 형태)
        
        Returns:
            str: 웹 Public URL(마크다운 형태)
        """
        try:
            local_image_url = extract_image_url_from_markdown(image_url)

            if not local_image_url:
                raise ValueError("로컬 이미지 URL을 추출할 수 없습니다.")
            public_url = upload_file_to_oci(local_image_url)
            return replace_image_url_in_markdown(image_url, public_url)

        except Exception as e:
            logger.error(f"로컬 이미지를 웹 Public URL로 변환 중 오류 발생: {e}")
            return image_url