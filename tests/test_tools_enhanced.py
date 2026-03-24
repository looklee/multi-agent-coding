"""
增强工具和额外工具测试
"""
import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools_enhanced import (
    RetryConfig, RetryError, timeout, validate_result,
    CircuitBreaker, RateLimiter, non_empty_result,
    type_validator, range_validator
)
from agents.tools_extra import (
    DatabaseTool, GitTool, HTTPTool, JSONTool, DateTimeTool
)


class TestRetry:
    """重试机制测试"""
    
    def test_retry_success(self):
        """重试成功测试"""
        attempt_count = [0]
        
        from agents.tools_enhanced import retry
        
        @retry(RetryConfig(max_attempts=3))
        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert attempt_count[0] == 2
    
    def test_retry_failure(self):
        """重试失败测试"""
        from agents.tools_enhanced import retry
        
        @retry(RetryConfig(max_attempts=3, base_delay=0.1))
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryError) as exc_info:
            always_fails()
        
        assert exc_info.value.attempts == 3


class TestTimeout:
    """超时机制测试"""
    
    def test_timeout_success(self):
        """超时成功测试"""
        from agents.tools_enhanced import timeout as timeout_decorator
        
        @timeout_decorator(5)
        def quick_func():
            return "done"
        
        result = quick_func()
        assert result == "done"
    
    def test_timeout_triggered(self):
        """超时触发测试"""
        import time
        from agents.tools_enhanced import timeout as timeout_decorator
        
        @timeout_decorator(0.5)
        def slow_func():
            time.sleep(2)
            return "done"
        
        with pytest.raises(TimeoutError):
            slow_func()


class TestValidation:
    """验证机制测试"""
    
    def test_non_empty_validation(self):
        """非空验证测试"""
        result = non_empty_result("valid content")
        assert result.valid is True
        
        result = non_empty_result("")
        assert result.valid is False
    
    def test_type_validator(self):
        """类型验证测试"""
        validator = type_validator(int)
        
        result = validator(42)
        assert result.valid is True
        
        result = validator("not an int")
        assert result.valid is False
    
    def test_range_validator(self):
        """范围验证测试"""
        validator = range_validator(min_val=0, max_val=100)
        
        result = validator(50)
        assert result.valid is True
        
        result = validator(-1)
        assert result.valid is False
        
        result = validator(101)
        assert result.valid is False


class TestCircuitBreaker:
    """熔断器测试"""
    
    def test_circuit_breaker_opens(self):
        """熔断器打开测试"""
        cb = CircuitBreaker(failure_threshold=3)
        
        def failing_func():
            raise ValueError("Error")
        
        # 触发多次失败
        for i in range(3):
            try:
                cb.call(failing_func)
            except:
                pass
        
        # 熔断器应该打开
        assert cb.state == "open"
    
    def test_circuit_breaker_resets(self):
        """熔断器重置测试"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)
        
        def failing_func():
            raise ValueError("Error")
        
        # 触发失败
        for i in range(2):
            try:
                cb.call(failing_func)
            except:
                pass
        
        assert cb.state == "open"
        
        # 等待恢复
        import time
        time.sleep(0.6)
        
        def success_func():
            return "ok"
        
        result = cb.call(success_func)
        assert result == "ok"
        assert cb.state == "closed"


class TestRateLimiter:
    """限流器测试"""
    
    def test_rate_limiter_allows(self):
        """限流器允许测试"""
        rl = RateLimiter(max_calls=5, period=1.0)
        
        # 应该允许 5 次
        for i in range(5):
            assert rl.acquire() is True
    
    def test_rate_limiter_blocks(self):
        """限流器阻止测试"""
        rl = RateLimiter(max_calls=2, period=1.0)
        
        rl.acquire()
        rl.acquire()
        
        # 第 3 次应该被阻止
        assert rl.acquire() is False


class TestJSONTool:
    """JSON 工具测试"""
    
    def setup_method(self):
        self.tool = JSONTool()
    
    def test_parse(self):
        """解析 JSON 测试"""
        result = self.tool.execute(
            operation="parse",
            data='{"name": "test", "value": 42}'
        )
        assert result.success is True
        assert result.output["name"] == "test"
    
    def test_stringify(self):
        """JSON 序列化测试"""
        result = self.tool.execute(
            operation="stringify",
            data={"name": "test"}
        )
        assert result.success is True
        assert "test" in result.output
    
    def test_get_nested(self):
        """获取嵌套值测试"""
        data = '{"user": {"name": "John", "address": {"city": "NYC"}}}'
        
        result = self.tool.execute(
            operation="get",
            data=data,
            path="user.address.city"
        )
        assert result.success is True
        assert result.output == "NYC"
    
    def test_validate(self):
        """验证 JSON 测试"""
        result = self.tool.execute(
            operation="validate",
            data='{"valid": true}'
        )
        assert result.success is True
        assert result.output["valid"] is True


class TestDateTimeTool:
    """日期时间工具测试"""
    
    def setup_method(self):
        self.tool = DateTimeTool()
    
    def test_now(self):
        """获取当前时间测试"""
        result = self.tool.execute(operation="now")
        assert result.success is True
        assert "T" in result.output  # ISO 格式
    
    def test_add_days(self):
        """添加天数测试"""
        result = self.tool.execute(
            operation="add",
            days=7
        )
        assert result.success is True
    
    def test_timestamp(self):
        """时间戳测试"""
        result = self.tool.execute(operation="timestamp")
        assert result.success is True
        assert isinstance(result.output, float)


class TestDatabaseTool:
    """数据库工具测试"""
    
    def setup_method(self):
        self.tool = DatabaseTool()
        self.temp_db = None
    
    def teardown_method(self):
        if self.temp_db and os.path.exists(self.temp_db):
            os.unlink(self.temp_db)
    
    def test_create_and_query(self):
        """创建和查询测试"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            self.temp_db = f.name
        
        # 创建表
        result = self.tool.execute(
            db_path=self.temp_db,
            query="CREATE TABLE test (id INTEGER, name TEXT)"
        )
        assert result.success is True
        
        # 插入数据
        result = self.tool.execute(
            db_path=self.temp_db,
            query="INSERT INTO test VALUES (?, ?)",
            params=(1, "test")
        )
        assert result.success is True
        
        # 查询
        result = self.tool.execute(
            db_path=self.temp_db,
            query="SELECT * FROM test",
            read_only=True
        )
        assert result.success is True
        assert len(result.output) == 1
    
    def test_read_only_protection(self):
        """只读保护测试"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            self.temp_db = f.name
        
        result = self.tool.execute(
            db_path=self.temp_db,
            query="DROP TABLE test",
            read_only=True
        )
        assert result.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
