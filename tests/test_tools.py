"""
工具模块测试
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools import (
    ToolRegistry, FileReadTool, FileWriteTool, ShellTool,
    CalculatorTool, CodeAnalysisTool, get_tool_registry
)


class TestCalculatorTool:
    """计算器工具测试"""
    
    def setup_method(self):
        self.tool = CalculatorTool()
    
    def test_basic_arithmetic(self):
        """基础算术测试"""
        result = self.tool.execute(expression="2 + 3")
        assert result.success is True
        assert result.output == 5
    
    def test_complex_expression(self):
        """复杂表达式测试"""
        result = self.tool.execute(expression="2 + 3 * 4")
        assert result.success is True
        assert result.output == 14
    
    def test_invalid_expression(self):
        """无效表达式测试"""
        result = self.tool.execute(expression="2 + + 3")
        assert result.success is False
    
    def test_forbidden_characters(self):
        """禁止字符测试"""
        result = self.tool.execute(expression="2 + __import__('os')")
        assert result.success is False


class TestFileTools:
    """文件工具测试"""
    
    def setup_method(self):
        self.read_tool = FileReadTool()
        self.write_tool = FileWriteTool()
        self.temp_file = None
    
    def teardown_method(self):
        if self.temp_file and os.path.exists(self.temp_file):
            os.unlink(self.temp_file)
    
    def test_write_and_read(self):
        """写入和读取测试"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            self.temp_file = f.name
            f.write("Hello, World!")
        
        result = self.read_tool.execute(path=self.temp_file)
        assert result.success is True
        assert "Hello, World!" in result.output
    
    def test_read_nonexistent(self):
        """读取不存在文件测试"""
        result = self.read_tool.execute(path="/nonexistent/file.txt")
        assert result.success is False
    
    def test_write_new_file(self):
        """写入新文件测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            result = self.write_tool.execute(path=path, content="Test content")
            
            assert result.success is True
            assert os.path.exists(path)


class TestShellTool:
    """Shell 工具测试"""
    
    def setup_method(self):
        self.tool = ShellTool()
    
    def test_echo_command(self):
        """echo 命令测试"""
        result = self.tool.execute(command="echo Hello")
        assert result.success is True
        assert "Hello" in result.output
    
    def test_invalid_command(self):
        """无效命令测试"""
        result = self.tool.execute(command="nonexistent_command_xyz")
        # 命令可能失败，但不一定抛出异常
        assert result is not None
    
    def test_timeout(self):
        """超时测试"""
        # 这个测试可能因系统而异
        result = self.tool.execute(command="sleep 5", timeout=1)
        assert result.success is False
        assert "timed out" in result.error.lower()


class TestCodeAnalysisTool:
    """代码分析工具测试"""
    
    def setup_method(self):
        self.tool = CodeAnalysisTool()
    
    def test_simple_function(self):
        """简单函数测试"""
        code = """
def hello():
    print("Hello")
    
def world():
    return 42
"""
        result = self.tool.execute(code=code, language="python")
        assert result.success is True
        assert result.output["functions"] == 2
        assert result.output["classes"] == 0
    
    def test_with_class(self):
        """含类的代码测试"""
        code = """
class MyClass:
    def method(self):
        pass

def func():
    if True:
        for i in range(10):
            pass
"""
        result = self.tool.execute(code=code, language="python")
        assert result.success is True
        assert result.output["classes"] == 1
        assert result.output["functions"] == 2


class TestToolRegistry:
    """工具注册表测试"""
    
    def setup_method(self):
        self.registry = ToolRegistry()
    
    def test_register_tool(self):
        """注册工具测试"""
        tool = CalculatorTool()
        self.registry.register(tool)
        
        definition = self.registry.get_tool("calculator")
        assert definition is not None
        assert definition.name == "calculator"
    
    def test_execute_tool(self):
        """执行工具测试"""
        self.registry.register(CalculatorTool())
        
        result = self.registry.execute_tool("calculator", expression="10 + 20")
        assert result.success is True
        assert result.output == 30
    
    def test_execute_nonexistent_tool(self):
        """执行不存在的工具测试"""
        result = self.registry.execute_tool("nonexistent_tool")
        assert result.success is False
        assert "not found" in result.error


class TestGetToolRegistry:
    """全局工具注册表测试"""
    
    def test_singleton(self):
        """单例模式测试"""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        assert registry1 is registry2
    
    def test_builtin_tools(self):
        """内置工具测试"""
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        # 检查是否有内置工具
        tool_names = [t.name for t in tools]
        assert "calculator" in tool_names
        assert "shell_exec" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
