"""
多 Agent 协作增强
- 消息传递
- 协商机制
- 共识达成
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from collections import defaultdict
import threading
import queue


class MessageType(Enum):
    """消息类型"""
    TASK = "task"
    REQUEST = "request"
    RESPONSE = "response"
    PROPOSAL = "proposal"
    VOTE = "vote"
    BROADCAST = "broadcast"
    ACK = "ack"


@dataclass
class Message:
    """消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    msg_type: MessageType = MessageType.TASK
    sender: str = ""
    receiver: str = ""
    content: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    reply_to: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.msg_type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to
        }


class MessageBus:
    """消息总线"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._message_queue: queue.Queue = queue.Queue()
        self._message_history: List[Message] = []
        self._lock = threading.Lock()
        self._running = False
        self._workers: List[threading.Thread] = []
    
    def subscribe(self, topic: str, callback: Callable):
        """订阅主题"""
        with self._lock:
            self._subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable):
        """取消订阅"""
        with self._lock:
            if callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)
    
    def publish(self, message: Message):
        """发布消息"""
        with self._lock:
            self._message_history.append(message)
            
            # 放入队列
            self._message_queue.put(message)
            
            # 通知订阅者
            topic = message.msg_type.value
            for callback in self._subscribers.get(topic, []):
                try:
                    callback(message)
                except Exception:
                    pass
    
    def send(self, sender: str, receiver: str, content: Any, 
             msg_type: MessageType = MessageType.TASK) -> Message:
        """发送消息"""
        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            msg_type=msg_type
        )
        self.publish(message)
        return message
    
    def get_history(self, limit: int = 100) -> List[Message]:
        """获取消息历史"""
        return self._message_history[-limit:]
    
    def start(self):
        """启动消息处理"""
        self._running = True
    
    def stop(self):
        """停止"""
        self._running = False


class NegotiationProtocol:
    """协商协议"""
    
    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
        self._proposals: Dict[str, Dict] = {}
        self._votes: Dict[str, Dict[str, bool]] = defaultdict(dict)
    
    def propose(self, proposer: str, agents: List[str], 
                proposal: Any, context: str = "") -> str:
        """提出建议"""
        proposal_id = str(uuid.uuid4())[:8]
        
        self._proposals[proposal_id] = {
            "proposer": proposer,
            "agents": agents,
            "proposal": proposal,
            "context": context,
            "votes": {},
            "status": "pending"
        }
        
        # 发送给所有参与 Agent
        for agent in agents:
            self.bus.send(
                sender=proposer,
                receiver=agent,
                content={
                    "proposal_id": proposal_id,
                    "proposal": proposal,
                    "context": context
                },
                msg_type=MessageType.PROPOSAL
            )
        
        return proposal_id
    
    def vote(self, proposal_id: str, voter: str, approve: bool, 
             reason: str = ""):
        """投票"""
        if proposal_id not in self._proposals:
            return
        
        self._votes[proposal_id][voter] = approve
        
        proposal = self._proposals[proposal_id]
        total_agents = len(proposal["agents"])
        votes_received = len(self._votes[proposal_id])
        approvals = sum(1 for v in self._votes[proposal_id].values() if v)
        
        # 检查是否达成多数
        if votes_received == total_agents:
            if approvals > total_agents / 2:
                proposal["status"] = "accepted"
            else:
                proposal["status"] = "rejected"
    
    def get_proposal_status(self, proposal_id: str) -> Optional[Dict]:
        """获取建议状态"""
        return self._proposals.get(proposal_id)
    
    def wait_for_consensus(self, proposal_id: str, 
                           timeout: float = 30) -> bool:
        """等待共识"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_proposal_status(proposal_id)
            if status and status["status"] != "pending":
                return status["status"] == "accepted"
            time.sleep(0.5)
        
        return False


class AgentBlackboard:
    """黑板系统 - 共享工作空间"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._global_lock = threading.Lock()
        self._observers: Dict[str, List[Callable]] = defaultdict(list)
        self._version: int = 0
    
    def write(self, key: str, value: Any, agent: str = ""):
        """写入数据"""
        with self._global_lock:
            self._data[key] = {
                "value": value,
                "writer": agent,
                "timestamp": time.time(),
                "version": self._version
            }
            self._version += 1
            
            # 通知观察者
            for callback in self._observers.get(key, []):
                try:
                    callback(key, value, agent)
                except Exception:
                    pass
    
    def read(self, key: str, default: Any = None) -> Any:
        """读取数据"""
        entry = self._data.get(key)
        return entry["value"] if entry else default
    
    def delete(self, key: str):
        """删除数据"""
        with self._global_lock:
            if key in self._data:
                del self._data[key]
    
    def subscribe(self, key: str, callback: Callable):
        """订阅数据变化"""
        self._observers[key].append(callback)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有数据"""
        return {k: v["value"] for k, v in self._data.items()}
    
    def get_version(self) -> int:
        """获取当前版本"""
        return self._version


class CollaborativeTask:
    """协作任务"""
    
    def __init__(self, task_id: str, description: str, 
                 participating_agents: List[str]):
        self.task_id = task_id
        self.description = description
        self.agents = participating_agents
        self.status = "pending"
        self.subtasks: Dict[str, Dict] = {}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.results: Dict[str, Any] = {}
        self.messages: List[Message] = []
    
    def add_subtask(self, subtask_id: str, description: str, 
                    assigned_agent: str, dependencies: List[str] = None):
        """添加子任务"""
        self.subtasks[subtask_id] = {
            "description": description,
            "assigned_agent": assigned_agent,
            "status": "pending",
            "result": None
        }
        
        if dependencies:
            self.dependencies[subtask_id] = set(dependencies)
    
    def complete_subtask(self, subtask_id: str, result: Any):
        """完成子任务"""
        if subtask_id in self.subtasks:
            self.subtasks[subtask_id]["status"] = "completed"
            self.subtasks[subtask_id]["result"] = result
            self.results[subtask_id] = result
    
    def is_ready(self, subtask_id: str) -> bool:
        """检查子任务是否就绪（依赖已完成）"""
        deps = self.dependencies.get(subtask_id, set())
        return all(
            self.subtasks.get(d, {}).get("status") == "completed"
            for d in deps
        )
    
    def is_complete(self) -> bool:
        """检查所有子任务是否完成"""
        return all(
            t["status"] == "completed" 
            for t in self.subtasks.values()
        )
    
    def get_status(self) -> Dict:
        """获取任务状态"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "status": self.status,
            "total_subtasks": len(self.subtasks),
            "completed_subtasks": sum(1 for t in self.subtasks.values() 
                                      if t["status"] == "completed"),
            "results": self.results
        }


class AgentTeam:
    """Agent 团队"""
    
    def __init__(self):
        self.members: Dict[str, Any] = {}  # agent_name -> agent_instance
        self.message_bus = MessageBus()
        self.blackboard = AgentBlackboard()
        self.negotiation = NegotiationProtocol(self.message_bus)
        self._active_tasks: Dict[str, CollaborativeTask] = {}
    
    def add_member(self, name: str, agent: Any):
        """添加成员"""
        self.members[name] = agent
        
        # 订阅消息
        self.message_bus.subscribe(
            MessageType.TASK.value,
            lambda msg: self._handle_task(msg, name)
        )
    
    def remove_member(self, name: str):
        """移除成员"""
        if name in self.members:
            del self.members[name]
    
    def create_task(self, description: str, 
                    participating_agents: List[str] = None) -> CollaborativeTask:
        """创建协作任务"""
        task_id = str(uuid.uuid4())[:8]
        
        if participating_agents is None:
            participating_agents = list(self.members.keys())
        
        task = CollaborativeTask(task_id, description, participating_agents)
        self._active_tasks[task_id] = task
        
        return task
    
    def _handle_task(self, message: Message, agent_name: str):
        """处理任务消息"""
        if message.receiver and message.receiver != agent_name:
            return
        
        # Agent 处理任务逻辑
        agent = self.members.get(agent_name)
        if agent and hasattr(agent, 'handle_message'):
            agent.handle_message(message)
    
    async def execute_collaborative(self, task: CollaborativeTask) -> Dict:
        """执行协作任务"""
        # 分配子任务
        for subtask_id, subtask in task.subtasks.items():
            agent_name = subtask["assigned_agent"]
            agent = self.members.get(agent_name)
            
            if agent:
                # 等待依赖
                while not task.is_ready(subtask_id):
                    await asyncio.sleep(0.1)
                
                # 执行子任务
                if hasattr(agent, 'execute_sync'):
                    result = agent.execute_sync(subtask["description"])
                    task.complete_subtask(subtask_id, result)
                    
                    # 写入黑板
                    self.blackboard.write(
                        f"result_{subtask_id}",
                        result,
                        agent_name
                    )
        
        # 等待所有完成
        while not task.is_complete():
            await asyncio.sleep(0.1)
        
        return task.get_status()
    
    def get_team_status(self) -> Dict:
        """获取团队状态"""
        return {
            "members": list(self.members.keys()),
            "active_tasks": len(self._active_tasks),
            "blackboard_items": len(self.blackboard.get_all()),
            "message_count": len(self.message_bus.get_history())
        }


# 全局实例
_teams: Dict[str, AgentTeam] = {}


def create_team(team_id: str) -> AgentTeam:
    """创建团队"""
    team = AgentTeam()
    _teams[team_id] = team
    return team


def get_team(team_id: str) -> Optional[AgentTeam]:
    """获取团队"""
    return _teams.get(team_id)
