"""
多模型 API 统一封装
支持 Qwen、Doubao、Claude 等主流大模型
"""
import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator
import requests
from dotenv import load_dotenv

load_dotenv()


class Message:
    """消息对象"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    """LLM 响应对象"""
    def __init__(self, content: str, usage: Dict = None, raw: Dict = None):
        self.content = content
        self.usage = usage or {}
        self.raw = raw or {}
    
    def __str__(self) -> str:
        return self.content


class BaseLLMProvider(ABC):
    """LLM 提供者基类"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        """流式聊天"""
        pass


class QwenProvider(BaseLLMProvider):
    """阿里云通义千问"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        # DashScope API 格式
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 提取参数，DashScope 支持的参数
        params = {}
        if "temperature" in kwargs:
            params["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            params["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            params["top_p"] = kwargs["top_p"]
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [m.to_dict() for m in messages]
            },
            "parameters": params
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # DashScope 响应格式
        output = data.get("output", {})
        usage = data.get("usage", {})
        
        return LLMResponse(
            content=output.get("text", "") or output.get("choices", [{}])[0].get("message", {}).get("content", ""),
            usage=usage,
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        # 简化实现，实际可添加 SSE 流式支持
        response = self.chat(messages, **kwargs)
        yield response.content


class DoubaoProvider(BaseLLMProvider):
    """火山引擎豆包"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            **kwargs
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        response = self.chat(messages, **kwargs)
        yield response.content


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Claude 格式转换
        system_msg = None
        chat_messages = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_messages.append(m.to_dict())
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            **kwargs
        }
        if system_msg:
            payload["system"] = system_msg
        
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        return LLMResponse(
            content=data["content"][0]["text"],
            usage=data.get("usage", {}),
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        response = self.chat(messages, **kwargs)
        yield response.content


class DeepSeekProvider(BaseLLMProvider):
    """深度求索 DeepSeek"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "deepseek-chat",
            "messages": [m.to_dict() for m in messages],
            **kwargs
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        response = self.chat(messages, **kwargs)
        yield response.content


class MoonshotProvider(BaseLLMProvider):
    """月之暗面 Moonshot (Kimi)"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "moonshot-v1-8k",
            "messages": [m.to_dict() for m in messages],
            **kwargs
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            usage=data.get("usage", {}),
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        response = self.chat(messages, **kwargs)
        yield response.content


class GeminiProvider(BaseLLMProvider):
    """Google Gemini"""
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}
        
        # Gemini 格式转换
        contents = []
        for m in messages:
            if m.role != "system":
                contents.append({
                    "role": "user" if m.role == "user" else "model",
                    "parts": [{"text": m.content}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                **kwargs
            }
        }
        
        resp = requests.post(url, params=params, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        return LLMResponse(
            content=data["candidates"][0]["content"]["parts"][0]["text"],
            usage=data.get("usageMetadata", {}),
            raw=data
        )
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        response = self.chat(messages, **kwargs)
        yield response.content


class LLMClient:
    """统一 LLM 客户端"""

    PROVIDERS = {
        "qwen": QwenProvider,
        "doubao": DoubaoProvider,
        "claude": ClaudeProvider,
        "deepseek": DeepSeekProvider,
        "moonshot": MoonshotProvider,
        "gemini": GeminiProvider,
    }
    
    def __init__(self, provider: str = "qwen", api_key: str = None, 
                 base_url: str = None, model: str = None):
        self.provider_name = provider
        
        if provider not in self.PROVIDERS:
            raise ValueError(f"不支持的 provider: {provider}")
        
        provider_cls = self.PROVIDERS[provider]
        
        # 默认配置
        defaults = {
            "qwen": {
                "base_url": "https://dashscope.aliyuncs.com/api/v1",
                "model": "qwen-plus"
            },
            "doubao": {
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-pro-32k"
            },
            "claude": {
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-5-sonnet-20241022"
            },
            "deepseek": {
                "base_url": None,
                "model": "deepseek-chat"
            },
            "moonshot": {
                "base_url": None,
                "model": "moonshot-v1-8k"
            },
            "gemini": {
                "base_url": None,
                "model": "gemini-1.5-flash"
            }
        }
        
        api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        base_url = base_url or defaults.get(provider, {}).get("base_url")
        model = model or defaults.get(provider, {}).get("model")
        
        if not api_key:
            raise ValueError(f"未找到 {provider} API Key，请设置环境变量")
        
        self.provider = provider_cls(api_key, base_url, model)
    
    def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        return self.provider.chat(messages, **kwargs)
    
    def chat_stream(self, messages: List[Message], **kwargs) -> Generator[str, None, None]:
        return self.provider.chat_stream(messages, **kwargs)
    
    def simple_chat(self, user_message: str, system_message: str = None, **kwargs) -> str:
        """简单对话接口"""
        messages = []
        if system_message:
            messages.append(Message("system", system_message))
        messages.append(Message("user", user_message))
        return self.chat(messages, **kwargs).content


def create_client(provider: str = "qwen", **kwargs) -> LLMClient:
    """工厂函数创建客户端"""
    return LLMClient(provider=provider, **kwargs)
