"""Agents module"""
from .base import BaseAgent, AgentState

# Agent 实现
class CodeWriterAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个专业的代码生成助手。"""
    @property
    def specialty(self) -> str:
        return "代码生成与实现"

class CodeReviewerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个严格的代码审查专家。"""
    @property
    def specialty(self) -> str:
        return "代码审查与质量评估"

class TestGeneratorAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个测试用例生成专家。"""
    @property
    def specialty(self) -> str:
        return "测试用例生成"

class DocWriterAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个技术文档编写专家。"""
    @property
    def specialty(self) -> str:
        return "技术文档编写"

class ArchitectAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个资深软件架构师。"""
    @property
    def specialty(self) -> str:
        return "系统架构设计"

class DebuggerAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = """你是一个调试和问题解决专家。"""
    @property
    def specialty(self) -> str:
        return "问题调试与解决"

AGENT_REGISTRY = {
    "codewriter": CodeWriterAgent,
    "codereviewer": CodeReviewerAgent,
    "testgenerator": TestGeneratorAgent,
    "docwriter": DocWriterAgent,
    "architect": ArchitectAgent,
    "debugger": DebuggerAgent,
}

def create_agent(agent_type: str, name: str = None, llm_client = None, **kwargs):
    from api.llm import LLMClient
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"未知的 Agent 类型：{agent_type}")
    agent_cls = AGENT_REGISTRY[agent_type]
    name = name or agent_type
    return agent_cls(name=name, llm_client=llm_client, **kwargs)

def get_available_agents() -> list:
    return list(AGENT_REGISTRY.keys())

__all__ = ["BaseAgent", "create_agent", "get_available_agents", "AGENT_REGISTRY"]
