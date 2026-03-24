"""
沙箱模块测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.sandbox import (
    SecurityChecker, SandboxedExecutor, PythonREPL, 
    TestRunner, execute_code
)


class TestSecurityChecker:
    """安全检查器测试"""
    
    def setup_method(self):
        self.checker = SecurityChecker()
    
    def test_safe_code(self):
        """安全代码测试"""
        code = "x = 1 + 2\nprint(x)"
        is_safe, error = self.checker.check(code)
        assert is_safe is True
    
    def test_import_forbidden(self):
        """禁止导入测试"""
        code = "import os\nprint(os.getcwd())"
        is_safe, error = self.checker.check(code)
        assert is_safe is False
        assert "Import" in error
    
    def test_exec_forbidden(self):
        """禁止 exec 测试"""
        code = "exec('print(1)')"
        is_safe, error = self.checker.check(code)
        assert is_safe is False
    
    def test_allowed_builtins(self):
        """允许的内建函数测试"""
        code = """
result = sum(range(10))
print(result)
"""
        is_safe, error = self.checker.check(code)
        assert is_safe is True


class TestSandboxedExecutor:
    """沙箱执行器测试"""
    
    def setup_method(self):
        self.executor = SandboxedExecutor(timeout=5)
    
    def test_simple_print(self):
        """简单打印测试"""
        code = "print('Hello, World!')"
        result = self.executor.execute(code)
        assert result.success is True
        assert "Hello, World!" in result.stdout
    
    def test_calculation(self):
        """计算测试"""
        code = "result = sum(range(100))\nprint(result)"
        result = self.executor.execute(code)
        assert result.success is True
        assert "4950" in result.stdout
    
    def test_timeout(self):
        """超时测试"""
        code = "import time\ntime.sleep(10)"
        result = self.executor.execute(code)
        assert result.success is False
        assert "timed out" in result.error.lower()
    
    def test_security_violation(self):
        """安全违规测试"""
        code = "import os\nos.system('echo hello')"
        result = self.executor.execute(code)
        assert result.success is False
        assert "Security check failed" in result.error


class TestPythonREPL:
    """Python REPL 测试"""
    
    def setup_method(self):
        self.repl = PythonREPL()
    
    def test_single_command(self):
        """单条命令测试"""
        result = self.repl.run("x = 5")
        assert result.success is True
    
    def test_state_persistence(self):
        """状态持久化测试"""
        self.repl.run("counter = 0")
        result = self.repl.run("counter += 1")
        result = self.repl.run("print(counter)")
        assert result.success is True
        assert "1" in result.stdout
    
    def test_history(self):
        """历史记录测试"""
        self.repl.run("x = 1")
        self.repl.run("y = 2")
        history = self.repl.get_history()
        assert len(history) == 2
    
    def test_reset(self):
        """重置测试"""
        self.repl.run("x = 100")
        self.repl.reset()
        assert len(self.repl.namespace) == 0


class TestTestRunner:
    """测试运行器测试"""
    
    def setup_method(self):
        self.runner = TestRunner()
    
    def test_run_single_test(self):
        """运行单个测试测试"""
        code = """
def add(a, b):
    return a + b
"""
        test_code = """
assert add(2, 3) == 5
print("Test passed!")
"""
        result = self.runner.run_tests(code, test_code)
        assert result.success is True
    
    def test_run_multiple_test_cases(self):
        """运行多个测试用例测试"""
        code = """
def multiply(a, b):
    return a * b
"""
        test_cases = [
            {"input": "multiply(2, 3)", "expected": 6, "description": "2*3"},
            {"input": "multiply(0, 5)", "expected": 0, "description": "0*5"},
            {"input": "multiply(-2, 3)", "expected": -6, "description": "-2*3"},
        ]
        
        results = self.runner.run_with_assertions(code, test_cases)
        assert results["total"] == 3
        assert results["passed"] == 3


class TestExecuteCode:
    """便捷函数测试"""
    
    def test_convenience_function(self):
        """便捷函数测试"""
        result = execute_code("print(42)")
        assert result.success is True
        assert "42" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
