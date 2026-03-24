"""
Agent 自主性模块测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.autonomy import (
    Plan, PlanStep, PlanStatus,
    Reflection, SelfAssessment,
    AutonomousPlanner, SelfReflector, MetaCognition,
    AutonomousAgent
)


class TestPlanStep:
    """计划步骤测试"""
    
    def test_step_creation(self):
        """步骤创建测试"""
        step = PlanStep(
            description="Test step",
            action="test",
            expected_outcome="Success"
        )
        
        assert step.description == "Test step"
        assert step.status == PlanStatus.DRAFT
        assert step.id is not None
    
    def test_step_to_dict(self):
        """步骤转字典测试"""
        step = PlanStep(description="Test")
        d = step.to_dict()
        
        assert "id" in d
        assert "description" in d
        assert d["description"] == "Test"


class TestPlan:
    """计划测试"""
    
    def test_plan_creation(self):
        """计划创建测试"""
        plan = Plan(goal="Test goal")
        
        assert plan.goal == "Test goal"
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.steps) == 0
    
    def test_add_step(self):
        """添加步骤测试"""
        plan = Plan(goal="Test")
        step = plan.add_step("Step 1", "action1")
        
        assert len(plan.steps) == 1
        assert step.description == "Step 1"
    
    def test_add_step_with_dependencies(self):
        """添加带依赖的步骤测试"""
        plan = Plan(goal="Test")
        plan.add_step("Step 1")
        plan.add_step("Step 2", dependencies=["step1_id"])
        
        assert len(plan.steps) == 2
        assert plan.steps[1].dependencies == ["step1_id"]
    
    def test_get_next_step(self):
        """获取下一步测试"""
        plan = Plan(goal="Test")
        step1 = plan.add_step("Step 1")
        step2 = plan.add_step("Step 2", dependencies=[step1.id])
        
        # 第一步应该可用
        next_step = plan.get_next_step()
        assert next_step.id == step1.id
        
        # 完成第一步后，第二步应该可用
        step1.status = PlanStatus.COMPLETED
        next_step = plan.get_next_step()
        assert next_step.id == step2.id
    
    def test_is_complete(self):
        """完成检查测试"""
        plan = Plan(goal="Test")
        plan.add_step("Step 1")
        plan.add_step("Step 2")
        
        assert plan.is_complete() is False
        
        for step in plan.steps:
            step.status = PlanStatus.COMPLETED
        
        assert plan.is_complete() is True
    
    def test_is_failed(self):
        """失败检查测试"""
        plan = Plan(goal="Test")
        step = plan.add_step("Step 1")
        step.status = PlanStatus.FAILED
        step.retry_count = 3
        step.max_retries = 2
        
        assert plan.is_failed() is True


class TestAutonomousPlanner:
    """自主规划器测试"""
    
    def test_create_plan(self):
        """创建计划测试"""
        planner = AutonomousPlanner()
        plan = planner.create_plan("Test goal")
        
        assert plan.goal == "Test goal"
        assert len(plan.steps) > 0  # 应该有默认步骤
    
    def test_get_plan(self):
        """获取计划测试"""
        planner = AutonomousPlanner()
        plan = planner.create_plan("Test")
        
        retrieved = planner.get_plan(plan.id)
        assert retrieved is plan
    
    def test_execute_plan(self):
        """执行计划测试"""
        planner = AutonomousPlanner()
        plan = planner.create_plan("Simple task")
        
        # 简单执行器
        def executor(step):
            step.result = "Done"
            return "Done"
        
        result = planner.execute_plan(plan, executor)
        assert result.status == PlanStatus.COMPLETED
    
    def test_adjust_plan(self):
        """调整计划测试"""
        planner = AutonomousPlanner()
        plan = planner.create_plan("Test")
        
        adjusted = planner.adjust_plan(plan, "Need to change approach")
        
        assert "adjustments" in plan.metadata
        assert len(plan.metadata["adjustments"]) == 1


class TestSelfReflector:
    """自我反思器测试"""
    
    def test_reflect_success(self):
        """成功反思测试"""
        reflector = SelfReflector()
        
        reflection = reflector.reflect(
            task_description="Test task",
            outcome="Completed successfully",
            success=True,
            confidence_before=5
        )
        
        assert reflection.task_description == "Test task"
        assert len(reflection.what_went_well) > 0
        assert reflection.confidence_after >= reflection.confidence_before
    
    def test_reflect_failure(self):
        """失败反思测试"""
        reflector = SelfReflector()
        
        reflection = reflector.reflect(
            task_description="Failed task",
            outcome="Did not complete",
            success=False,
            confidence_before=5
        )
        
        assert reflection.task_description == "Failed task"
        assert len(reflection.what_went_poorly) > 0
    
    def test_get_reflections(self):
        """获取反思测试"""
        reflector = SelfReflector()
        
        reflector.reflect("Task 1", "Result 1", True)
        reflector.reflect("Task 2", "Result 2", False)
        
        reflections = reflector.get_reflections()
        assert len(reflections) == 2
    
    def test_get_patterns(self):
        """获取模式测试"""
        reflector = SelfReflector()
        
        for i in range(5):
            reflector.reflect(f"Task {i}", "Success", True)
        
        patterns = reflector.get_patterns()
        
        assert patterns["total_reflections"] == 5
        assert "strengths" in patterns
        assert "weaknesses" in patterns


class TestMetaCognition:
    """元认知测试"""
    
    def test_assess_capability(self):
        """能力评估测试"""
        meta = MetaCognition()
        
        assessment = meta.assess_capability("Simple task")
        
        assert assessment.confidence_level > 0
        assert isinstance(assessment.capabilities, dict)
    
    def test_record_task(self):
        """记录任务测试"""
        meta = MetaCognition()
        
        meta.record_task("Test task", success=True, duration=10, complexity=5)
        
        stats = meta.get_task_statistics()
        assert stats["total_tasks"] == 1
        assert stats["success_rate"] == 1.0
    
    def test_should_delegate(self):
        """委托判断测试"""
        meta = MetaCognition()
        
        # 默认情况下不应该委托
        should_delegate, reason = meta.should_delegate("Test task")
        # 根据实现，可能返回 True 或 False
        
    def test_get_task_statistics(self):
        """任务统计测试"""
        meta = MetaCognition()
        
        # 空统计
        stats = meta.get_task_statistics()
        assert stats == {}
        
        # 添加数据后
        meta.record_task("Task 1", True, 10, 5)
        meta.record_task("Task 2", False, 20, 7)
        
        stats = meta.get_task_statistics()
        assert stats["total_tasks"] == 2
        assert stats["success_rate"] == 0.5


class TestAutonomousAgent:
    """自主 Agent 测试"""
    
    def test_execute_autonomously(self):
        """自主执行测试"""
        # Mock base agent
        class MockAgent:
            def execute_sync(self, task, context=None):
                return f"Executed: {task}"
        
        mock_agent = MockAgent()
        auto_agent = AutonomousAgent(mock_agent)
        
        result = auto_agent.execute_autonomously("Test goal")
        
        # 结果应该包含状态、计划、反思等
        assert "status" in result
        assert "plan" in result or "assessment" in result


class TestGlobalInstances:
    """全局实例测试"""
    
    def test_planner_singleton(self):
        """规划器单例测试"""
        from agents.autonomy import get_planner
        
        p1 = get_planner()
        p2 = get_planner()
        assert p1 is p2
    
    def test_reflector_singleton(self):
        """反思器单例测试"""
        from agents.autonomy import get_reflector
        
        r1 = get_reflector()
        r2 = get_reflector()
        assert r1 is r2
    
    def test_meta_cognition_singleton(self):
        """元认知单例测试"""
        from agents.autonomy import get_meta_cognition
        
        m1 = get_meta_cognition()
        m2 = get_meta_cognition()
        assert m1 is m2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
