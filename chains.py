# src/chains.py
"""
各种功能 Chain
"""
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .config import config
from .knowledge_base import knowledge_base

# 初始化 LLM
llm = ChatOllama(model=config.LLM_MODEL, temperature=config.TEMPERATURE)


def format_docs(docs):
    """格式化检索结果"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        source = f"[{meta.get('title', 'Unknown')}]"
        if meta.get('page'):
            source += f" (Page {meta['page']})"
        formatted.append(f"【来源 {i}】{source}\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


class ResearchAssistant:
    """科研助手"""

    def __init__(self):
        self.kb = knowledge_base
        self.retriever = self.kb.get_retriever()
        self._build_chains()

    def _build_chains(self):
        """构建各种功能 Chain"""

        # 1. 通用问答 Chain
        self.qa_prompt = ChatPromptTemplate.from_template(
            """你是一个专业的科研助手，帮助研究人员查询和理解学术文献。

【检索到的相关文献内容】
{context}

【用户问题】
{question}

【回答要求】
1. 基于检索到的文献内容回答
2. 必须标注信息来源（论文标题）
3. 如果信息不足，诚实说明
4. 使用学术化但易懂的语言

请回答："""
        )

        self.qa_chain = (
                {
                    "context": self.retriever | format_docs,
                    "question": RunnablePassthrough()
                }
                | self.qa_prompt
                | llm
                | StrOutputParser()
        )

        # 2.  论文总结 Chain
        self.summary_prompt = ChatPromptTemplate.from_template(
            """请对以下论文内容进行结构化总结：

【论文内容】
{content}

请按以下格式输出：

## 📌 一句话总结
（用一句话概括这篇论文的核心贡献）

## 🎯 研究问题
（这篇论文要解决什么问题？）

## 💡 核心方法
（用了什么方法？创新点是什么？）

## 📊 主要结果
（实验结果如何？有哪些关键数据？）

## 🔗 与其他工作的关系
（引用了哪些重要工作？和哪些方法对比？）

## 💭 我的思考
（这篇论文的优缺点、可能的改进方向）
"""
        )

        self.summary_chain = self.summary_prompt | llm | StrOutputParser()

        # 3. 对比分析 Chain
        self.compare_prompt = ChatPromptTemplate.from_template(
            """请对比分析以下两个/多个方法或论文：

【相关文献内容】
{content}

【对比主题】
{topic}

请按以下格式输出对比分析：

## 📋 对比概览

| 维度 | 方法A | 方法B |
|------|-------|-------|
| 核心思想 | | |
| 技术路线 | | |
| 优点 | | |
| 缺点 | | |
| 适用场景 | | |

## 🔍 详细分析

### 相同点
1. 
2. 

### 不同点
1.  
2. 

### 各自优势
- 方法A 适合... 
- 方法B 适合...

## 💡 选择建议
（什么情况下用哪个方法）
"""
        )

        # 4. Related Work 生成 Chain
        self.related_work_prompt = ChatPromptTemplate.from_template(
            """基于以下文献内容，为研究主题生成 Related Work 段落：

【研究主题】
{topic}

【相关文献】
{content}

【要求】
1. 按照学术论文 Related Work 的标准格式撰写
2. 逻辑清晰，分类讨论
3. 正确引用文献（使用 [作者, 年份] 格式）
4. 指出现有工作的局限性，引出研究动机

请生成 Related Work：
"""
        )

        self.related_work_chain = (
                self.related_work_prompt | llm | StrOutputParser()
        )

    # ===== 核心功能方法 =====

    def ask(self, question: str) -> str:
        """
        通用问答：问任何关于你读过的论文的问题
        """
        return self.qa_chain.invoke(question)

    def summarize_paper(self, paper_title: str) -> str:
        """
        总结指定论文
        """
        # 检索该论文的内容
        docs = self.kb.search(
            paper_title,
            k=10,
            filter_dict={"title": paper_title}
        )

        if not docs:
            # 尝试模糊搜索
            docs = self.kb.search(paper_title, k=10)

        if not docs:
            return f"❌ 未找到论文: {paper_title}"

        content = "\n\n".join([doc.page_content for doc in docs])
        return self.summary_chain.invoke({"content": content})

    def compare(self, topic: str) -> str:
        """
        对比分析多个方法/论文
        """
        docs = self.kb.search(topic, k=8)

        if not docs:
            return f"❌ 未找到与 '{topic}' 相关的内容"

        content = format_docs(docs)
        chain = self.compare_prompt | llm | StrOutputParser()
        return chain.invoke({"content": content, "topic": topic})

    def generate_related_work(self, topic: str) -> str:
        """
        生成 Related Work 段落
        """
        docs = self.kb.search(topic, k=10)

        if not docs:
            return f"❌ 未找到与 '{topic}' 相关的文献"

        content = format_docs(docs)
        return self.related_work_chain.invoke({
            "topic": topic,
            "content": content
        })

    def find_papers_about(self, topic: str) -> str:
        """
        查找关于某主题的所有论文
        """
        docs = self.kb.search_with_scores(topic, k=10)

        if not docs:
            return f"❌ 未找到与 '{topic}' 相关的论文"

        # 按论文去重
        seen_titles = set()
        results = []

        for doc, score in docs:
            title = doc.metadata.get('title', 'Unknown')
            if title not in seen_titles:
                seen_titles.add(title)
                results.append({
                    "title": title,
                    "authors": doc.metadata.get('authors', ''),
                    "year": doc.metadata.get('year', ''),
                    "relevance": f"{(1 - score) * 100:.1f}%",  # 转换为相关度百分比
                    "snippet": doc.page_content[:200] + "..."
                })

        # 格式化输出
        output = f"📚 找到 {len(results)} 篇相关论文：\n\n"
        for i, r in enumerate(results, 1):
            output += f"**{i}. {r['title']}**\n"
            output += f"   👤 作者: {r['authors']}\n"
            output += f"   📅 年份: {r['year']}\n"
            output += f"   🎯 相关度: {r['relevance']}\n"
            output += f"   📝 摘要: {r['snippet']}\n\n"

        return output

    def brainstorm(self, research_idea: str) -> str:
        """
        基于知识库进行研究想法头脑风暴
        """
        docs = self.kb.search(research_idea, k=8)
        context = format_docs(docs) if docs else "（知识库中暂无直接相关内容）"

        prompt = ChatPromptTemplate.from_template(
            """你是一位经验丰富的科研导师。学生提出了一个研究想法，请帮助他拓展思路。

【学生的研究想法】
{idea}

【相关文献参考】
{context}

请提供以下帮助：

## 💡 想法评估
（这个想法的可行性、创新性如何？）

## 🔗 相关工作
（有哪些已有工作与此相关？可以借鉴什么？）

## 🚀 可能的研究方向
1. 方向A: ... 
2. 方向B: ...
3. 方向C: ...

## ⚠️ 潜在挑战
（可能遇到的困难和解决思路）

## 📋 建议的下一步
（接下来应该做什么？读哪些论文？做什么实验？）
"""
        )

        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"idea": research_idea, "context": context})


# 导出单例
assistant = ResearchAssistant()