"""
Agent 自主性模块
- 自主规划
- 目标分解
- 自我反思
- 元认知
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import re


class PlanStatus(Enum):
    """计划状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ADJUSTED = "adjusted"


@dataclass
class PlanStep:
    """计划步骤"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    action: str = ""
    expected_outcome: str = ""
    dependencies: List[str] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    result: str = ""
    error: str = ""
    retry_count: int = 0
    max_retries: int = 2
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "expected_outcome": self.expected_outcome,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count
        }


@dataclass
class Plan:
    """执行计划"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    reflection: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def add_step(self, description: str, action: str = "", 
                 dependencies: List[str] = None) -> PlanStep:
        """添加步骤"""
        step = PlanStep(
            description=description,
            action=action,
            dependencies=dependencies or []
        )
        self.steps.append(step)
        return step
    
    def get_next_step(self) -> Optional[PlanStep]:
        """获取下一个可执行步骤"""
        completed_ids = {
            s.id for s in self.steps 
            if s.status == PlanStatus.COMPLETED
        }
        
        for step in self.steps:
            if step.status == PlanStatus.DRAFT:
                # 检查依赖是否完成
                if all(dep_id in completed_ids for dep_id in step.dependencies):
                    return step
        
        return None
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def is_complete(self) -> bool:
        """检查计划是否完成"""
        return all(s.status == PlanStatus.COMPLETED for s in self.steps)
    
    def is_failed(self) -> bool:
        """检查计划是否失败"""
        return any(s.status == PlanStatus.FAILED and s.retry_count >= s.max_retries 
                   for s in self.steps)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "reflection": self.reflection,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


@dataclass
class Reflection:
    """反思记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_description: str = ""
    what_went_well: List[str] = field(default_factory=list)
    what_went_poorly: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    confidence_before: int = 0  # 1-10
    confidence_after: int = 0   # 1-10
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "what_went_well": self.what_went_well,
            "what_went_poorly": self.what_went_poorly,
            "lessons_learned": self.lessons_learned,
            "action_items": self.action_items,
            "confidence_before": self.confidence_before,
            "confidence_after": self.confidence_after,
            "created_at": self.created_at
        }


@dataclass
class SelfAssessment:
    """自我评估"""
    capabilities: Dict[str, float] = field(default_factory=dict)  # 能力评分 0-1
    confidence_level: float = 0.0
    known_limitations: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "capabilities": self.capabilities,
            "confidence_level": self.confidence_level,
            "known_limitations": self.known_limitations,
            "recommended_actions": self.recommended_actions
        }


class AutonomousPlanner:
    """自主规划器"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._plans: Dict[str, Plan] = {}
        self._reflections: List[Reflection] = []
    
    def create_plan(self, goal: str, context: str = "") -> Plan:
        """创建执行计划"""
        plan = Plan(goal=goal)
        self._plans[plan.id] = plan
        
        if self.llm:
            # 使用 LLM 生成计划
            plan = self._generate_plan_with_llm(plan, context)
        else:
            # 使用规则生成计划
            plan = self._generate_plan_with_rules(plan, context)
        
        return plan
    
    def _generate_plan_with_llm(self, plan: Plan, context: str) -> Plan:
        """使用 LLM 生成计划"""
        prompt = f"""请为以下目标制定一个详细的执行计划：

目标：{plan.goal}
上下文：{context}

要求：
1. 将目标分解为 3-7 个具体步骤
2. 每个步骤应该是可执行的
3. 标明步骤之间的依赖关系
4. 预期每个步骤的输出

请以 JSON 格式返回，格式如下：
{{
    "steps": [
        {{
            "id": "step1",
            "description": "步骤描述",
            "action": "具体行动",
            "expected_outcome": "预期输出",
            "dependencies": []
        }}
    ],
    "estimated_difficulty": 1-10,
    "potential_challenges": ["挑战 1", "挑战 2"]
}}"""
        
        try:
            from api.llm import Message
            response = self.llm.simple_chat(prompt)
            
            # 解析 JSON 响应
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
                
                for step_data in plan_data.get("steps", []):
                    plan.add_step(
                        description=step_data.get("description", ""),
                        action=step_data.get("action", ""),
                        dependencies=step_data.get("dependencies", [])
                    )
                
                plan.metadata["difficulty"] = plan_data.get("estimated_difficulty", 5)
                plan.metadata["challenges"] = plan_data.get("potential_challenges", [])
        except Exception as e:
            # 降级到规则基础
            plan = self._generate_plan_with_rules(plan, context)
        
        return plan
    
    def _generate_plan_with_rules(self, plan: Plan, context: str) -> Plan:
        """使用规则生成计划"""
        # 通用计划模板
        generic_steps = [
            ("理解任务", "analyze", []),
            ("制定方案", "plan", ["step1"]),
            ("执行实现", "execute", ["step2"]),
            ("验证结果", "verify", ["step3"]),
            ("总结输出", "finalize", ["step4"]),
        ]
        
        for desc, action, deps in generic_steps:
            plan.add_step(description=desc, action=action, dependencies=deps)
        
        return plan
    
    def execute_plan(self, plan: Plan, executor_func=None) -> Plan:
        """执行计划"""
        plan.status = PlanStatus.ACTIVE
        
        while not plan.is_complete() and not plan.is_failed():
            step = plan.get_next_step()
            
            if not step:
                if plan.is_failed():
                    plan.status = PlanStatus.FAILED
                    break
                continue
            
            # 执行步骤
            step.status = PlanStatus.ACTIVE
            
            try:
                if executor_func:
                    result = executor_func(step)
                    step.result = result
                    step.status = PlanStatus.COMPLETED
                else:
                    step.status = PlanStatus.COMPLETED
                
            except Exception as e:
                step.retry_count += 1
                step.error = str(e)
                
                if step.retry_count >= step.max_retries:
                    step.status = PlanStatus.FAILED
                else:
                    step.status = PlanStatus.DRAFT  # 重试
        
        if plan.is_complete():
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = time.time()
        elif plan.is_failed():
            plan.status = PlanStatus.FAILED
        
        return plan
    
    def adjust_plan(self, plan: Plan, feedback: str) -> Plan:
        """调整计划"""
        # 根据反馈调整
        plan.metadata["adjustments"] = plan.metadata.get("adjustments", [])
        plan.metadata["adjustments"].append({
            "time": time.time(),
            "feedback": feedback
        })
        
        # 标记为已调整
        plan.status = PlanStatus.ADJUSTED
        
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """获取计划"""
        return self._plans.get(plan_id)
    
    def get_all_plans(self) -> List[Plan]:
        """获取所有计划"""
        return list(self._plans.values())


class SelfReflector:
    """自我反思器"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._reflections: List[Reflection] = []
    
    def reflect(self, task_description: str, outcome: str, 
                success: bool, confidence_before: int = 5) -> Reflection:
        """进行反思"""
        reflection = Reflection(
            task_description=task_description,
            confidence_before=confidence_before
        )
        
        if self.llm:
            reflection = self._reflect_with_llm(reflection, outcome, success)
        else:
            reflection = self._reflect_with_rules(reflection, outcome, success)
        
        reflection.confidence_after = self._calculate_confidence(reflection, success)
        
        self._reflections.append(reflection)
        return reflection
    
    def _reflect_with_llm(self, reflection: Reflection, 
                          outcome: str, success: bool) -> Reflection:
        """使用 LLM 进行反思"""
        prompt = f"""请对以下任务执行进行反思：

任务：{reflection.task_description}
结果：{outcome}
成功：{"是" if success else "否"}

请回答以下问题：
1. 哪些地方做得好？（列出 2-3 点）
2. 哪些地方可以改进？（列出 2-3 点）
3. 学到了什么经验教训？（列出 2-3 点）
4. 下次应该采取什么不同的行动？（列出 2-3 点）

请以 JSON 格式返回：
{{
    "what_went_well": ["点 1", "点 2"],
    "what_went_poorly": ["点 1", "点 2"],
    "lessons_learned": ["教训 1", "教训 2"],
    "action_items": ["行动 1", "行动 2"]
}}"""
        
        try:
            from api.llm import Message
            response = self.llm.simple_chat(prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                reflection.what_went_well = data.get("what_went_well", [])
                reflection.what_went_poorly = data.get("what_went_poorly", [])
                reflection.lessons_learned = data.get("lessons_learned", [])
                reflection.action_items = data.get("action_items", [])
        except:
            reflection = self._reflect_with_rules(reflection, outcome, success)
        
        return reflection
    
    def _reflect_with_rules(self, reflection: Reflection, 
                           outcome: str, success: bool) -> Reflection:
        """使用规则进行反思"""
        if success:
            reflection.what_went_well = ["任务成功完成"]
            reflection.lessons_learned = ["当前方法有效"]
        else:
            reflection.what_went_poorly = ["任务未成功完成"]
            reflection.action_items = ["需要分析方法改进"]
        
        return reflection
    
    def _calculate_confidence(self, reflection: Reflection, 
                             success: bool) -> int:
        """计算反思后的信心水平"""
        base_confidence = reflection.confidence_before
        
        if success:
            # 成功增加信心
            adjustment = len(reflection.what_went_well)
        else:
            # 失败减少信心
            adjustment = -len(reflection.what_went_poorly)
        
        # 经验教训可以缓冲变化
        if reflection.lessons_learned:
            adjustment = int(adjustment * 0.7)  # 减少变化幅度
        
        new_confidence = max(1, min(10, base_confidence + adjustment))
        return new_confidence
    
    def get_reflections(self, limit: int = 10) -> List[Reflection]:
        """获取反思记录"""
        return self._reflections[-limit:]
    
    def get_patterns(self) -> Dict:
        """获取反思中的模式"""
        if not self._reflections:
            return {}
        
        all_well = []
        all_poorly = []
        all_lessons = []
        
        for r in self._reflections:
            all_well.extend(r.what_went_well)
            all_poorly.extend(r.what_went_poorly)
            all_lessons.extend(r.lessons_learned)
        
        # 计算频率
        def count_frequency(items):
            freq = {}
            for item in items:
                freq[item] = freq.get(item, 0) + 1
            return freq
        
        return {
            "strengths": count_frequency(all_well),
            "weaknesses": count_frequency(all_poorly),
            "lessons": count_frequency(all_lessons),
            "total_reflections": len(self._reflections),
            "avg_confidence_change": sum(
                r.confidence_after - r.confidence_before 
                for r in self._reflections
            ) / len(self._reflections)
        }


class MetaCognition:
    """元认知 - 对自身认知的认知"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._assessments: Dict[str, SelfAssessment] = {}
        self._task_history: List[Dict] = []
    
    def assess_capability(self, task_description: str) -> SelfAssessment:
        """评估完成某任务的能力"""
        assessment = SelfAssessment()
        
        if self.llm:
            assessment = self._assess_with_llm(assessment, task_description)
        else:
            assessment = self._assess_with_history(assessment, task_description)
        
        self._assessments[task_description] = assessment
        return assessment
    
    def _assess_with_llm(self, assessment: SelfAssessment, 
                         task_description: str) -> SelfAssessment:
        """使用 LLM 评估"""
        prompt = f"""请评估完成以下任务的能力：

任务：{task_description}

考虑因素：
1. 任务复杂度
2. 所需技能
3. 潜在困难
4. 成功概率

请以 JSON 格式返回：
{{
    "confidence_level": 0.0-1.0,
    "capabilities": {{
        "analysis": 0.0-1.0,
        "implementation": 0.0-1.0,
        "debugging": 0.0-1.0
    }},
    "known_limitations": ["限制 1", "限制 2"],
    "recommended_actions": ["建议 1", "建议 2"]
}}"""
        
        try:
            from api.llm import Message
            response = self.llm.simple_chat(prompt)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                assessment.confidence_level = data.get("confidence_level", 0.5)
                assessment.capabilities = data.get("capabilities", {})
                assessment.known_limitations = data.get("known_limitations", [])
                assessment.recommended_actions = data.get("recommended_actions", [])
        except:
            assessment = self._assess_with_history(assessment, task_description)
        
        return assessment
    
    def _assess_with_history(self, assessment: SelfAssessment, 
                             task_description: str) -> SelfAssessment:
        """基于历史评估"""
        # 简单实现：根据任务关键词匹配历史
        assessment.confidence_level = 0.7  # 默认信心
        
        return assessment
    
    def record_task(self, task_description: str, success: bool, 
                    duration: float = 0, complexity: int = 5):
        """记录任务执行"""
        self._task_history.append({
            "task": task_description,
            "success": success,
            "duration": duration,
            "complexity": complexity,
            "timestamp": time.time()
        })
    
    def should_delegate(self, task_description: str) -> Tuple[bool, str]:
        """判断是否应该委托给其他 Agent"""
        assessment = self.assess_capability(task_description)
        
        if assessment.confidence_level < 0.4:
            return True, f"信心水平过低 ({assessment.confidence_level:.2f})"
        
        if assessment.confidence_level < 0.6 and assessment.known_limitations:
            return True, f"存在已知限制：{', '.join(assessment.known_limitations)}"
        
        return False, ""
    
    def get_task_statistics(self) -> Dict:
        """获取任务统计"""
        if not self._task_history:
            return {}
        
        total = len(self._task_history)
        successful = sum(1 for t in self._task_history if t["success"])
        
        return {
            "total_tasks": total,
            "success_rate": successful / total if total > 0 else 0,
            "avg_duration": sum(t["duration"] for t in self._task_history) / total,
            "avg_complexity": sum(t["complexity"] for t in self._task_history) / total
        }


# 自主 Agent 包装器
class AutonomousAgent:
    """自主 Agent 包装器"""
    
    def __init__(self, base_agent, llm_client=None):
        self.base_agent = base_agent
        self.planner = AutonomousPlanner(llm_client)
        self.reflector = SelfReflector(llm_client)
        self.meta_cognition = MetaCognition(llm_client)
    
    def execute_autonomously(self, goal: str, context: str = "") -> Dict:
        """自主执行任务"""
        # 1. 评估能力
        assessment = self.meta_cognition.assess_capability(goal)
        
        # 2. 检查是否应该委托
        should_delegate, reason = self.meta_cognition.should_delegate(goal)
        if should_delegate:
            return {
                "status": "delegated",
                "reason": reason,
                "assessment": assessment.to_dict()
            }
        
        # 3. 创建计划
        plan = self.planner.create_plan(goal, context)
        
        # 4. 执行计划
        def execute_step(step):
            return self.base_agent.execute_sync(step.description)
        
        result_plan = self.planner.execute_plan(plan, execute_step)
        
        # 5. 反思
        success = result_plan.status == PlanStatus.COMPLETED
        reflection = self.reflector.reflect(
            goal,
            str([s.result for s in result_plan.steps]),
            success,
            confidence_before=int(assessment.confidence_level * 10)
        )
        
        # 6. 记录
        self.meta_cognition.record_task(
            goal,
            success,
            duration=time.time() - plan.created_at
        )
        
        return {
            "status": result_plan.status.value,
            "plan": result_plan.to_dict(),
            "reflection": reflection.to_dict(),
            "assessment": assessment.to_dict()
        }


# 全局实例
_planners: Dict[str, AutonomousPlanner] = {}
_reflectors: Dict[str, SelfReflector] = {}
_meta_cognitions: Dict[str, MetaCognition] = {}


def get_planner(llm_client=None) -> AutonomousPlanner:
    """获取规划器"""
    key = "default"
    if key not in _planners:
        _planners[key] = AutonomousPlanner(llm_client)
    return _planners[key]


def get_reflector(llm_client=None) -> SelfReflector:
    """获取反思器"""
    key = "default"
    if key not in _reflectors:
        _reflectors[key] = SelfReflector(llm_client)
    return _reflectors[key]


def get_meta_cognition(llm_client=None) -> MetaCognition:
    """获取元认知"""
    key = "default"
    if key not in _meta_cognitions:
        _meta_cognitions[key] = MetaCognition(llm_client)
    return _meta_cognitions[key]
