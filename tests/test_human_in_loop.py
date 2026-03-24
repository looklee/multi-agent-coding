"""
人机协作模块测试
"""
import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_in_loop import (
    HumanInLoop, ReviewStatus, ReviewRequest,
    FeedbackCollector, get_human_in_loop, get_feedback_collector
)


class TestHumanInLoop:
    """人机协作测试"""
    
    def setup_method(self):
        self.hil = HumanInLoop(timeout_seconds=5)
    
    def test_request_review(self):
        """请求审核测试"""
        review = self.hil.request_review(
            task_id="t1",
            content="Please review this code",
            reason="Security check"
        )
        
        assert review.task_id == "t1"
        assert review.status == ReviewStatus.PENDING
    
    def test_approve(self):
        """批准审核测试"""
        review = self.hil.request_review("t1", "content")
        
        result = self.hil.approve(review.id, reviewer="admin")
        assert result is True
        
        updated = self.hil.get_review(review.id)
        assert updated.status == ReviewStatus.APPROVED
    
    def test_reject(self):
        """拒绝审核测试"""
        review = self.hil.request_review("t1", "content")
        
        result = self.hil.reject(review.id, reviewer="admin", feedback="Needs improvement")
        assert result is True
        
        updated = self.hil.get_review(review.id)
        assert updated.status == ReviewStatus.REJECTED
        assert updated.feedback == "Needs improvement"
    
    def test_modify(self):
        """修改审核测试"""
        review = self.hil.request_review("t1", "original content")
        
        result = self.hil.modify(
            review.id,
            modified_content="modified content",
            reviewer="admin"
        )
        assert result is True
        
        updated = self.hil.get_review(review.id)
        assert updated.status == ReviewStatus.MODIFIED
        assert updated.modified_content == "modified content"
    
    def test_wait_for_review(self):
        """等待审核测试"""
        review = self.hil.request_review("t1", "content")
        
        # 异步批准
        import threading
        def approve_later():
            time.sleep(0.5)
            self.hil.approve(review.id)
        
        thread = threading.Thread(target=approve_later)
        thread.start()
        
        result = self.hil.wait_for_review(review.id, timeout=2)
        assert result.status == ReviewStatus.APPROVED
    
    def test_wait_timeout(self):
        """等待超时测试"""
        review = self.hil.request_review("t1", "content")
        
        # 不批准，等待超时
        result = self.hil.wait_for_review(review.id, timeout=1)
        assert result.status == ReviewStatus.TIMEOUT
    
    def test_get_pending_reviews(self):
        """获取待审核列表测试"""
        self.hil.request_review("t1", "content1")
        self.hil.request_review("t2", "content2")
        self.hil.request_review("t3", "content3")
        self.hil.approve(self.hil.get_review("t2").id)
        
        pending = self.hil.get_pending_reviews()
        assert len(pending) == 2
    
    def test_cleanup_expired(self):
        """清理过期审核测试"""
        # 创建一个很快就过期的审核
        old_hil = HumanInLoop(timeout_seconds=0.1)
        review = old_hil.request_review("t1", "content")
        
        time.sleep(0.2)
        old_hil.cleanup_expired()
        
        updated = old_hil.get_review(review.id)
        assert updated.status == ReviewStatus.TIMEOUT


class TestFeedbackCollector:
    """反馈收集器测试"""
    
    def setup_method(self):
        self.collector = FeedbackCollector()
    
    def test_add_feedback(self):
        """添加反馈测试"""
        entry = self.collector.add_feedback(
            task_id="t1",
            content="Great job!",
            rating=5
        )
        
        assert entry.task_id == "t1"
        assert entry.rating == 5
    
    def test_get_feedback(self):
        """获取反馈测试"""
        self.collector.add_feedback("t1", "good", rating=4)
        self.collector.add_feedback("t1", "excellent", rating=5)
        
        feedbacks = self.collector.get_feedback("t1")
        assert len(feedbacks) == 2
    
    def test_get_agent_feedback(self):
        """获取 Agent 反馈测试"""
        self.collector.add_feedback("t1", "good", agent_name="agent1", rating=4)
        self.collector.add_feedback("t2", "bad", agent_name="agent1", rating=2)
        self.collector.add_feedback("t3", "ok", agent_name="agent2", rating=3)
        
        feedbacks = self.collector.get_agent_feedback("agent1")
        assert len(feedbacks) == 2
    
    def test_get_statistics(self):
        """获取统计测试"""
        self.collector.add_feedback("t1", "", rating=5)
        self.collector.add_feedback("t2", "", rating=4)
        self.collector.add_feedback("t3", "", rating=3)
        
        stats = self.collector.get_statistics()
        assert stats["total"] == 3
        assert stats["avg_rating"] == 4.0


class TestGlobalInstances:
    """全局实例测试"""
    
    def test_hil_singleton(self):
        """人机协作单例测试"""
        hil1 = get_human_in_loop()
        hil2 = get_human_in_loop()
        assert hil1 is hil2
    
    def test_feedback_singleton(self):
        """反馈收集器单例测试"""
        fc1 = get_feedback_collector()
        fc2 = get_feedback_collector()
        assert fc1 is fc2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
