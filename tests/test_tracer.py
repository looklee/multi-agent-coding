"""
执行日志模块测试
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tracer import (
    ExecutionLogger, EventType, TaskTrace, Event,
    get_logger, log_event
)


class TestEvent:
    """事件测试"""
    
    def test_event_creation(self):
        """事件创建测试"""
        event = Event(
            event_type=EventType.TASK_CREATED,
            task_id="test-001",
            data={"description": "test task"}
        )
        
        assert event.event_type == EventType.TASK_CREATED
        assert event.task_id == "test-001"
        assert event.id is not None
    
    def test_event_to_dict(self):
        """事件转字典测试"""
        event = Event(event_type=EventType.TASK_COMPLETED)
        d = event.to_dict()
        
        assert "id" in d
        assert "event_type" in d
        assert d["event_type"] == "task_completed"


class TestTaskTrace:
    """任务追溯测试"""
    
    def test_trace_creation(self):
        """追溯创建测试"""
        trace = TaskTrace(
            task_id="test-001",
            description="Test task"
        )
        
        assert trace.task_id == "test-001"
        assert trace.status == "pending"
        assert len(trace.events) == 0
    
    def test_add_event(self):
        """添加事件测试"""
        trace = TaskTrace(task_id="t1", description="test")
        event = Event(event_type=EventType.TASK_STARTED)
        trace.add_event(event)
        
        assert len(trace.events) == 1
    
    def test_get_decision_chain(self):
        """获取决策链测试"""
        trace = TaskTrace(task_id="t1", description="test")
        trace.add_event(Event(event_type=EventType.AGENT_SELECTED, agent_name="test"))
        trace.add_event(Event(event_type=EventType.TASK_COMPLETED))
        
        chain = trace.get_decision_chain()
        assert len(chain) == 1  # 只有 AGENT_SELECTED 在决策链中


class TestExecutionLogger:
    """执行日志记录器测试"""
    
    def setup_method(self):
        import tempfile
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.logger = ExecutionLogger(db_path=self.temp_db.name)
    
    def teardown_method(self):
        import os
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_create_trace(self):
        """创建追溯测试"""
        trace = self.logger.create_trace("t1", "Test task")
        assert trace.task_id == "t1"
    
    def test_log_event(self):
        """记录事件测试"""
        self.logger.create_trace("t1", "Test task")
        
        event = self.logger.log_event(
            "t1",
            EventType.TASK_STARTED,
            data={"step": 1}
        )
        
        assert event.event_type == EventType.TASK_STARTED
        assert event.task_id == "t1"
    
    def test_get_trace(self):
        """获取追溯测试"""
        self.logger.create_trace("t1", "Test task")
        self.logger.log_event("t1", EventType.TASK_STARTED)
        self.logger.log_event("t1", EventType.TASK_COMPLETED, data={"result": "done"})
        
        trace = self.logger.get_trace("t1")
        assert trace is not None
        assert trace.status == "completed"
    
    def test_get_recent_traces(self):
        """获取最近追溯测试"""
        for i in range(5):
            self.logger.create_trace(f"t{i}", f"Task {i}")
        
        traces = self.logger.get_recent_traces(limit=3)
        assert len(traces) <= 3
    
    def test_search_traces(self):
        """搜索追溯测试"""
        self.logger.create_trace("t1", "Python code generation")
        self.logger.create_trace("t2", "Java code review")
        
        results = self.logger.search_traces("Python")
        assert len(results) >= 1
    
    def test_get_statistics(self):
        """获取统计测试"""
        self.logger.create_trace("t1", "Task 1")
        self.logger.log_event("t1", EventType.TASK_STARTED)
        self.logger.log_event("t1", EventType.TASK_COMPLETED)
        
        stats = self.logger.get_statistics()
        assert stats["total_tasks"] >= 1
    
    def test_export_trace_json(self):
        """导出追溯 JSON 测试"""
        self.logger.create_trace("t1", "Test task")
        self.logger.log_event("t1", EventType.TASK_COMPLETED, data={"result": "ok"})
        
        content = self.logger.export_trace("t1", format="json")
        assert "Test task" in content
    
    def test_export_trace_markdown(self):
        """导出追溯 Markdown 测试"""
        self.logger.create_trace("t1", "Test task")
        
        content = self.logger.export_trace("t1", format="markdown")
        assert "# 任务追溯" in content


class TestGlobalLogger:
    """全局日志记录器测试"""
    
    def test_singleton(self):
        """单例测试"""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2
    
    def test_log_event_convenience(self):
        """便捷记录测试"""
        logger = get_logger()
        logger.create_trace("test-001", "Test")
        
        event = log_event("test-001", EventType.TASK_STARTED)
        assert event is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
