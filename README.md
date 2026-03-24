# Multi-Agent Coding Assistant

多 Agent 协作编码助手，通过多个专业化 Agent 协作完成复杂的编程任务。

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 命令行使用
python main.py "为快速排序生成 Python 实现和测试用例"

# Web UI
streamlit run webui.py
```

## 痛点解决

本项目旨在解决当前 AI 编程助手的以下痛点：

1. **单一模型能力局限** - 不同任务需要不同专长，单一模型难以兼顾
2. **缺乏任务分解** - 复杂任务难以一次性完成
3. **无法协作** - 代码生成、审查、测试需要不同视角
4. **上下文丢失** - 长对话中容易遗忘早期信息
5. **无法并行** - 独立子任务可以并行处理提高效率

## ✨ 特性

- 🤖 **11 种专用 Agent** - 覆盖编程全流程
- 🔌 **6 个模型提供商** - Qwen, DeepSeek, Moonshot, Doubao, Claude, Gemini
- 📋 **智能任务分解** - 自动将复杂任务分解为可执行的子任务
- ⚡ **并行执行** - 支持多 Agent 并行处理子任务
- 🎯 **优先级调度** - 支持任务优先级和依赖管理
- 💾 **记忆管理** - 每个 Agent 维护独立记忆上下文
- 🔥 **配置热重载** - YAML 配置文件修改后自动生效
- 🎨 **Web 界面** - 美观的 Streamlit Web UI
- 💬 **自定义指令** - Agent 支持自定义系统提示
- 💰 **成本优化** - Token 缓存、智能路由、成本统计
- 📊 **执行追溯** - 完整决策链和日志记录
- 👤 **人机协作** - 人工审核节点、实时反馈
- 🛠️ **工具调用** - 文件操作、Shell、网络搜索、代码分析等
- 🔒 **代码沙箱** - 安全执行生成的代码
- 🧠 **自学习** - 从经验中学习并优化行为
- 🤝 **多 Agent 协作** - 消息总线、黑板系统、协商机制

## 📊 项目结构

```
multi-agent-coding/
├── api/              # LLM API 封装
│   └── llm.py        # 支持 6 个提供商
├── agents/           # 11 种 Agent
│   ├── base.py       # 基类
│   └── __init__.py   # Agent 定义
├── core/             # 核心调度
│   └── orchestrator.py
├── config/           # 配置管理
│   └── manager.py    # 热重载配置
├── main.py           # CLI 入口
├── webui.py          # Web UI
├── requirements.txt
└── README.md
```

## 🤖 可用 Agent

| Agent | 专长 | 描述 |
|-------|------|------|
| codewriter | 代码生成 | 生成高质量、可维护的代码 |
| codereviewer | 代码审查 | 检查代码质量和潜在问题 |
| testgenerator | 测试生成 | 生成全面的测试用例 |
| docwriter | 文档编写 | 编写技术文档和注释 |
| architect | 架构设计 | 系统架构和技术选型 |
| debugger | 问题调试 | 分析和解决代码问题 |
| **security** | 安全审计 | 识别安全漏洞和风险 |
| **performance** | 性能优化 | 性能分析和优化建议 |
| **refactor** | 代码重构 | 识别代码异味并重构 |
| **ml** | 机器学习 | ML 模型设计和实现 |
| **devops** | DevOps | CI/CD 和基础设施 |

## 🔌 支持的模型

| 提供商 | 默认模型 | 环境变量 |
|--------|----------|----------|
| Qwen | qwen-plus | QWEN_API_KEY |
| DeepSeek | deepseek-chat | DEEPSEEK_API_KEY |
| Moonshot | moonshot-v1-8k | MOONSHOT_API_KEY |
| Doubao | doubao-pro-32k | DOUBAO_API_KEY |
| Claude | claude-3-5-sonnet | CLAUDE_API_KEY |
| Gemini | gemini-1.5-flash | GEMINI_API_KEY |

## 💻 使用方式

### 命令行

```bash
# 基础使用
python main.py "实现一个线程安全的缓存类"

# 指定提供商
python main.py -p deepseek "分析代码性能问题"

# 指定 Agent
python main.py -a security -a performance "审计这段代码"

# 交互模式
python main.py
```

### Web UI

```bash
streamlit run webui.py
```

访问 http://localhost:8501

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_tools.py -v
pytest tests/test_sandbox.py -v
```

### 代码使用

```python
from api.llm import create_client
from agents import create_agent
from core.orchestrator import MultiAgentOrchestrator, TaskPriority

# 创建编排器
orchestrator = MultiAgentOrchestrator()
llm = create_client(provider="qwen", api_key="your-key")
orchestrator.set_llm(llm)

# 添加 Agent
orchestrator.add_agent("codewriter", create_agent("codewriter", llm_client=llm))
orchestrator.add_agent("security", create_agent("security", llm_client=llm))

# 创建带优先级和依赖的任务
task1 = orchestrator.scheduler.create_task("生成代码", priority=TaskPriority.HIGH)
task2 = orchestrator.scheduler.create_task("安全审计", dependencies=[task1.id])

# 执行
import asyncio
results = asyncio.run(orchestrator.scheduler.execute_parallel())
```

## ⚙️ 配置

### 环境变量

```bash
# .env
QWEN_API_KEY=sk-xxx
DEEPSEEK_API_KEY=xxx
MOONSHOT_API_KEY=xxx
```

### YAML 配置

```yaml
# config/config.yaml
default_model:
  provider: qwen

agents:
  codewriter:
    temperature: 0.7
    max_tokens: 4096
    system_prompt: "你是专业的代码生成助手"
  
  security:
    temperature: 0.3
    max_tokens: 2048

scheduler:
  max_concurrent_tasks: 3
  retry_attempts: 2
```

配置文件修改后自动重载！

## 🛠️ 扩展

### 添加新 Agent

```python
from agents.base import BaseAgent

class CustomAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = "你的系统提示词"
    
    @property
    def specialty(self) -> str:
        return "你的专长描述"

# 注册到 agents/__init__.py 的 AGENT_REGISTRY
```

### 自定义 Agent 指令

```python
agent = create_agent("codewriter", llm_client=llm)
agent.set_custom_instructions("请使用函数式编程风格")
```

## 📄 许可证

MIT
