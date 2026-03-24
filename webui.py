"""
Multi-Agent Coding Assistant - Web UI
基于 Streamlit 的 Web 界面
"""
import streamlit as st
from api.llm import create_client, LLMClient
from agents import create_agent, get_available_agents
from core.orchestrator import MultiAgentOrchestrator, TaskPriority
import time


# 页面配置
st.set_page_config(
    page_title="Multi-Agent Coding Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.orchestrator = None
        st.session_state.llm = None
        st.session_state.results = []
        st.session_state.task_history = []


def sidebar_config():
    """侧边栏配置"""
    st.sidebar.title("⚙️ 配置")
    
    # LLM 提供商选择
    provider = st.sidebar.selectbox(
        "LLM 提供商",
        ["qwen", "deepseek", "moonshot", "doubao", "claude", "gemini"],
        index=0
    )
    
    # API Key 输入
    api_key = st.sidebar.text_input(
        "API Key",
        type="password",
        placeholder=f"输入 {provider.upper()} API Key",
        key=f"api_key_{provider}"
    )
    
    # 模型名称
    model = st.sidebar.text_input(
        "模型名称",
        placeholder="留空使用默认模型",
        key=f"model_{provider}"
    )
    
    st.sidebar.divider()
    
    # Agent 选择
    st.sidebar.subheader("🤖 启用 Agent")
    available_agents = get_available_agents()
    selected_agents = st.sidebar.multiselect(
        "选择要启用的 Agent",
        options=available_agents,
        default=["codewriter", "codereviewer"],
        key="selected_agents"
    )
    
    st.sidebar.divider()
    
    # 高级设置
    st.sidebar.subheader("🔧 高级设置")
    max_concurrent = st.sidebar.slider("最大并发任务数", 1, 10, 3)
    auto_decompose = st.sidebar.checkbox("自动任务分解", value=True)
    
    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "selected_agents": selected_agents,
        "max_concurrent": max_concurrent,
        "auto_decompose": auto_decompose
    }


def show_agent_status(orchestrator):
    """显示 Agent 状态"""
    st.subheader("🤖 Agent 状态")
    
    if orchestrator:
        agent_status = orchestrator.scheduler.get_agent_status()
        cols = st.columns(min(3, len(agent_status)))
        
        for i, (name, status) in enumerate(agent_status.items()):
            with cols[i % 3]:
                status_color = "🟢" if status.get("status") == "idle" else "🔵"
                st.metric(
                    label=f"{status_color} {name}",
                    value=status.get("specialty", "-"),
                    delta=f"完成：{status.get('completed_tasks', 0)}"
                )


def main():
    st.markdown('<p class="main-header">🤖 Multi-Agent Coding Assistant</p>', 
                unsafe_allow_html=True)
    st.markdown("多 Agent 协作编码助手 - 让 AI 团队为你工作")
    
    # 初始化
    init_session_state()
    
    # 侧边栏配置
    config = sidebar_config()
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 任务输入
        st.subheader("📝 任务描述")
        task_input = st.text_area(
            "输入你的编程任务",
            placeholder="例如：用 Python 实现一个快速排序，包含测试用例和性能优化建议",
            height=150,
            key="task_input"
        )
        
        # 优先级选择
        priority = st.selectbox(
            "任务优先级",
            options=["NORMAL", "HIGH", "URGENT", "LOW"],
            index=1
        )
        
        # 执行按钮
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        with col_btn1:
            run_btn = st.button("🚀 执行任务", type="primary", use_container_width=True)
        with col_btn2:
            clear_btn = st.button("🗑️ 清空", use_container_width=True)
        with col_btn3:
            export_btn = st.button("📥 导出", use_container_width=True)
    
    with col2:
        # 快速任务模板
        st.subheader("⚡ 快速模板")
        templates = {
            "代码生成": "实现一个功能完整的 XXX 类，包含错误处理和文档",
            "代码审查": "审查以下代码的安全性、性能和可维护性：[粘贴代码]",
            "测试生成": "为以下代码生成全面的单元测试：[粘贴代码]",
            "性能优化": "分析以下代码的性能瓶颈并提供优化方案：[粘贴代码]",
            "安全审计": "审计以下代码的安全漏洞：[粘贴代码]",
        }
        
        for name, template in templates.items():
            if st.button(f"{name}", key=f"template_{name}", use_container_width=True):
                st.session_state.task_input = template
        
        st.divider()
        
        # 系统信息
        st.subheader("📊 系统状态")
        if st.session_state.llm:
            st.success(f"LLM: {config['provider']} 已连接")
        else:
            st.info("未连接 LLM")
        
        st.info(f"可用 Agent: {len(get_available_agents())}")
    
    # 执行任务
    if run_btn and task_input:
        if not config['api_key']:
            st.error(f"请输入 {config['provider'].upper()} API Key")
            st.stop()
        
        if not config['selected_agents']:
            st.error("请至少选择一个 Agent")
            st.stop()
        
        with st.spinner("🔄 正在初始化..."):
            try:
                # 创建 LLM 客户端
                st.session_state.llm = create_client(
                    provider=config['provider'],
                    api_key=config['api_key'],
                    model=config['model'] or None
                )
                
                # 创建编排器
                st.session_state.orchestrator = MultiAgentOrchestrator()
                st.session_state.orchestrator.set_llm(st.session_state.llm)
                
                # 注册选中的 Agent
                for agent_type in config['selected_agents']:
                    agent = create_agent(agent_type, llm_client=st.session_state.llm)
                    st.session_state.orchestrator.add_agent(agent_type, agent)
                
            except Exception as e:
                st.error(f"初始化失败：{str(e)}")
                st.stop()
        
        # 显示 Agent 状态
        show_agent_status(st.session_state.orchestrator)
        
        # 执行任务
        st.divider()
        st.subheader("📋 执行结果")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            with st.spinner("🤖 Agent 团队正在协作处理你的任务..."):
                # 创建任务
                task = st.session_state.orchestrator.scheduler.create_task(
                    description=task_input,
                    priority=TaskPriority[priority],
                    context={"user_input": task_input}
                )
                
                status_text.text("正在分解任务和分配...")
                progress_bar.progress(20)
                
                # 执行
                results = st.session_state.orchestrator.scheduler.execute_parallel([task])
                
                progress_bar.progress(100)
                status_text.text("✅ 完成!")
                
                # 显示结果
                for i, result in enumerate(results, 1):
                    with st.expander(f"📄 Agent: {result.agent_name} - {'✅ 成功' if result.success else '❌ 失败'}", 
                                   expanded=True):
                        if result.success:
                            st.markdown(result.output)
                        else:
                            st.error(f"错误：{result.output}")
                        
                        st.caption(f"耗时：{result.duration:.2f}秒")
                
                # 保存历史
                st.session_state.task_history.append({
                    "task": task_input,
                    "results": results,
                    "timestamp": time.time()
                })
                
        except Exception as e:
            st.error(f"执行失败：{str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    elif clear_btn:
        st.session_state.task_input = ""
        st.session_state.results = []
        st.rerun()
    
    elif export_btn and st.session_state.results:
        # 导出结果
        export_content = "\n\n---\n\n".join([r.output for r in st.session_state.results])
        st.download_button(
            label="📥 下载结果",
            data=export_content,
            file_name=f"agent_result_{int(time.time())}.md",
            mime="text/markdown"
        )
    
    # 任务历史
    if st.session_state.task_history:
        st.divider()
        st.subheader("📜 任务历史")
        for i, history in enumerate(reversed(st.session_state.task_history[-5:]), 1):
            with st.expander(f"任务 #{len(st.session_state.task_history) - i + 1}: {history['task'][:50]}..."):
                st.caption(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(history['timestamp']))}")
                for result in history['results']:
                    st.markdown(f"**Agent**: {result.agent_name}")
                    st.markdown(result.output[:200] + "...")


if __name__ == "__main__":
    main()
