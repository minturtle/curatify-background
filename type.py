from typing import TypedDict, List, Optional, Literal
from datetime import datetime

class ContentChunk(TypedDict):
    type: Literal["text", "img"]
    content: str

class ContentAnalysisResult(TypedDict):
    order: int
    contentTitle: str
    content: str


class PaperMessage(TypedDict):
    user_id: str
    paper_id: str

class ArXivMetadata(TypedDict):
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    updated: Optional[str]
    categories: List[str]

class PaperData(TypedDict):
    title: str
    summary: str
    contentBlocks: List[ContentAnalysisResult]
    url: str
    authors: List[str]
    categories: List[str]
    abstract: str
    lastPublishDate: Optional[str]

class UserLibrary(TypedDict):
    user_id: str
    paper_id: str
    created_at: datetime