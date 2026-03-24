# Multi-Agent Coding Assistant

多 Agent 协作编码助手，通过多个专业化 Agent 协作完成复杂的编程任务。

## 痛点解决

本项目旨在解决当前 AI 编程助手的以下痛点：

1. **单一模型能力局限** - 不同任务需要不同专长，单一模型难以兼顾
2. **缺乏任务分解** - 复杂任务难以一次性完成
3. **无法协作** - 代码生成、审查、测试需要不同视角
4. **上下文丢失** - 长对话中容易遗忘早期信息
5. **无法并行** - 独立子任务可以并行处理提高效率

## 特性

- 🤖 **多 Agent 协作** - 6 种专用 Agent：代码生成、审查、测试、文档、架构、调试
- 🔌 **多模型支持** - 支持 Qwen、Doubao、Claude 等主流大模型
- 📋 **智能任务分解** - 自动将复杂任务分解为可执行的子任务
- ⚡ **并行执行** - 支持多 Agent 并行处理子任务
- 💾 **记忆管理** - 每个 Agent 维护独立记忆上下文
- 🎯 **灵活配置** - YAML 配置文件 + 环境变量

## 项目结构

```
multi-agent-coding/
├── api/              # LLM API 封装
│   └── llm.py
├── agents/           # Agent 定义
│   ├── base.py       # 基类
│   └── __init__.py   # 专用 Agent
├── core/             # 核心调度
│   └── orchestrator.py
├── config/           # 配置文件
│   └── config.example.yaml
├── main.py           # 入口
├── requirements.txt
├── .env.example
└── README.md
```

## 安装

```bash
# 克隆/进入项目
cd multi-agent-coding

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

## 使用

### 命令行使用

```bash
# 使用默认配置（Qwen）
python main.py "为快速排序生成 Python 实现和测试用例"

# 指定提供商
python main.py -p doubao "分析这段代码的性能问题"

# 指定 Agent
python main.py -a codewriter -a codereviewer "实现一个 REST API"

# 交互模式
python main.py
```

### 代码使用

```python
from api.llm import create_client
from agents import create_agent
from core.orchestrator import MultiAgentOrchestrator

# 创建编排器
orchestrator = MultiAgentOrchestrator()
llm = create_client(provider="qwen", api_key="your-key")
orchestrator.set_llm(llm)

# 添加 Agent
orchestrator.add_agent("codewriter", create_agent("codewriter", llm_client=llm))
orchestrator.add_agent("codereviewer", create_agent("codereviewer", llm_client=llm))

# 执行任务
results = orchestrator.run_sync("实现一个线程安全的缓存类")

for result in results:
    print(f"Agent: {result.agent_name}")
    print(f"输出：{result.output}")
```

## 可用 Agent

| Agent | 专长 | 描述 |
|-------|------|------|
| codewriter | 代码生成 | 生成高质量、可维护的代码 |
| codereviewer | 代码审查 | 检查代码质量和潜在问题 |
| testgenerator | 测试生成 | 生成全面的测试用例 |
| docwriter | 文档编写 | 编写技术文档和注释 |
| architect | 架构设计 | 系统架构和技术选型 |
| debugger | 问题调试 | 分析和解决代码问题 |

## 支持的模型

| 提供商 | 模型 | 环境变量 |
|--------|------|----------|
| Qwen | qwen-coding-plus | QWEN_API_KEY |
| Doubao | doubao-pro-32k | DOUBAO_API_KEY |
| Claude | claude-3-5-sonnet | CLAUDE_API_KEY |

## 配置示例

```yaml
# config/config.yaml
default_model:
  provider: qwen
  model: qwen-coding-plus

agents:
  codewriter:
    temperature: 0.7
    max_tokens: 4096
  codereviewer:
    temperature: 0.3
    max_tokens: 2048
```

## 扩展

### 添加新 Agent

```python
from agents.base import BaseAgent

class CustomAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = "你的系统提示词"
    
    @property
    def specialty(self) -> str:
        return "你的专长描述"

# 注册
from agents import AGENT_REGISTRY
AGENT_REGISTRY["custom"] = CustomAgent
```

### 添加新模型提供商

```python
from api.llm import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    def chat(self, messages, **kwargs):
        # 实现你的 API 调用
        pass
```

## 许可证

MIT
