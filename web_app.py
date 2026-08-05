"""CollabCheck - Streamlit 主入口。

页面布局、会话状态与历史记录在此维护；
检索逻辑见 search_service / sources / name_utils / search_lock，
弹窗渲染见 ui，配置见 config。
"""
import streamlit as st

from search_service import run_search, search_lock
from ui import show_detail_dialog

st.set_page_config(page_title="CollabCheck", layout="wide")

# ===== 简洁风格样式 =====
st.markdown(
    """
    <style>
    .stApp { background-color: #FAFBFC; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px; }
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #EEF0F3; }
    [data-testid="stSidebar"] .block-container { padding-top: 1.6rem; }
    .cb-hero h1 { font-size: 2.2rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 0.15rem 0; color: #111827; }
    .cb-hero p { margin: 0 0 0.8rem 0; color: #6B7280; font-size: 0.95rem; }
    .cb-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1rem 1.25rem; margin: 0.6rem 0; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04); color: #374151; line-height: 1.7; }
    .cb-card code { background: #F3F4F6; padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.85em; }
    .stButton > button { border-radius: 8px; font-weight: 600; }
    .stButton > button[kind="primary"] { background: #111827; border: 1px solid #111827; }
    .stTextArea textarea { border-radius: 8px; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== 会话状态初始化 =====
if 'last_search_time' not in st.session_state:
    st.session_state.last_search_time = 0
if 'is_searching' not in st.session_state:
    st.session_state.is_searching = False
if 'history_queue' not in st.session_state:
    st.session_state.history_queue = []
if 'fixed_input' not in st.session_state:
    st.session_state.fixed_input = ""
if 'candidate_input' not in st.session_state:
    st.session_state.candidate_input = ""


# ===== 侧边栏：说明信息 =====
with st.sidebar:
    st.markdown("### CollabCheck")
    st.caption("作者间潜在利益冲突快速筛查")
    st.divider()

    with st.expander("使用方法", expanded=False):
        st.markdown(
            """
- 每行一位作者，格式：`名; 姓`（例如 `Nancy; Lane`）。
- **Potential COI**：潜在利益相关方。
- **Author(s)**：待查作者。
- 点击 **Start Search** 开始交叉筛查。
"""
        )

    with st.expander("免责声明", expanded=False):
        st.markdown(
            """
- 本工具自动检索多个学术数据库，结果可能**不精准、有遗漏或误判**，仅供初步筛查参考。
- 最终结论请以人工核查、论文原文及官方记录为准。
"""
        )

    with st.expander("关于 CollabCheck", expanded=False):
        st.markdown(
            """
**开源项目**，基于 [MIT License](LICENSE) 协议发布，可自由使用与修改。
"""
        )

# ===== 主区域：输入与结果 =====
with st.container():
    st.markdown(
        '<div class="cb-hero">'
        "<h1>CollabCheck</h1>"
        "<p>快速筛查两位作者间是否存在共同发文，识别潜在利益冲突（COI）。</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 输入区（主要位置）
    col1, col2 = st.columns(2)
    with col1:
        fixed_input = st.text_area(
            "Potential COI 潜在相关方",
            value=st.session_state.fixed_input,
            height=160,
            key="fixed_input_widget"
        )
        st.session_state.fixed_input = fixed_input

    with col2:
        candidate_input = st.text_area(
            "Author(s) 待查作者",
            value=st.session_state.candidate_input,
            height=160,
            key="candidate_input_widget"
        )
        st.session_state.candidate_input = candidate_input
    
    # Auto-refreshing status display using fragment
    @st.fragment(run_every=2)
    def status_display():
        """Auto-refreshing status indicator that updates every 2 seconds."""
        current_status, current_message = search_lock.get_status()

        if current_status == "busy":
            st.warning("系统正在处理其他请求，请稍候... (自动刷新中)")
        elif current_status == "cooldown":
            st.warning(current_message)
        else:
            st.success("系统就绪，可以开始搜索")

    status_display()
    
    current_status, _ = search_lock.get_status()
    can_search = (current_status == "ready")

    if st.button("Start Search", type="primary", disabled=not can_search, use_container_width=True):
        run_search(fixed_input, candidate_input)

st.divider()

if st.session_state.history_queue:
    st.subheader("Search History (Session)")
    
    for i, item in enumerate(reversed(st.session_state.history_queue)):
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{item['timestamp']}**")
                # Showing a brief preview could be nice, e.g. the first fixed author vs first candidate
                preview = "Results View"
                try:
                     f_auth = item['data']['inputs']['fixed'].split('\n')[0][:20]
                     c_auth = item['data']['inputs']['candidate'].split('\n')[0][:20]
                     preview = f"{f_auth}... vs {c_auth}..."
                except:
                    pass
                st.caption(preview)
                
            with col2:
                # Unique key is important here. 
                # Since we are iterating reversed list, 'i' will be 0 for the newest item.
                if st.button("View", key=f"hist_view_{len(st.session_state.history_queue) - 1 - i}"):
                    show_detail_dialog(item['title'], item['timestamp'], item['data'])
            
            st.divider()
