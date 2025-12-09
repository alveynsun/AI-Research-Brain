# app.py
"""
AI 科研文献助手 - Streamlit 界面
"""
import streamlit as st
import os
from src.knowledge_base import knowledge_base as kb
from src.chains import assistant

# ===== 页面配置 =====
st.set_page_config(
    page_title="📚 AI 科研助手",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== 侧边栏 =====
with st.sidebar:
    st.title("📚 AI 科研助手")
    st.caption("你的文献第二大脑")

    st.divider()

    # 知识库统计
    stats = kb.get_stats()
    st.metric("📄 论文总数", stats["total_papers"])
    st.metric("📦 知识块数", stats["total_chunks"])

    if stats["top_keywords"]:
        st.subheader("🏷️ 热门关键词")
        for kw, count in stats["top_keywords"][:5]:
            st.write(f"- {kw} ({count})")

    st.divider()

    # 上传论文
    st.subheader("📤 上传论文")
    uploaded_file = st.file_uploader(
        "选择 PDF 文件",
        type=["pdf"],
        help="支持上传学术论文 PDF"
    )

    if uploaded_file:
        # 保存文件
        save_path = os.path.join("data/papers", uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 添加到知识库
        with st.spinner("正在解析论文..."):
            try:
                metadata = kb.add_paper(save_path)
                st.success(f"✅ 已添加: {metadata.title}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 添加失败: {e}")

# ===== 主界面 =====
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 智能问答",
    "📝 论文总结",
    "🔍 对比分析",
    "✍️ 写作助手",
    "📚 论文列表"
])

# ----- Tab 1: 智能问答 -----
with tab1:
    st.header("💬 问问你的文献库")
    st.caption("问任何关于你读过的论文的问题")

    # 示例问题
    example_questions = [
        "我读过哪些关于 Transformer 的论文？",
        "XXX 方法的优缺点是什么？",
        "有哪些论文使用了 YYY 数据集？",
        "对比一下 A 方法和 B 方法",
    ]

    st.write("💡 **示例问题：**")
    cols = st.columns(2)
    for i, q in enumerate(example_questions):
        if cols[i % 2].button(q, key=f"example_{i}"):
            st.session_state.qa_input = q

    # 输入框
    question = st.text_input(
        "输入你的问题：",
        value=st.session_state.get("qa_input", ""),
        placeholder="例如：XXX 方法是如何工作的？"
    )

    if st.button("🔍 搜索", type="primary") and question:
        with st.spinner("正在检索和思考..."):
            answer = assistant.ask(question)

        st.markdown("### 📖 回答")
        st.markdown(answer)

        # 显示相关文档
        with st.expander("📄 查看相关原文"):
            docs = kb.search(question, k=3)
            for doc in docs:
                st.info(f"**来源:** {doc.metadata.get('title', 'Unknown')}")
                st.write(doc.page_content[:500] + "...")
                st.divider()

# ----- Tab 2: 论文总结 -----
with tab2:
    st.header("📝 论文总结")
    st.caption("快速回顾一篇论文的核心内容")

    papers = kb.list_papers()

    if papers:
        paper_titles = [p.title for p in papers]
        selected_paper = st.selectbox("选择论文：", paper_titles)

        if st.button("📋 生成总结", type="primary"):
            with st.spinner("正在总结..."):
                summary = assistant.summarize_paper(selected_paper)
            st.markdown(summary)
    else:
        st.info("📭 知识库为空，请先上传论文")

# ----- Tab 3: 对比分析 -----
with tab3:
    st.header("🔍 方法对比")
    st.caption("对比分析不同方法或论文")

    compare_topic = st.text_input(
        "输入要对比的主题：",
        placeholder="例如：BERT vs GPT, 或者：注意力机制的不同实现"
    )

    if st.button("⚖️ 开始对比", type="primary") and compare_topic:
        with st.spinner("正在分析... "):
            comparison = assistant.compare(compare_topic)
        st.markdown(comparison)

# ----- Tab 4: 写作助手 -----
with tab4:
    st.header("✍️ 写作助手")

    writing_mode = st.radio(
        "选择功能：",
        ["📚 生成 Related Work", "💡 研究想法头脑风暴"]
    )

    if writing_mode == "📚 生成 Related Work":
        topic = st.text_area(
            "输入研究主题：",
            placeholder="描述你的研究主题，系统会基于知识库生成 Related Work 段落"
        )

        if st.button("📝 生成", type="primary") and topic:
            with st.spinner("正在生成..."):
                related_work = assistant.generate_related_work(topic)
            st.markdown("### 生成的 Related Work")
            st.markdown(related_work)

            # 复制按钮
            st.code(related_work, language="markdown")

    else:  # 头脑风暴
        idea = st.text_area(
            "输入你的研究想法：",
            placeholder="描述你的研究想法，AI 会帮你拓展思路"
        )

        if st.button("🧠 头脑风暴", type="primary") and idea:
            with st.spinner("正在思考..."):
                brainstorm = assistant.brainstorm(idea)
            st.markdown(brainstorm)

# ----- Tab 5: 论文列表 -----
with tab5:
    st.header("📚 我的论文库")

    papers = kb.list_papers()

    if papers:
        # 搜索过滤
        search_term = st.text_input("🔍 搜索论文：", placeholder="输入标题或关键词")

        filtered_papers = papers
        if search_term:
            filtered_papers = [
                p for p in papers
                if search_term.lower() in p.title.lower()
                   or search_term.lower() in " ".join(p.keywords).lower()
            ]

        st.write(f"共 {len(filtered_papers)} 篇论文")

        for paper in filtered_papers:
            with st.expander(f"📄 {paper.title}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**作者:** {', '.join(paper.authors)}")
                    st.write(f"**年份:** {paper.year or '未知'}")
                    st.write(f"**会议/期刊:** {paper.venue or '未知'}")
                with col2:
                    st.write(f"**关键词:** {', '.join(paper.keywords)}")
                    st.write(f"**添加时间:** {paper.added_date}")

                if paper.abstract:
                    st.write("**摘要:**")
                    st.write(paper.abstract)
    else:
        st.info("📭 还没有添加任何论文，请通过侧边栏上传")

# ===== 页脚 =====
st.divider()
st.caption("🧠 AI 科研助手 | 基于 LangChain + Ollama 构建")