import streamlit as st
import tempfile
import uuid
from auto_defense_system.agent.graph import graph_invoke, clear_history, get_thread_messages
from auto_defense_system.rag.retriever import init_rag_retriever
from auto_defense_system.security.permission import ROLE_PERMISSIONS, get_role_info
from auto_defense_system.security.audit import read_audit_log

# 页面配置
st.set_page_config(
    page_title="AI安全智能助手-终版",
    page_icon="🔒",
    layout="wide"
)

# 页面标题
st.title("🔒 AI安全智能助手 | 企业级终版")
st.caption("Agent+RAG全链路安全防护 | 网安工具集 | 权限控制 | 审计合规 | 秋招面试专用")

# ---------------------- 初始化会话状态 ----------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = f"web_user_{st.session_state.session_id}"

# Restore messages from checkpointer on first load (survives page refresh)
if "messages" not in st.session_state:
    restored = get_thread_messages(st.session_state.user_id)
    st.session_state.messages = restored

if "current_role" not in st.session_state:
    st.session_state.current_role = "user"
if "retriever" not in st.session_state:
    st.session_state.retriever = None

# ---------------------- 侧边栏控制面板 ----------------------
with st.sidebar:
    st.header("🔧 控制面板")

    # 角色权限模块
    st.subheader("👤 角色权限控制")
    selected_role = st.selectbox(
        "选择当前角色",
        options=list(ROLE_PERMISSIONS.keys()),
        format_func=lambda x: ROLE_PERMISSIONS[x]["name"],
        index=list(ROLE_PERMISSIONS.keys()).index(st.session_state.current_role)
    )

    # 角色切换逻辑
    if selected_role != st.session_state.current_role:
        st.session_state.current_role = selected_role
        clear_history(st.session_state.user_id)
        st.session_state.messages = []
        st.success(f"已切换为【{ROLE_PERMISSIONS[selected_role]['name']}】")

    # 权限说明
    role_info = get_role_info(st.session_state.current_role)
    st.info(f"当前权限：{role_info['desc']}")

    st.divider()

    # PDF上传模块
    st.subheader("📄 知识库PDF上传")
    uploaded_file = st.file_uploader("选择PDF文档", type="pdf")
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(uploaded_file.getvalue())
            temp_path = f.name

        st.session_state.retriever = init_rag_retriever(temp_path, persist=False, session_id=st.session_state.session_id)
        st.success(f"✅ 已成功加载文档：{uploaded_file.name}，当前会话已切换为该文档知识库")

    st.divider()

    # 操作按钮区
    col1, col2 = st.columns(2)
    with col1:
        if st.button("清空对话", type="primary", use_container_width=True):
            clear_history(st.session_state.user_id)
            st.session_state.messages = []
            st.success("✅ 对话已清空（持久化状态已重置）")
    with col2:
        if st.button("刷新日志", use_container_width=True):
            st.rerun()

    st.divider()

    # 审计日志面板
    st.subheader("📊 操作审计日志")
    log_line_count = st.slider("显示日志条数", min_value=5, max_value=50, value=10)
    log_content = read_audit_log(log_line_count)
    st.code(log_content, language="text")

    st.divider()
    st.subheader("✅ 功能清单")
    st.markdown("""
    - 📄 会话级知识库RAG问答
    - 🔍 敏感信息检测/脱敏
    - 🧪 简易Web漏洞扫描
    - 💉 SQL注入攻击检测
    - 🛡️ Prompt注入拦截
    - 🔐 角色权限控制
    - 📊 操作审计日志
    - 🔏 输出合规校验
    - 💬 多轮对话记忆（SQLite持久化）
    """)

# ---------------------- 主对话界面 ----------------------
# 渲染历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入框
user_input = st.chat_input("请输入安全相关问题，支持：知识库问答、敏感信息检测、SQL注入检测、漏洞扫描...")

# 处理用户输入
if user_input:
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call LangGraph agent (pure checkpointer mode — no chat_history)
    with st.chat_message("assistant"):
        with st.spinner("Agent安全处理中..."):
            answer = graph_invoke(
                user_input=user_input,
                role=st.session_state.current_role,
                retriever=st.session_state.retriever,
                user_id=st.session_state.user_id,
            )
        st.markdown(answer)

    # Add assistant message to UI
    st.session_state.messages.append({"role": "assistant", "content": answer})
