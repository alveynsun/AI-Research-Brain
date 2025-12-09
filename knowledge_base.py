# src/knowledge_base.py
"""
向量知识库管理
"""
import os
import json
from typing import List, Dict, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from dataclasses import asdict

from .config import config
from .paper_loader import PaperLoader, PaperMetadata


class ResearchKnowledgeBase:
    """科研知识库"""

    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=config.EMBEDDING_MODEL)
        self.paper_loader = PaperLoader()
        self.papers_index: Dict[str, PaperMetadata] = {}  # 论文索引
        self.index_file = os.path.join(config.CHROMA_DIR, "papers_index.json")

        self._init_vectorstore()
        self._load_papers_index()

    def _init_vectorstore(self):
        """初始化向量数据库"""
        self.vectorstore = Chroma(
            persist_directory=config.CHROMA_DIR,
            embedding_function=self.embeddings,
            collection_name=config.COLLECTION_NAME
        )

    def _load_papers_index(self):
        """加载论文索引"""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in data.items():
                    self.papers_index[k] = PaperMetadata(**v)
            print(f"📚 已加载 {len(self.papers_index)} 篇论文索引")

    def _save_papers_index(self):
        """保存论文索引"""
        data = {k: asdict(v) for k, v in self.papers_index.items()}
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_paper(self, file_path: str) -> PaperMetadata:
        """添加论文到知识库"""
        # 检查是否已存在
        if file_path in self.papers_index:
            print(f"⚠️ 论文已存在: {file_path}")
            return self.papers_index[file_path]

        # 加载并解析
        chunks, metadata = self.paper_loader.load_pdf(file_path)

        # 添加到向量库
        self.vectorstore.add_documents(chunks)

        # 更新索引
        self.papers_index[file_path] = metadata
        self._save_papers_index()

        print(f"✅ 论文已添加: {metadata.title}")
        return metadata

    def add_note(self, content: str, title: str, related_paper: str = None):
        """添加笔记"""
        chunks = self.paper_loader.load_text_note(content, title)

        if related_paper:
            for chunk in chunks:
                chunk.metadata["related_paper"] = related_paper

        self.vectorstore.add_documents(chunks)
        print(f"✅ 笔记已添加: {title}")

    def search(self, query: str, k: int = None, filter_dict: Dict = None) -> List[Document]:
        """
        检索相关内容

        Args:
            query: 查询文本
            k: 返回数量
            filter_dict: 过滤条件，如 {"year": 2023}
        """
        k = k or config.RETRIEVER_K

        if filter_dict:
            results = self.vectorstore.similarity_search(
                query, k=k, filter=filter_dict
            )
        else:
            results = self.vectorstore.similarity_search(query, k=k)

        return results

    def search_with_scores(self, query: str, k: int = None) -> List[tuple]:
        """检索并返回相似度分数"""
        k = k or config.RETRIEVER_K
        return self.vectorstore.similarity_search_with_score(query, k=k)

    def get_retriever(self, k: int = None):
        """获取检索器"""
        k = k or config.RETRIEVER_K
        return self.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )

    def list_papers(self) -> List[PaperMetadata]:
        """列出所有论文"""
        return list(self.papers_index.values())

    def get_paper_by_title(self, title: str) -> Optional[PaperMetadata]:
        """根据标题查找论文"""
        for paper in self.papers_index.values():
            if title.lower() in paper.title.lower():
                return paper
        return None

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        papers = self.list_papers()

        # 按年份统计
        year_counts = {}
        for p in papers:
            if p.year:
                year_counts[p.year] = year_counts.get(p.year, 0) + 1

        # 关键词统计
        keyword_counts = {}
        for p in papers:
            for kw in p.keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        top_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_papers": len(papers),
            "papers_by_year": year_counts,
            "top_keywords": top_keywords,
            "total_chunks": self.vectorstore._collection.count()
        }


# 导出单例
from .paper_loader import asdict  # 需要导入 asdict

knowledge_base = ResearchKnowledgeBase()