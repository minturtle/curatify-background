from typing import TypedDict, List, Optional, Any

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
    contentBlocks: List[Any]
    url: str
    authors: List[str]
    categories: List[str]
    abstract: str
    lastPublishDate: Optional[str]