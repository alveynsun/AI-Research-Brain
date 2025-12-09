# src/config.py
from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class Config:
    # 模型配置
    LLM_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "qwen2.5:7b"
    TEMPERATURE: float = 0.3

    # 路径配置
    PAPERS_DIR: str = "data/papers"
    CHROMA_DIR: str = "db/chroma"
    COLLECTION_NAME: str = "research_papers"

    # RAG 配置
    CHUNK_SIZE: int = 1000  # 论文内容较长，用大一点的 chunk
    CHUNK_OVERLAP: int = 200
    RETRIEVER_K: int = 5

    # 支持的文件类型
    SUPPORTED_EXTENSIONS: List[str] = field(
        default_factory=lambda: ['. pdf', '.txt', '.md']
    )

    def __post_init__(self):
        os.makedirs(self.PAPERS_DIR, exist_ok=True)
        os.makedirs(self.CHROMA_DIR, exist_ok=True)


config = Config()