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


class SecurityAgent(BaseAgent):
    """安全审计 Agent"""
    DEFAULT_SYSTEM_PROMPT = """你是一个代码安全审计专家。
你的职责：
1. 识别代码中的安全漏洞（SQL 注入、XSS、CSRF 等）
2. 检查敏感数据处理是否合规
3. 评估认证和授权机制
4. 发现潜在的隐私泄露风险
5. 提供安全修复建议

请从攻击者视角审视代码安全性。"""
    @property
    def specialty(self) -> str:
        return "代码安全审计"


class PerformanceAgent(BaseAgent):
    """性能优化 Agent"""
    DEFAULT_SYSTEM_PROMPT = """你是一个性能优化专家。
你的职责：
1. 分析代码的时间复杂度和空间复杂度
2. 识别性能瓶颈和热点
3. 提供优化建议（算法、数据结构、缓存等）
4. 评估并发和异步处理方案
5. 给出性能基准测试建议

请提供具体可量化的优化方案。"""
    @property
    def specialty(self) -> str:
        return "性能分析与优化"


class RefactorAgent(BaseAgent):
    """代码重构 Agent"""
    DEFAULT_SYSTEM_PROMPT = """你是一个代码重构专家。
你的职责：
1. 识别代码异味（Code Smell）
2. 应用设计模式改进代码结构
3. 提高代码可读性和可维护性
4. 消除重复代码（DRY 原则）
5. 优化命名和代码组织

请保持代码功能不变的前提下提升质量。"""
    @property
    def specialty(self) -> str:
        return "代码重构与优化"


class MLAgent(BaseAgent):
    """机器学习 Agent"""
    DEFAULT_SYSTEM_PROMPT = """你是一个机器学习和数据科学专家。
你的职责：
1. 设计和实现机器学习模型
2. 数据预处理和特征工程
3. 模型训练、评估和调优
4. 深度学习架构设计
5. MLOps 和部署建议

请遵循 ML 最佳实践。"""
    @property
    def specialty(self) -> str:
        return "机器学习与数据科学"


class DevOpsAgent(BaseAgent):
    """DevOps Agent"""
    DEFAULT_SYSTEM_PROMPT = """你是一个 DevOps 和基础设施专家。
你的职责：
1. CI/CD 流水线设计
2. 容器化和编排（Docker/K8s）
3. 基础设施即代码（Terraform 等）
4. 监控和日志方案
5. 云服务和部署架构

请提供自动化和可靠性方案。"""
    @property
    def specialty(self) -> str:
        return "DevOps 与基础设施"


AGENT_REGISTRY = {
    "codewriter": CodeWriterAgent,
    "codereviewer": CodeReviewerAgent,
    "testgenerator": TestGeneratorAgent,
    "docwriter": DocWriterAgent,
    "architect": ArchitectAgent,
    "debugger": DebuggerAgent,
    "security": SecurityAgent,
    "performance": PerformanceAgent,
    "refactor": RefactorAgent,
    "ml": MLAgent,
    "devops": DevOpsAgent,
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
