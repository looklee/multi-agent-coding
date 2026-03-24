"""
Agent 基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from api.llm import LLMClient, Message


@dataclass
class AgentState:
    """Agent 状态"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    status: str = "idle"  # idle, working, done, error
    current_task: str = ""
    completed_tasks: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, name: str, llm_client: LLMClient = None,
                 system_prompt: str = None, temperature: float = 0.7,
                 max_tokens: int = 4096, custom_system_prompt: str = None):
        self.name = name
        self.llm = llm_client or LLMClient()
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        # 支持自定义系统提示（可覆盖默认）
        if custom_system_prompt:
            self.system_prompt = custom_system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.state = AgentState(name=name)
        self.memory: List[Message] = []
        self._custom_instructions: str = ""

    DEFAULT_SYSTEM_PROMPT = "你是一个有帮助的 AI 助手"

    @property
    @abstractmethod
    def specialty(self) -> str:
        """Agent 专长描述"""
        pass
    
    def set_llm(self, llm_client: LLMClient):
        """设置 LLM 客户端"""
        self.llm = llm_client
    
    def clear_memory(self):
        """清空记忆"""
        self.memory = []
    
    def set_custom_instructions(self, instructions: str):
        """设置自定义指令（追加到系统提示）"""
        self._custom_instructions = instructions
    
    def add_to_memory(self, role: str, content: str):
        """添加消息到记忆"""
        self.memory.append(Message(role, content))

    def _build_messages(self, user_message: str) -> List[Message]:
        """构建消息列表"""
        # 合并系统提示和自定义指令
        system_prompt = self.system_prompt
        if self._custom_instructions:
            system_prompt = f"{self.system_prompt}\n\n自定义指令:\n{self._custom_instructions}"
        
        messages = [Message("system", system_prompt)]
        messages.extend(self.memory)
        messages.append(Message("user", user_message))
        return messages
    
    async def execute(self, task: str, context: str = None) -> str:
        """执行任务（异步）"""
        self.state.status = "working"
        self.state.current_task = task
        
        try:
            prompt = task
            if context:
                prompt = f"上下文信息:\n{context}\n\n任务:\n{task}"
            
            messages = self._build_messages(prompt)
            response = await self._call_llm(messages)
            
            self.add_to_memory("user", prompt)
            self.add_to_memory("assistant", response)
            
            self.state.status = "done"
            self.state.completed_tasks += 1
            return response
            
        except Exception as e:
            self.state.status = "error"
            raise e
    
    def execute_sync(self, task: str, context: str = None) -> str:
        """执行任务（同步）"""
        self.state.status = "working"
        self.state.current_task = task
        
        try:
            prompt = task
            if context:
                prompt = f"上下文信息:\n{context}\n\n任务:\n{task}"
            
            messages = self._build_messages(prompt)
            response = self.llm.chat(
                messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            ).content
            
            self.add_to_memory("user", prompt)
            self.add_to_memory("assistant", response)
            
            self.state.status = "done"
            self.state.completed_tasks += 1
            return response
            
        except Exception as e:
            self.state.status = "error"
            raise e
    
    async def _call_llm(self, messages: List[Message]) -> str:
        """调用 LLM（异步）"""
        # 实际使用时可以实现异步版本
        return self.llm.chat(
            messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        ).content
    
    def get_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "id": self.state.id,
            "name": self.name,
            "specialty": self.specialty,
            "status": self.state.status,
            "current_task": self.state.current_task,
            "completed_tasks": self.state.completed_tasks,
            "memory_size": len(self.memory)
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, status={self.state.status})"
