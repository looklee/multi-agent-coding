"""
任务调度与协作核心
"""
import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from agents.base import BaseAgent
from api.llm import LLMClient, Message


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务对象"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str = None
    result: str = None
    error: str = None
    context: Dict = field(default_factory=dict)
    subtasks: List['Task'] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime = None
    completed_at: datetime = None
    
    def __dict__(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    success: bool
    output: str
    agent_name: str
    duration: float
    metadata: Dict = field(default_factory=dict)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_concurrent: int = 3, retry_attempts: int = 2):
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.agents: Dict[str, BaseAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue = None
        self._semaphore: asyncio.Semaphore = None
        self._running = False
    
    def register_agent(self, name: str, agent: BaseAgent):
        """注册 Agent"""
        self.agents[name] = agent
    
    def unregister_agent(self, name: str):
        """注销 Agent"""
        if name in self.agents:
            del self.agents[name]
    
    def create_task(self, description: str, context: Dict = None) -> Task:
        """创建任务"""
        task = Task(description=description, context=context or {})
        self.tasks[task.id] = task
        return task
    
    def create_subtask(self, parent_task: Task, description: str) -> Task:
        """创建子任务"""
        subtask = Task(description=description)
        parent_task.subtasks.append(subtask)
        return subtask
    
    async def execute_task(self, task: Task, agent_name: str = None) -> TaskResult:
        """执行单个任务"""
        if task.status == TaskStatus.RUNNING:
            raise ValueError(f"任务 {task.id} 正在执行中")
        
        # 选择 Agent
        if not agent_name:
            agent_name = self._select_agent(task)
        
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' 未注册")
        
        agent = self.agents[agent_name]
        task.assigned_agent = agent_name
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        start_time = datetime.now()
        
        try:
            # 执行任务
            context = task.context.get("context", "")
            result = await agent.execute(task.description, context)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            return TaskResult(
                task_id=task.id,
                success=True,
                output=result,
                agent_name=agent_name,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            return TaskResult(
                task_id=task.id,
                success=False,
                output=str(e),
                agent_name=agent_name,
                duration=(datetime.now() - start_time).total_seconds(),
                metadata={"error": str(e)}
            )
    
    def _select_agent(self, task: Task) -> str:
        """智能选择 Agent（简化版）"""
        # 可以根据任务描述智能匹配最合适的 Agent
        # 这里简单轮询
        if not self.agents:
            raise ValueError("没有可用的 Agent")
        return list(self.agents.keys())[0]
    
    async def execute_parallel(self, tasks: List[Task]) -> List[TaskResult]:
        """并行执行多个任务"""
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def limited_execute(task: Task) -> TaskResult:
            async with self._semaphore:
                return await self.execute_task(task)
        
        results = await asyncio.gather(
            *[limited_execute(task) for task in tasks],
            return_exceptions=True
        )
        
        return [r if isinstance(r, TaskResult) else TaskResult(
            task_id="unknown",
            success=False,
            output=str(r),
            agent_name="unknown",
            duration=0,
            metadata={"error": str(r)}
        ) for r in results]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_agent_status(self) -> Dict[str, Dict]:
        """获取所有 Agent 状态"""
        return {name: agent.get_status() for name, agent in self.agents.items()}


class MultiAgentOrchestrator:
    """多 Agent 编排器"""
    
    def __init__(self, default_provider: str = "qwen"):
        self.scheduler = TaskScheduler()
        self.default_provider = default_provider
        self.llm_client: LLMClient = None
        self._task_decomposer: BaseAgent = None
    
    def set_llm(self, llm_client: LLMClient):
        """设置默认 LLM"""
        self.llm_client = llm_client
        for agent in self.scheduler.agents.values():
            agent.set_llm(llm_client)
    
    def add_agent(self, name: str, agent: BaseAgent):
        """添加 Agent"""
        if self.llm_client:
            agent.set_llm(self.llm_client)
        self.scheduler.register_agent(name, agent)
    
    async def decompose_task(self, task_description: str) -> List[str]:
        """使用 LLM 分解任务"""
        if not self._task_decomposer:
            self._task_decomposer = self._create_decomposer()
        
        prompt = f"""请将以下任务分解为 3-5 个可执行的子任务：

任务：{task_description}

要求：
1. 每个子任务应该是独立可执行的
2. 子任务之间可以有依赖关系
3. 用简洁的语言描述每个子任务

请直接列出子任务，格式为：
1. 子任务 1
2. 子任务 2
..."""
        
        response = self._task_decomposer.execute_sync(prompt)
        
        # 解析子任务列表
        subtasks = []
        for line in response.split("\n"):
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                subtasks.append(line.split(".", 1)[1].strip())
        
        return subtasks or [task_description]
    
    def _create_decomposer(self) -> BaseAgent:
        """创建任务分解 Agent"""
        from agents import create_agent
        return create_agent(
            "architect",
            name="TaskDecomposer",
            llm_client=self.llm_client or LLMClient(self.default_provider),
            temperature=0.3
        )
    
    async def run(self, task_description: str, auto_decompose: bool = True,
                  agent_assignments: Dict[str, str] = None) -> List[TaskResult]:
        """运行任务"""
        
        # 任务分解
        if auto_decompose:
            subtasks = await self.decompose_task(task_description)
        else:
            subtasks = [task_description]
        
        # 创建任务
        tasks = []
        for i, subtask_desc in enumerate(subtasks):
            task = self.scheduler.create_task(
                description=subtask_desc,
                context={"original_task": task_description, "index": i}
            )
            tasks.append(task)
        
        # 分配 Agent
        if agent_assignments:
            for task, agent_name in zip(tasks, agent_assignments.values()):
                task.assigned_agent = agent_name
        
        # 执行任务
        results = await self.scheduler.execute_parallel(tasks)
        
        return results
    
    def run_sync(self, task_description: str, **kwargs) -> List[TaskResult]:
        """同步运行任务"""
        return asyncio.run(self.run(task_description, **kwargs))
    
    def get_status(self) -> Dict:
        """获取编排器状态"""
        return {
            "agents": self.scheduler.get_agent_status(),
            "total_tasks": len(self.scheduler.tasks),
            "pending_tasks": len([t for t in self.scheduler.tasks.values() 
                                 if t.status == TaskStatus.PENDING]),
            "completed_tasks": len([t for t in self.scheduler.tasks.values() 
                                   if t.status == TaskStatus.COMPLETED])
        }
