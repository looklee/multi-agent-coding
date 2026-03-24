"""
代码执行沙箱
- 安全的代码执行环境
- 资源和权限限制
- 执行结果捕获
"""
import ast
import io
import sys
import uuid
import tempfile
import os
import subprocess
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import threading
import time


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    output: Any = None
    error: str = ""
    execution_time: float = 0.0
    memory_used: int = 0
    metadata: Dict = field(default_factory=dict)


class SecurityChecker:
    """代码安全检查器"""
    
    # 禁止的 AST 节点
    FORBIDDEN_NODES = {
        'Import', 'ImportFrom',  # 禁止导入
        'Exec', 'Eval',  # 禁止 exec/eval
        'Compile',  # 禁止编译
        'Open',  # 禁止文件操作
        'Call',  # 限制函数调用（白名单）
    }
    
    # 允许的内置函数
    ALLOWED_BUILTINS = {
        'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list', 'dict',
        'set', 'tuple', 'sum', 'min', 'max', 'abs', 'round', 'sorted', 'reversed',
        'enumerate', 'zip', 'map', 'filter', 'isinstance', 'issubclass',
        'getattr', 'setattr', 'hasattr', 'dir', 'type', 'repr', 'format',
        'ord', 'chr', 'hex', 'oct', 'bin', 'pow', 'divmod'
    }
    
    # 允许的模块
    ALLOWED_MODULES = {'math', 'random', 'collections', 'itertools', 'functools', 're'}
    
    def check(self, code: str) -> tuple[bool, str]:
        """检查代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        # 检查禁止的节点
        for node in ast.walk(tree):
            node_name = type(node).__name__
            
            if node_name == 'Import':
                return False, "Import statements are not allowed"
            
            if node_name == 'ImportFrom':
                module = getattr(node, 'module', '')
                if module not in self.ALLOWED_MODULES:
                    return False, f"Import from '{module}' is not allowed"
            
            if node_name == 'Call':
                # 检查函数调用
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name not in self.ALLOWED_BUILTINS:
                        return False, f"Function '{func_name}' is not allowed"
        
        return True, ""


class SandboxedExecutor:
    """沙箱执行器"""
    
    def __init__(self, timeout: int = 10, max_memory_mb: int = 128):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.security_checker = SecurityChecker()
    
    def execute(self, code: str, input_data: str = "") -> ExecutionResult:
        """执行代码"""
        start_time = time.time()
        
        # 安全检查
        is_safe, error_msg = self.security_checker.check(code)
        if not is_safe:
            return ExecutionResult(
                success=False,
                error=f"Security check failed: {error_msg}"
            )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # 执行
            result = subprocess.run(
                [sys.executable, temp_path],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self._get_restricted_env()
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                metadata={"returncode": result.returncode}
            )
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timed out after {self.timeout}s"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e)
            )
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _get_restricted_env(self) -> Dict:
        """获取受限的环境变量"""
        env = os.environ.copy()
        # 移除敏感环境变量
        for key in list(env.keys()):
            if any(s in key.lower() for s in ['key', 'secret', 'password', 'token']):
                del env[key]
        return env
    
    def execute_in_namespace(self, code: str, namespace: Dict = None) -> ExecutionResult:
        """在命名空间中执行（更轻量级的沙箱）"""
        if namespace is None:
            namespace = {
                '__builtins__': {k: v for k, v in __builtins__.items() 
                               if k in SecurityChecker.ALLOWED_BUILTINS}
            }
        
        # 安全检查
        is_safe, error_msg = self.security_checker.check(code)
        if not is_safe:
            return ExecutionResult(success=False, error=error_msg)
        
        # 捕获输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        start_time = time.time()
        
        try:
            exec(code, namespace)
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=True,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=execution_time,
                output=namespace.get('result')
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                stderr=stderr_capture.getvalue()
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class PythonREPL:
    """Python REPL 沙箱"""
    
    def __init__(self):
        self.executor = SandboxedExecutor()
        self.history: List[Dict] = []
        self.namespace = {}
    
    def run(self, code: str) -> ExecutionResult:
        """运行代码"""
        result = self.executor.execute_in_namespace(code, self.namespace)
        
        self.history.append({
            "code": code,
            "result": result,
            "timestamp": time.time()
        })
        
        return result
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取执行历史"""
        return self.history[-limit:]
    
    def reset(self):
        """重置命名空间"""
        self.namespace = {}
        self.history.clear()


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.executor = SandboxedExecutor(timeout=60)
    
    def run_tests(self, code: str, test_code: str) -> ExecutionResult:
        """运行测试"""
        combined = f"{code}\n\n{test_code}"
        return self.executor.execute(combined)
    
    def run_with_assertions(self, code: str, test_cases: List[Dict]) -> Dict:
        """运行多个测试用例"""
        results = []
        
        for i, test in enumerate(test_cases):
            test_code = f"""
{code}

# Test case {i + 1}: {test.get('description', '')}
result = {test['input']}
expected = {test['expected']}
assert result == expected, f"Failed: {{result}} != {{expected}}"
print(f"Test {i + 1} passed")
"""
            result = self.executor.execute(test_code)
            results.append({
                "test_case": i + 1,
                "description": test.get('description', ''),
                "passed": result.success,
                "error": result.error
            })
        
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "results": results
        }


# 全局实例
_repl: Optional[PythonREPL] = None
_test_runner: Optional[TestRunner] = None


def get_repl() -> PythonREPL:
    """获取 REPL 实例"""
    global _repl
    if _repl is None:
        _repl = PythonREPL()
    return _repl


def get_test_runner() -> TestRunner:
    """获取测试运行器"""
    global _test_runner
    if _test_runner is None:
        _test_runner = TestRunner()
    return _test_runner


def execute_code(code: str, timeout: int = 10) -> ExecutionResult:
    """便捷执行代码"""
    executor = SandboxedExecutor(timeout=timeout)
    return executor.execute(code)
