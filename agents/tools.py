"""
工具调用模块
- 工具注册和发现
- 自动工具选择
- 工具执行和结果处理
"""
import inspect
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps
import subprocess
import requests


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter]
    func: Callable
    returns: str = ""
    
    def to_schema(self) -> Dict:
        """转换为 JSON Schema 格式"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: str = ""
    metadata: Dict = field(default_factory=dict)


class BaseTool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
    
    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        sig = inspect.signature(self.execute)
        parameters = []
        
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == dict:
                param_type = "object"
            elif param.annotation == list:
                param_type = "array"
            
            parameters.append(ToolParameter(
                name=name,
                type=param_type,
                description="",
                required=param.default == inspect.Parameter.empty
            ))
        
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=parameters,
            func=self.execute
        )


class ToolRegistry:
    """工具注册表"""
    
    _instance = None
    _tools: Dict[str, ToolDefinition] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, tool: BaseTool):
        """注册工具"""
        definition = tool.get_definition()
        self._tools[tool.name] = definition
    
    def register_function(self, name: str = None, description: str = ""):
        """装饰器：注册函数为工具"""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                return ToolResult(success=True, output=result)
            
            # 解析参数
            sig = inspect.signature(func)
            parameters = []
            for param_name, param in sig.parameters.items():
                parameters.append(ToolParameter(
                    name=param_name,
                    type="string",
                    required=param.default == inspect.Parameter.empty
                ))
            
            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=description or func.__doc__ or "",
                parameters=parameters,
                func=wrapper
            )
            return wrapper
        return decorator
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[ToolDefinition]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_tool_schemas(self) -> List[Dict]:
        """获取所有工具的 JSON Schema"""
        return [tool.to_schema() for tool in self._tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(success=False, output=None, error=f"Tool '{name}' not found")
        
        try:
            result = tool.func(**kwargs)
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ============ 内置工具实现 ============

class FileReadTool(BaseTool):
    """读取文件内容"""
    name = "file_read"
    description = "读取本地文件的内容"
    
    def execute(self, path: str) -> ToolResult:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ToolResult(success=True, output=content, metadata={"path": path, "length": len(content)})
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class FileWriteTool(BaseTool):
    """写入文件"""
    name = "file_write"
    description = "写入内容到本地文件"
    
    def execute(self, path: str, content: str, mode: str = "w") -> ToolResult:
        try:
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            return ToolResult(success=True, output=f"Successfully wrote to {path}", metadata={"path": path})
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ShellTool(BaseTool):
    """执行 Shell 命令"""
    name = "shell_exec"
    description = "执行 Shell 命令并返回输出"
    
    def execute(self, command: str, timeout: int = 30) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return ToolResult(
                success=True,
                output=result.stdout,
                metadata={
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None, error="Command timed out")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WebSearchTool(BaseTool):
    """网络搜索工具"""
    name = "web_search"
    description = "搜索网络获取信息（使用 DuckDuckGo HTML 接口）"
    
    def execute(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            # 使用 DuckDuckGo HTML 搜索
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            
            resp = requests.post(url, data=params, timeout=10)
            resp.raise_for_status()
            
            # 简单解析结果
            results = []
            html = resp.text
            
            # 提取标题和链接
            title_pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
            matches = re.findall(title_pattern, html)
            
            for link, title in matches[:num_results]:
                results.append({"title": title, "link": link})
            
            return ToolResult(success=True, output=results, metadata={"query": query})
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class UrlFetchTool(BaseTool):
    """获取 URL 内容"""
    name = "url_fetch"
    description = "获取指定 URL 的内容"
    
    def execute(self, url: str, timeout: int = 10) -> ToolResult:
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return ToolResult(
                success=True,
                output=resp.text[:5000],  # 限制长度
                metadata={"url": url, "status": resp.status_code}
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CalculatorTool(BaseTool):
    """计算器"""
    name = "calculator"
    description = "执行数学计算"
    
    def execute(self, expression: str) -> ToolResult:
        try:
            # 安全的数学计算
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return ToolResult(success=False, output=None, error="Invalid characters in expression")
            
            result = eval(expression, {"__builtins__": {}}, {})
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CodeAnalysisTool(BaseTool):
    """代码分析工具"""
    name = "code_analyze"
    description = "分析代码的结构、复杂度等"
    
    def execute(self, code: str, language: str = "python") -> ToolResult:
        try:
            lines = code.split('\n')
            
            analysis = {
                "total_lines": len(lines),
                "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
                "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
                "blank_lines": sum(1 for l in lines if not l.strip()),
                "functions": len(re.findall(r'\bdef\s+\w+', code)),
                "classes": len(re.findall(r'\bclass\s+\w+', code)),
            }
            
            # 估算复杂度
            complexity = (
                analysis["functions"] * 2 +
                analysis["classes"] * 3 +
                len(re.findall(r'\bif\b', code)) +
                len(re.findall(r'\bfor\b', code)) +
                len(re.findall(r'\bwhile\b', code))
            )
            
            analysis["estimated_complexity"] = complexity
            
            return ToolResult(success=True, output=analysis)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# 全局注册表
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        
        # 注册内置工具
        _registry.register(FileReadTool())
        _registry.register(FileWriteTool())
        _registry.register(ShellTool())
        _registry.register(WebSearchTool())
        _registry.register(UrlFetchTool())
        _registry.register(CalculatorTool())
        _registry.register(CodeAnalysisTool())
    
    return _registry


def tool(name: str = None, description: str = ""):
    """装饰器：注册函数为工具"""
    registry = get_tool_registry()
    return registry.register_function(name, description)


# 使用示例
if __name__ == "__main__":
    registry = get_tool_registry()
    
    print("可用工具:")
    for tool in registry.list_tools():
        print(f"  - {tool.name}: {tool.description}")
    
    # 执行工具
    result = registry.execute_tool("calculator", expression="2 + 3 * 4")
    print(f"\n计算器结果：{result.output}")
