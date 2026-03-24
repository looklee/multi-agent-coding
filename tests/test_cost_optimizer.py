"""
成本优化模块测试
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cost_optimizer import (
    TokenCache, SmartRouter, CostTracker, BatchProcessor,
    get_cache, get_cost_tracker, get_router
)


class TestTokenCache:
    """Token 缓存测试"""
    
    def setup_method(self):
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.cache = TokenCache(db_path=self.temp_db.name, ttl_seconds=3600)
    
    def teardown_method(self):
        import os
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_cache_set_get(self):
        """缓存设置和获取测试"""
        self.cache.set("test prompt", "test response", 10, 20)
        
        result = self.cache.get("test prompt")
        assert result is not None
        assert result.content == "test response"
        assert result.input_tokens == 10
        assert result.output_tokens == 20
    
    def test_cache_miss(self):
        """缓存未命中测试"""
        result = self.cache.get("nonexistent prompt")
        assert result is None
    
    def test_cache_hit_count(self):
        """缓存命中计数测试"""
        self.cache.set("prompt", "response", 5, 5)
        
        self.cache.get("prompt")
        self.cache.get("prompt")
        
        result = self.cache.get("prompt")
        assert result.hit_count >= 2
    
    def test_stats(self):
        """统计信息测试"""
        self.cache.set("p1", "r1", 10, 10)
        self.cache.set("p2", "r2", 20, 20)
        self.cache.get("p1")
        
        stats = self.cache.get_stats()
        assert stats["cache_size"] >= 2
        assert stats["total_hits"] >= 1


class TestSmartRouter:
    """智能路由测试"""
    
    def setup_method(self):
        self.router = SmartRouter()
    
    def test_estimate_complexity_simple(self):
        """简单任务复杂度评估"""
        score, model_type = self.router.estimate_complexity("什么是 Python？")
        assert score <= 4
        assert model_type == "cheap"
    
    def test_estimate_complexity_medium(self):
        """中等任务复杂度评估"""
        score, model_type = self.router.estimate_complexity("实现一个快速排序")
        assert 4 <= score <= 7
    
    def test_estimate_complexity_hard(self):
        """复杂任务复杂度评估"""
        score, model_type = self.router.estimate_complexity(
            "设计一个高并发分布式系统架构"
        )
        assert score >= 7
        assert model_type == "powerful"
    
    def test_select_model_budget_mode(self):
        """预算模式选择模型测试"""
        provider, model = self.router.select_model(
            "简单任务", 
            budget_mode=True
        )
        # 应该选择较便宜的模型
        assert provider is not None
    
    def test_get_price(self):
        """获取价格测试"""
        input_price, output_price = self.router.get_price("qwen", "qwen-plus")
        assert input_price > 0
        assert output_price > 0


class TestCostTracker:
    """成本追踪器测试"""
    
    def setup_method(self):
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.tracker = CostTracker(db_path=self.temp_db.name)
    
    def teardown_method(self):
        import os
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_record_cost(self):
        """记录成本测试"""
        self.tracker.record(
            provider="qwen",
            model="qwen-plus",
            input_tokens=100,
            output_tokens=50,
            task_id="test-001"
        )
        
        total = self.tracker.get_total_cost()
        assert total > 0
    
    def test_get_stats(self):
        """获取统计测试"""
        self.tracker.record("qwen", "qwen-plus", 100, 50, "t1")
        self.tracker.record("deepseek", "deepseek-chat", 200, 100, "t2")
        
        stats = self.tracker.get_stats()
        assert stats["total_cost"] > 0
        assert stats["total_tokens"] > 0
        assert "qwen" in stats["by_provider"]


class TestBatchProcessor:
    """批量处理器测试"""
    
    def setup_method(self):
        self.processor = BatchProcessor(max_batch_size=3)
        self.results = []
    
    def test_batch_accumulation(self):
        """批量累积测试"""
        def callback(combined, task_ids):
            self.results.append((combined, task_ids))
        
        self.processor.add("t1", "task 1", callback)
        self.processor.add("t2", "task 2", callback)
        # 还没达到批量大小
        assert len(self.results) == 0
        
        self.processor.add("t3", "task 3", callback)
        # 达到批量大小，应该触发处理
        assert len(self.results) >= 1


class TestGlobalInstances:
    """全局实例测试"""
    
    def test_cache_singleton(self):
        """缓存单例测试"""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
    
    def test_router_singleton(self):
        """路由单例测试"""
        router1 = get_router()
        router2 = get_router()
        assert router1 is router2
    
    def test_cost_tracker_singleton(self):
        """成本追踪器单例测试"""
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()
        assert tracker1 is tracker2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
