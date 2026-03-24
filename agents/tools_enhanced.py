"""
工具调用增强
- 重试机制
- 超时控制
- 结果验证
- 错误恢复
"""
import time
import random
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from functools import wraps
import threading


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential: bool = True
    jitter: bool = True


@dataclass
class TimeoutConfig:
    """超时配置"""
    seconds: float = 30.0
    raise_exception: bool = False


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RetryError(Exception):
    """重试失败异常"""
    def __init__(self, message: str, last_error: Exception = None, attempts: int = 0):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


class TimeoutError(Exception):
    """超时异常"""
    pass


def retry(config: RetryConfig = None):
    """重试装饰器"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    if attempt == config.max_attempts:
                        break
                    
                    # 计算延迟
                    if config.exponential:
                        delay = config.base_delay * (2 ** (attempt - 1))
                    else:
                        delay = config.base_delay
                    
                    delay = min(delay, config.max_delay)
                    
                    if config.jitter:
                        delay = delay * (0.5 + random.random())
                    
                    time.sleep(delay)
            
            raise RetryError(
                f"Failed after {config.max_attempts} attempts",
                last_error=last_error,
                attempts=config.max_attempts
            )
        
        return wrapper
    return decorator


def timeout(config: TimeoutConfig = None):
    """超时装饰器"""
    if config is None:
        config = TimeoutConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result_container = [None]
            exception_container = [None]
            
            def target():
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    exception_container[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=config.seconds)
            
            if thread.is_alive():
                if config.raise_exception:
                    raise TimeoutError(f"Function timed out after {config.seconds}s")
                return None
            
            if exception_container[0]:
                raise exception_container[0]
            
            return result_container[0]
        
        return wrapper
    return decorator


def validate_result(validator: Callable[[Any], ValidationResult]):
    """结果验证装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            validation = validator(result)
            
            if not validation.valid:
                errors = "; ".join(validation.errors)
                raise ValueError(f"Result validation failed: {errors}")
            
            return result
        return wrapper
    return decorator


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行调用"""
        with self._lock:
            if self.state == "open":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            
            with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failures = 0
            
            return result
        
        except Exception as e:
            with self._lock:
                self.failures += 1
                self.last_failure_time = time.time()
                
                if self.failures >= self.failure_threshold:
                    self.state = "open"
            
            raise e
    
    def reset(self):
        """重置熔断器"""
        with self._lock:
            self.failures = 0
            self.state = "closed"
            self.last_failure_time = None


class RateLimiter:
    """限流器"""
    
    def __init__(self, max_calls: int, period: float = 1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """获取许可"""
        with self._lock:
            now = time.time()
            
            # 移除过期的调用记录
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            return False
    
    def wait_and_acquire(self, timeout: float = None) -> bool:
        """等待并获取许可"""
        start = time.time()
        
        while True:
            if self.acquire():
                return True
            
            if timeout and (time.time() - start) > timeout:
                return False
            
            time.sleep(0.1)
    
    def __call__(self, func: Callable):
        """装饰器用法"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_and_acquire()
            return func(*args, **kwargs)
        return wrapper


class ToolExecutionContext:
    """工具执行上下文"""
    
    def __init__(self):
        self.retry_config = RetryConfig()
        self.timeout_config = TimeoutConfig()
        self.circuit_breaker: Optional[CircuitBreaker] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.metadata: Dict = {}
    
    def set_retry(self, max_attempts: int = 3, exponential: bool = True):
        """设置重试配置"""
        self.retry_config = RetryConfig(max_attempts=max_attempts, exponential=exponential)
        return self
    
    def set_timeout(self, seconds: float = 30.0):
        """设置超时"""
        self.timeout_config = TimeoutConfig(seconds=seconds)
        return self
    
    def enable_circuit_breaker(self, threshold: int = 5):
        """启用熔断器"""
        self.circuit_breaker = CircuitBreaker(failure_threshold=threshold)
        return self
    
    def enable_rate_limit(self, max_calls: int, period: float = 1.0):
        """启用限流"""
        self.rate_limiter = RateLimiter(max_calls=max_calls, period=period)
        return self


class EnhancedToolExecutor:
    """增强的工具执行器"""
    
    def __init__(self):
        self.contexts: Dict[str, ToolExecutionContext] = {}
        self.default_context = ToolExecutionContext()
    
    def register_context(self, tool_name: str, context: ToolExecutionContext):
        """注册工具上下文"""
        self.contexts[tool_name] = context
    
    def execute(self, tool_name: str, func: Callable, *args, **kwargs) -> Any:
        """执行工具"""
        context = self.contexts.get(tool_name, self.default_context)
        
        # 限流
        if context.rate_limiter:
            context.rate_limiter.wait_and_acquire()
        
        # 熔断器包装
        if context.circuit_breaker:
            original_func = func
            func = lambda *a, **kw: context.circuit_breaker.call(original_func, *a, **kw)
        
        # 重试包装
        func = retry(context.retry_config)(func)
        
        # 超时包装
        func = timeout(context.timeout_config)(func)
        
        return func(*args, **kwargs)


# 预定义验证器
def non_empty_result(result: Any) -> ValidationResult:
    """非空验证"""
    if result is None or result == "" or result == []:
        return ValidationResult(valid=False, errors=["Result is empty"])
    return ValidationResult(valid=True)


def type_validator(expected_type: type):
    """类型验证"""
    def validate(result: Any) -> ValidationResult:
        if not isinstance(result, expected_type):
            return ValidationResult(
                valid=False,
                errors=[f"Expected {expected_type}, got {type(result)}"]
            )
        return ValidationResult(valid=True)
    return validate


def range_validator(min_val: float = None, max_val: float = None):
    """范围验证"""
    def validate(result: Any) -> ValidationResult:
        errors = []
        
        if not isinstance(result, (int, float)):
            return ValidationResult(valid=False, errors=["Result is not a number"])
        
        if min_val is not None and result < min_val:
            errors.append(f"Result {result} is below minimum {min_val}")
        
        if max_val is not None and result > max_val:
            errors.append(f"Result {result} is above maximum {max_val}")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors)
    
    return validate


# 全局执行器
_executor = EnhancedToolExecutor()


def get_executor() -> EnhancedToolExecutor:
    """获取执行器"""
    return _executor


def configure_tool(tool_name: str, **kwargs) -> ToolExecutionContext:
    """配置工具"""
    context = ToolExecutionContext()
    
    if "retry_attempts" in kwargs:
        context.set_retry(max_attempts=kwargs["retry_attempts"])
    
    if "timeout" in kwargs:
        context.set_timeout(seconds=kwargs["timeout"])
    
    if "circuit_breaker" in kwargs:
        context.enable_circuit_breaker(kwargs["circuit_breaker"])
    
    if "rate_limit" in kwargs:
        context.enable_rate_limit(*kwargs["rate_limit"])
    
    _executor.register_context(tool_name, context)
    return context
