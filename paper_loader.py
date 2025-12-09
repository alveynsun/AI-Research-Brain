# src/paper_loader.py
"""
论文加载与元数据提取
"""
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import config


@dataclass
class PaperMetadata:
    """论文元数据"""
    title: str
    authors: List[str]
    abstract: str
    year: Optional[int] = None
    venue: Optional[str] = None  # 发表会议/期刊
    keywords: List[str] = None
    file_path: str = ""
    added_date: str = ""

    def __post_init__(self):
        if not self.added_date:
            self.added_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        if self.keywords is None:
            self.keywords = []


class PaperLoader:
    """论文加载器"""

    def __init__(self):
        self.llm = ChatOllama(model=config.LLM_MODEL, temperature=0)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # 元数据提取 Prompt
        self.metadata_prompt = ChatPromptTemplate.from_template(
            """从以下论文内容中提取元数据信息。

【论文内容（前3页）】
{content}

请提取以下信息，以 JSON 格式输出：
{{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要内容（如果能找到）",
    "year": 发表年份（数字，如 2023）,
    "venue": "发表会议或期刊名称",
    "keywords": ["关键词1", "关键词2", "关键词3"]
}}

注意：
- 如果某个字段找不到，设为 null
- keywords 请根据论文内容自动提取 3-5 个关键词
- 只输出 JSON，不要其他内容

JSON 输出："""
        )

    def load_pdf(self, file_path: str) -> tuple[List, PaperMetadata]:
        """
        加载 PDF 论文
        返回：(文档块列表, 元数据)
        """
        print(f"📄 加载论文: {file_path}")

        # 1. 加载 PDF
        loader = PyPDFLoader(file_path)
        pages = loader.load()

        if not pages:
            raise ValueError(f"无法加载 PDF: {file_path}")

        print(f"   共 {len(pages)} 页")

        # 2.  提取元数据（用前3页的内容）
        first_pages_content = "\n".join([
            pages[i].page_content for i in range(min(3, len(pages)))
        ])
        metadata = self._extract_metadata(first_pages_content, file_path)

        # 3. 切分文档
        chunks = self.splitter.split_documents(pages)
        print(f"   切分为 {len(chunks)} 个文本块")

        # 4. 为每个 chunk 添加元数据
        for chunk in chunks:
            chunk.metadata.update({
                "title": metadata.title,
                "authors": ", ".join(metadata.authors),
                "year": metadata.year,
                "venue": metadata.venue,
                "keywords": ", ".join(metadata.keywords),
                "file_path": file_path
            })

        return chunks, metadata

    def _extract_metadata(self, content: str, file_path: str) -> PaperMetadata:
        """使用 LLM 提取论文元数据"""
        try:
            chain = self.metadata_prompt | self.llm | JsonOutputParser()
            result = chain.invoke({"content": content[:8000]})  # 限制长度

            return PaperMetadata(
                title=result.get("title", "Unknown Title"),
                authors=result.get("authors", ["Unknown"]),
                abstract=result.get("abstract", ""),
                year=result.get("year"),
                venue=result.get("venue"),
                keywords=result.get("keywords", []),
                file_path=file_path
            )
        except Exception as e:
            print(f"   ⚠️元数据提取失败: {e}")
            # 从文件名猜测标题
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0].replace("_", " ")
            return PaperMetadata(
                title=title,
                authors=["Unknown"],
                abstract="",
                file_path=file_path
            )

    def load_text_note(self, content: str, title: str) -> List:
        """加载文本笔记"""
        from langchain_core.documents import Document

        doc = Document(
            page_content=content,
            metadata={
                "title": title,
                "type": "note",
                "added_date": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        )
        return self.splitter.split_documents([doc])