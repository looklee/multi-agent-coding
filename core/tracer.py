"""
执行日志和追溯模块
- 完整执行日志
- 决策链记录
- 可追溯的任务历史
"""
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import sqlite3
from threading import Lock


class EventType(Enum):
    """事件类型"""
    TASK_CREATED = "task_created"
    TASK_DECOMPOSED = "task_decomposed"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_SELECTED = "agent_selected"
    LLM_CALL = "llm_call"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    HUMAN_REVIEW = "human_review"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"
    COST_RECORDED = "cost_recorded"


@dataclass
class Event:
    """执行事件"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.TASK_CREATED
    task_id: str = ""
    agent_name: str = ""
    timestamp: float = field(default_factory=time.time)
    data: Dict = field(default_factory=dict)
    parent_event_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "data": self.data,
            "parent_event_id": self.parent_event_id
        }


@dataclass
class TaskTrace:
    """任务追溯记录"""
    task_id: str
    description: str
    status: str = "pending"
    events: List[Event] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: str = ""
    error: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def add_event(self, event: Event):
        event.task_id = self.task_id
        self.events.append(event)
    
    def get_decision_chain(self) -> List[Dict]:
        """获取决策链"""
        chain = []
        for event in self.events:
            if event.event_type in [
                EventType.AGENT_SELECTED,
                EventType.TASK_DECOMPOSED,
                EventType.HUMAN_REVIEW,
                EventType.LLM_CALL
            ]:
                chain.append(event.to_dict())
        return chain
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "decision_chain": self.get_decision_chain(),
            "metadata": self.metadata
        }


class ExecutionLogger:
    """执行日志记录器"""
    
    def __init__(self, db_path: str = "execution_logs.db"):
        self.db_path = db_path
        self._lock = Lock()
        self._traces: Dict[str, TaskTrace] = {}
        self._in_memory_limit = 100  # 内存中保留的追溯记录数
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    task_id TEXT PRIMARY KEY,
                    description TEXT,
                    status TEXT,
                    created_at REAL,
                    completed_at REAL,
                    result TEXT,
                    error TEXT,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    task_id TEXT,
                    agent_name TEXT,
                    timestamp REAL,
                    data TEXT,
                    parent_event_id TEXT,
                    FOREIGN KEY (task_id) REFERENCES traces(task_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_created ON traces(created_at)")
    
    def create_trace(self, task_id: str, description: str, metadata: Dict = None) -> TaskTrace:
        """创建任务追溯记录"""
        trace = TaskTrace(
            task_id=task_id,
            description=description,
            metadata=metadata or {}
        )
        self._traces[task_id] = trace
        return trace
    
    def get_trace(self, task_id: str) -> Optional[TaskTrace]:
        """获取任务追溯记录"""
        # 先在内存中查找
        if task_id in self._traces:
            return self._traces[task_id]
        
        # 从数据库加载
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM traces WHERE task_id = ?", (task_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                trace = TaskTrace(
                    task_id=row[0],
                    description=row[1],
                    status=row[2],
                    created_at=row[3],
                    completed_at=row[4],
                    result=row[5],
                    error=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                )
                
                # 加载事件
                cursor = conn.execute(
                    "SELECT * FROM events WHERE task_id = ? ORDER BY timestamp",
                    (task_id,)
                )
                for event_row in cursor.fetchall():
                    event = Event(
                        id=event_row[0],
                        event_type=EventType(event_row[1]),
                        task_id=event_row[2],
                        agent_name=event_row[3],
                        timestamp=event_row[4],
                        data=json.loads(event_row[5]) if event_row[5] else {},
                        parent_event_id=event_row[6]
                    )
                    trace.events.append(event)
                
                return trace
    
    def log_event(self, task_id: str, event_type: EventType, 
                  data: Dict = None, agent_name: str = "", 
                  parent_event_id: str = "") -> Event:
        """记录事件"""
        event = Event(
            event_type=event_type,
            task_id=task_id,
            agent_name=agent_name,
            data=data or {},
            parent_event_id=parent_event_id
        )
        
        # 获取或创建追溯
        trace = self._traces.get(task_id)
        if not trace:
            trace = self.create_trace(task_id, "")
        
        trace.add_event(event)
        
        # 更新状态
        if event_type == EventType.TASK_STARTED:
            trace.status = "running"
        elif event_type == EventType.TASK_COMPLETED:
            trace.status = "completed"
            trace.completed_at = time.time()
            trace.result = data.get("result", "") if data else ""
        elif event_type == EventType.TASK_FAILED:
            trace.status = "failed"
            trace.completed_at = time.time()
            trace.error = data.get("error", "") if data else ""
        
        # 持久化
        self._persist_trace(trace)
        
        return event
    
    def _persist_trace(self, trace: TaskTrace):
        """持久化追溯记录"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 保存追溯
                conn.execute("""
                    INSERT OR REPLACE INTO traces 
                    (task_id, description, status, created_at, completed_at, result, error, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trace.task_id,
                    trace.description,
                    trace.status,
                    trace.created_at,
                    trace.completed_at,
                    trace.result,
                    trace.error,
                    json.dumps(trace.metadata)
                ))
                
                # 保存新事件
                for event in trace.events:
                    conn.execute("""
                        INSERT OR IGNORE INTO events 
                        (id, event_type, task_id, agent_name, timestamp, data, parent_event_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.id,
                        event.event_type.value,
                        event.task_id,
                        event.agent_name,
                        event.timestamp,
                        json.dumps(event.data),
                        event.parent_event_id
                    ))
        
        # 清理内存
        if len(self._traces) > self._in_memory_limit:
            oldest_id = min(self._traces.keys(), 
                          key=lambda k: self._traces[k].created_at)
            del self._traces[oldest_id]
    
    def get_recent_traces(self, limit: int = 20) -> List[TaskTrace]:
        """获取最近的追溯记录"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT task_id FROM traces ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                task_ids = [row[0] for row in cursor.fetchall()]
        
        return [self.get_trace(tid) for tid in task_ids if self.get_trace(tid)]
    
    def search_traces(self, keyword: str, limit: int = 20) -> List[TaskTrace]:
        """搜索追溯记录"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT task_id FROM traces WHERE description LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{keyword}%", limit)
                )
                task_ids = [row[0] for row in cursor.fetchall()]
        
        return [self.get_trace(tid) for tid in task_ids if self.get_trace(tid)]
    
    def get_statistics(self, days: int = 7) -> Dict:
        """获取统计信息"""
        cutoff = time.time() - (days * 24 * 3600)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 总任务数
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM traces WHERE created_at > ?", (cutoff,)
                )
                total = cursor.fetchone()[0]
                
                # 按状态分组
                cursor = conn.execute(
                    "SELECT status, COUNT(*) FROM traces WHERE created_at > ? GROUP BY status",
                    (cutoff,)
                )
                by_status = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 事件统计
                cursor = conn.execute(
                    "SELECT event_type, COUNT(*) FROM events WHERE timestamp > ? GROUP BY event_type",
                    (cutoff,)
                )
                by_event = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 平均完成时间
                cursor = conn.execute(
                    """SELECT AVG(completed_at - created_at) FROM traces 
                       WHERE completed_at IS NOT NULL AND created_at > ?""",
                    (cutoff,)
                )
                avg_duration = cursor.fetchone()[0] or 0
                
                return {
                    "total_tasks": total,
                    "by_status": by_status,
                    "by_event_type": by_event,
                    "avg_duration_seconds": avg_duration,
                    "period_days": days
                }
    
    def export_trace(self, task_id: str, format: str = "json") -> str:
        """导出追溯记录"""
        trace = self.get_trace(task_id)
        if not trace:
            return ""
        
        if format == "json":
            return json.dumps(trace.to_dict(), indent=2, ensure_ascii=False)
        elif format == "markdown":
            return self._to_markdown(trace)
        else:
            return json.dumps(trace.to_dict(), indent=2, ensure_ascii=False)
    
    def _to_markdown(self, trace: TaskTrace) -> str:
        """转换为 Markdown 格式"""
        lines = [
            f"# 任务追溯：{trace.task_id}",
            f"",
            f"**描述**: {trace.description}",
            f"**状态**: {trace.status}",
            f"**创建时间**: {datetime.fromtimestamp(trace.created_at).isoformat()}",
        ]
        
        if trace.completed_at:
            lines.append(f"**完成时间**: {datetime.fromtimestamp(trace.completed_at).isoformat()}")
        
        if trace.result:
            lines.extend(["", "## 结果", "", trace.result])
        
        if trace.error:
            lines.extend(["", "## 错误", "", trace.error])
        
        lines.extend(["", "## 决策链", ""])
        
        for event in trace.get_decision_chain():
            icon = {
                EventType.AGENT_SELECTED: "🤖",
                EventType.TASK_DECOMPOSED: "📋",
                EventType.HUMAN_REVIEW: "👤",
                EventType.LLM_CALL: "💬"
            }.get(EventType(event["event_type"]), "•")
            
            lines.append(f"{icon} **{event['event_type']}** - {datetime.fromtimestamp(event['timestamp']).isoformat()}")
            if event.get("agent_name"):
                lines.append(f"   Agent: {event['agent_name']}")
            if event.get("data"):
                lines.append(f"   详情：{json.dumps(event['data'], ensure_ascii=False)[:200]}")
            lines.append("")
        
        return "\n".join(lines)


# 全局实例
_logger: Optional[ExecutionLogger] = None


def get_logger() -> ExecutionLogger:
    global _logger
    if _logger is None:
        _logger = ExecutionLogger()
    return _logger


def log_event(task_id: str, event_type: EventType, 
              data: Dict = None, agent_name: str = "") -> Event:
    """便捷记录事件"""
    return get_logger().log_event(task_id, event_type, data, agent_name)
