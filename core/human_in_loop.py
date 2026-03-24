"""
人机协作模块
- 人工审核节点
- 实时反馈
- 中断和恢复
"""
import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue


class ReviewStatus(Enum):
    """审核状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"


@dataclass
class ReviewRequest:
    """审核请求"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    agent_name: str = ""
    content: str = ""
    reason: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: float = field(default_factory=time.time)
    reviewed_at: Optional[float] = None
    reviewer: str = ""
    feedback: str = ""
    modified_content: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reviewer": self.reviewer,
            "feedback": self.feedback,
            "modified_content": self.modified_content
        }


class HumanInLoop:
    """人机协作控制器"""
    
    def __init__(self, timeout_seconds: float = 300):
        self.timeout_seconds = timeout_seconds
        self._pending_reviews: Dict[str, ReviewRequest] = {}
        self._lock = threading.Lock()
        self._review_queue: queue.Queue = queue.Queue()
        self._callbacks: Dict[str, Callable] = {}
        self._auto_approve_patterns: List[str] = []
    
    def request_review(self, task_id: str, content: str, 
                       agent_name: str = "", reason: str = "") -> ReviewRequest:
        """请求人工审核"""
        review = ReviewRequest(
            task_id=task_id,
            content=content,
            agent_name=agent_name,
            reason=reason
        )
        
        with self._lock:
            self._pending_reviews[review.id] = review
        
        self._review_queue.put(review)
        
        # 触发回调
        for callback in self._callbacks.values():
            try:
                callback(review)
            except Exception:
                pass
        
        return review
    
    def approve(self, review_id: str, reviewer: str = "", 
                feedback: str = "") -> bool:
        """批准审核"""
        with self._lock:
            if review_id not in self._pending_reviews:
                return False
            
            review = self._pending_reviews[review_id]
            review.status = ReviewStatus.APPROVED
            review.reviewed_at = time.time()
            review.reviewer = reviewer
            review.feedback = feedback
        
        return True
    
    def reject(self, review_id: str, reviewer: str = "", 
               feedback: str = "") -> bool:
        """拒绝审核"""
        with self._lock:
            if review_id not in self._pending_reviews:
                return False
            
            review = self._pending_reviews[review_id]
            review.status = ReviewStatus.REJECTED
            review.reviewed_at = time.time()
            review.reviewer = reviewer
            review.feedback = feedback
        
        return True
    
    def modify(self, review_id: str, modified_content: str,
               reviewer: str = "", feedback: str = "") -> bool:
        """修改后批准"""
        with self._lock:
            if review_id not in self._pending_reviews:
                return False
            
            review = self._pending_reviews[review_id]
            review.status = ReviewStatus.MODIFIED
            review.reviewed_at = time.time()
            review.reviewer = reviewer
            review.feedback = feedback
            review.modified_content = modified_content
        
        return True
    
    def wait_for_review(self, review_id: str, 
                        timeout: float = None) -> ReviewRequest:
        """等待审核完成"""
        timeout = timeout or self.timeout_seconds
        start_time = time.time()
        
        while True:
            with self._lock:
                if review_id not in self._pending_reviews:
                    raise ValueError(f"Review {review_id} not found")
                
                review = self._pending_reviews[review_id]
                
                if review.status != ReviewStatus.PENDING:
                    return review
            
            # 检查超时
            if time.time() - start_time > timeout:
                with self._lock:
                    if review_id in self._pending_reviews:
                        review = self._pending_reviews[review_id]
                        review.status = ReviewStatus.TIMEOUT
                        review.reviewed_at = time.time()
                return review
            
            time.sleep(0.5)
    
    async def wait_for_review_async(self, review_id: str,
                                    timeout: float = None) -> ReviewRequest:
        """异步等待审核"""
        timeout = timeout or self.timeout_seconds
        start_time = time.time()
        
        while True:
            with self._lock:
                if review_id not in self._pending_reviews:
                    raise ValueError(f"Review {review_id} not found")
                
                review = self._pending_reviews[review_id]
                
                if review.status != ReviewStatus.PENDING:
                    return review
            
            if time.time() - start_time > timeout:
                with self._lock:
                    if review_id in self._pending_reviews:
                        review = self._pending_reviews[review_id]
                        review.status = ReviewStatus.TIMEOUT
                        review.reviewed_at = time.time()
                return review
            
            await asyncio.sleep(0.5)
    
    def get_pending_reviews(self) -> List[ReviewRequest]:
        """获取待审核列表"""
        with self._lock:
            return [
                r for r in self._pending_reviews.values() 
                if r.status == ReviewStatus.PENDING
            ]
    
    def get_review(self, review_id: str) -> Optional[ReviewRequest]:
        """获取审核请求"""
        with self._lock:
            return self._pending_reviews.get(review_id)
    
    def register_callback(self, callback_id: str, callback: Callable):
        """注册审核回调"""
        self._callbacks[callback_id] = callback
    
    def unregister_callback(self, callback_id: str):
        """注销回调"""
        if callback_id in self._callbacks:
            del self._callbacks[callback_id]
    
    def set_auto_approve_patterns(self, patterns: List[str]):
        """设置自动批准模式（用于测试或低风险任务）"""
        self._auto_approve_patterns = patterns
    
    def cleanup_expired(self):
        """清理过期审核"""
        cutoff = time.time() - self.timeout_seconds
        with self._lock:
            for review in self._pending_reviews.values():
                if review.status == ReviewStatus.PENDING and review.created_at < cutoff:
                    review.status = ReviewStatus.TIMEOUT
                    review.reviewed_at = time.time()


@dataclass
class FeedbackEntry:
    """反馈条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = ""
    agent_name: str = ""
    content: str = ""
    rating: int = 0  # 1-5
    created_at: float = field(default_factory=time.time)


class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self):
        self._feedbacks: List[FeedbackEntry] = []
        self._lock = threading.Lock()
    
    def add_feedback(self, task_id: str, content: str, 
                     agent_name: str = "", rating: int = 0) -> FeedbackEntry:
        """添加反馈"""
        entry = FeedbackEntry(
            task_id=task_id,
            content=content,
            agent_name=agent_name,
            rating=rating
        )
        
        with self._lock:
            self._feedbacks.append(entry)
        
        return entry
    
    def get_feedback(self, task_id: str) -> List[FeedbackEntry]:
        """获取任务的反馈"""
        with self._lock:
            return [f for f in self._feedbacks if f.task_id == task_id]
    
    def get_agent_feedback(self, agent_name: str) -> List[FeedbackEntry]:
        """获取 Agent 的反馈"""
        with self._lock:
            return [f for f in self._feedbacks if f.agent_name == agent_name]
    
    def get_statistics(self) -> Dict:
        """获取反馈统计"""
        with self._lock:
            total = len(self._feedbacks)
            if total == 0:
                return {"total": 0, "avg_rating": 0, "by_rating": {}}
            
            ratings = [f.rating for f in self._feedbacks if f.rating > 0]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            by_rating = {}
            for i in range(1, 6):
                by_rating[i] = sum(1 for f in self._feedbacks if f.rating == i)
            
            return {
                "total": total,
                "avg_rating": avg_rating,
                "by_rating": by_rating
            }


class InterruptibleTask:
    """可中断任务包装器"""
    
    def __init__(self, task_func: Callable, human_in_loop: HumanInLoop):
        self.task_func = task_func
        self.human_in_loop = human_in_loop
        self._interrupted = False
        self._checkpoint_data: Dict = {}
    
    def set_checkpoint(self, checkpoint_id: str, data: Dict):
        """设置检查点"""
        self._checkpoint_data[checkpoint_id] = data
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict]:
        """获取检查点数据"""
        return self._checkpoint_data.get(checkpoint_id)
    
    def interrupt(self):
        """中断任务"""
        self._interrupted = True
    
    def is_interrupted(self) -> bool:
        """检查是否被中断"""
        return self._interrupted
    
    def execute_with_reviews(self, *args, review_points: List[str] = None, **kwargs):
        """执行任务，在指定点请求审核"""
        review_points = review_points or []
        results = []
        
        for i, step in enumerate(review_points):
            if self._interrupted:
                raise InterruptedError("Task was interrupted")
            
            # 执行步骤
            result = self.task_func(*args, step=step, **kwargs)
            results.append(result)
            
            # 请求审核
            review = self.human_in_loop.request_review(
                task_id=f"step_{i}",
                content=str(result),
                reason=f"步骤 {i}: {step}"
            )
            
            reviewed = self.human_in_loop.wait_for_review(review.id)
            
            if reviewed.status == ReviewStatus.REJECTED:
                raise PermissionError(f"Step {i} rejected: {reviewed.feedback}")
            elif reviewed.status == ReviewStatus.MODIFIED:
                results[-1] = reviewed.modified_content
        
        return results


# 全局实例
_human_in_loop: Optional[HumanInLoop] = None
_feedback_collector: Optional[FeedbackCollector] = None


def get_human_in_loop() -> HumanInLoop:
    global _human_in_loop
    if _human_in_loop is None:
        _human_in_loop = HumanInLoop()
    return _human_in_loop


def get_feedback_collector() -> FeedbackCollector:
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector


def request_review(task_id: str, content: str, 
                   reason: str = "") -> ReviewRequest:
    """便捷请求审核"""
    return get_human_in_loop().request_review(task_id, content, reason=reason)


def add_feedback(task_id: str, content: str, 
                 rating: int = 0) -> FeedbackEntry:
    """便捷添加反馈"""
    return get_feedback_collector().add_feedback(task_id, content, rating=rating)
