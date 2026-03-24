"""
全功能集成测试套件
测试所有核心功能和高级特性
"""
import pytest
import sys
import os
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 核心模块测试 ====================

class TestCoreModules:
    """核心模块测试"""
    
    def test_import_all_modules(self):
        """测试所有模块可导入"""
        # 核心模块
        from api.llm import LLMClient, Message, create_client
        from agents import create_agent, get_available_agents
        from core.orchestrator import MultiAgentOrchestrator, TaskScheduler, Task
        
        # 高级模块
        from agents.autonomy import AutonomousAgent, AutonomousPlanner, SelfReflector
        from agents.tools import get_tool_registry, CalculatorTool
        from agents.sandbox import SandboxedExecutor, execute_code
        
        # 生态系统
        from plugins import get_plugin_manager, get_marketplace, get_config_hub
        
        assert True
    
    def test_agent_creation(self):
        """测试 Agent 创建"""
        from agents import create_agent, get_available_agents
        
        agents = get_available_agents()
        assert len(agents) >= 11
        
        # 创建各种类型的 Agent
        for agent_type in ['codewriter', 'codereviewer', 'debugger']:
            agent = create_agent(agent_type)
            assert agent is not None
            assert agent.name == agent_type
    
    def test_tool_registry(self):
        """测试工具注册表"""
        from agents.tools import get_tool_registry
        
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        # 应该有至少 7 个内置工具
        assert len(tools) >= 7
        
        # 检查关键工具存在
        tool_names = [t.name for t in tools]
        assert 'calculator' in tool_names
        assert 'shell_exec' in tool_names
        assert 'file_read' in tool_names
    
    def test_sandbox_execution(self):
        """测试沙箱执行"""
        from agents.sandbox import execute_code
        
        # 安全代码执行
        result = execute_code("print(sum(range(10)))")
        assert result.success is True
        assert "45" in result.stdout
    
    def test_cost_optimizer(self):
        """测试成本优化"""
        from core.cost_optimizer import SmartRouter
        
        router = SmartRouter()
        
        # 测试复杂度评估
        score, model_type = router.estimate_complexity("什么是 Python?")
        assert score <= 4
        
        score, model_type = router.estimate_complexity("设计高并发分布式系统")
        assert score >= 7


# ==================== 高级功能测试 ====================

class TestAdvancedFeatures:
    """高级功能测试"""
    
    def test_autonomous_planning(self):
        """测试自主规划"""
        from agents.autonomy import AutonomousPlanner
        
        planner = AutonomousPlanner()
        plan = planner.create_plan("完成一个复杂任务")
        
        assert plan.goal == "完成一个复杂任务"
        assert len(plan.steps) > 0
    
    def test_self_reflection(self):
        """测试自我反思"""
        from agents.autonomy import SelfReflector
        
        reflector = SelfReflector()
        reflection = reflector.reflect(
            "测试任务",
            "成功完成",
            success=True,
            confidence_before=5
        )
        
        assert reflection.task_description == "测试任务"
        assert len(reflection.what_went_well) > 0
    
    def test_meta_cognition(self):
        """测试元认知"""
        from agents.autonomy import MetaCognition
        
        meta = MetaCognition()
        assessment = meta.assess_capability("简单任务")
        
        assert assessment.confidence_level > 0
        assert isinstance(assessment.capabilities, dict)
    
    def test_human_in_loop(self):
        """测试人机协作"""
        from core.human_in_loop import HumanInLoop, ReviewStatus
        
        hil = HumanInLoop(timeout_seconds=2)
        review = hil.request_review("t1", "审核内容", reason="测试")
        
        assert review.status == ReviewStatus.PENDING
        
        # 批准
        hil.approve(review.id)
        updated = hil.get_review(review.id)
        assert updated.status == ReviewStatus.APPROVED
    
    def test_execution_tracing(self):
        """测试执行追溯"""
        from core.tracer import ExecutionLogger, EventType
        
        logger = ExecutionLogger()
        trace = logger.create_trace("test-001", "测试任务")
        
        logger.log_event("test-001", EventType.TASK_STARTED)
        logger.log_event("test-001", EventType.TASK_COMPLETED, data={"result": "ok"})
        
        retrieved = logger.get_trace("test-001")
        assert retrieved.status == "completed"
        assert len(retrieved.events) == 2


# ==================== 生态系统测试 ====================

class TestEcosystem:
    """生态系统测试"""
    
    def test_plugin_system(self):
        """测试插件系统"""
        from plugins import get_plugin_manager
        
        manager = get_plugin_manager()
        manager.discover_and_load()
        
        # 应该能正常工作
        assert manager.loader is not None
    
    def test_marketplace(self):
        """测试工具市场"""
        from plugins import get_marketplace
        
        marketplace = get_marketplace()
        
        # 提交测试工具
        tool_id = marketplace.submit_tool(
            name="Test Tool",
            description="测试工具",
            code="print('hello')",
            category="test",
            tags=["test", "demo"]
        )
        
        # 搜索工具
        tools = marketplace.search_tools("测试")
        assert len(tools) > 0
        
        # 获取工具
        tool = marketplace.get_tool(tool_id)
        assert tool.name == "Test Tool"
    
    def test_config_hub(self):
        """测试配置中心"""
        from plugins import get_config_hub
        
        hub = get_config_hub()
        
        # 搜索模板
        templates = hub.search_templates("")
        assert len(templates) >= 4  # 至少有 4 个默认模板
        
        # 应用模板
        template = templates[0]
        config = hub.apply_template(template.id)
        assert config is not None
    
    def test_plugin_lifecycle(self):
        """测试插件生命周期"""
        from plugins.plugin_system import PluginLoader
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PluginLoader(plugins_dir=tmpdir)
            
            # 创建测试插件
            plugin_dir = os.path.join(tmpdir, "test_plugin")
            os.makedirs(plugin_dir)
            
            # 创建清单
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "测试插件",
                "entry_point": "main"
            }
            with open(os.path.join(plugin_dir, "manifest.json"), 'w') as f:
                import json
                json.dump(manifest, f)
            
            # 创建插件代码
            code = '''
from plugins.plugin_system import Plugin

class Plugin(Plugin):
    name = "test_plugin"
    version = "1.0.0"
    
    def on_load(self):
        pass
'''
            with open(os.path.join(plugin_dir, "main.py"), 'w') as f:
                f.write(code)
            
            # 发现和加载
            manifests = loader.discover_plugins()
            assert len(manifests) == 1


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        from agents import create_agent
        from agents.tools import get_tool_registry
        from agents.sandbox import execute_code
        from core.tracer import ExecutionLogger, EventType
        from core.cost_optimizer import get_cost_tracker
        
        # 1. 创建 Agent
        agent = create_agent("codewriter")
        
        # 2. 使用工具
        registry = get_tool_registry()
        result = registry.execute_tool("calculator", expression="10 + 20")
        assert result.output == 30
        
        # 3. 执行代码
        code_result = execute_code("print('test')")
        assert code_result.success is True
        
        # 4. 追踪执行
        logger = ExecutionLogger()
        trace = logger.create_trace("integration-test", "集成测试")
        logger.log_event("integration-test", EventType.TASK_STARTED)
        
        # 5. 记录成本
        tracker = get_cost_tracker()
        tracker.record("qwen", "qwen-plus", 100, 50, "integration-test")
        
        # 验证
        stats = tracker.get_stats()
        assert stats["total_cost"] > 0
    
    def test_multi_agent_collaboration(self):
        """测试多 Agent 协作"""
        from agents import create_agent
        from core.orchestrator import TaskScheduler
        
        scheduler = TaskScheduler(max_concurrent=2)
        
        # 注册多个 Agent
        for agent_type in ['codewriter', 'codereviewer']:
            agent = create_agent(agent_type)
            scheduler.register_agent(agent_type, agent)
        
        # 创建任务
        task = scheduler.create_task("测试任务")
        
        # 验证 Agent 已注册
        assert len(scheduler.agents) >= 2
    
    def test_tool_enhanced_agent(self):
        """测试增强型 Agent"""
        from agents import create_agent
        from agents.tools import get_tool_registry
        
        # 创建带工具的 Agent
        agent = create_agent("codewriter", enable_tools=True)
        
        # 验证工具已启用
        assert agent.enable_tools is True
        
        # 获取可用工具
        tools = agent.get_available_tools()
        assert len(tools) > 0
    
    def test_config_template_workflow(self):
        """测试配置模板工作流"""
        from plugins import get_config_hub
        
        hub = get_config_hub()
        
        # 创建自定义模板
        template_id = hub.create_template(
            name="Custom Template",
            agent_type="codewriter",
            config={"temperature": 0.8, "max_tokens": 2048},
            description="自定义测试模板",
            tags=["custom", "test"]
        )
        
        # 搜索并应用
        templates = hub.search_templates("Custom")
        assert len(templates) > 0
        
        config = hub.apply_template(template_id)
        assert config["temperature"] == 0.8


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""
    
    def test_concurrent_execution(self):
        """测试并发执行"""
        import asyncio
        from agents.sandbox import SandboxedExecutor
        
        async def run_tests():
            executor = SandboxedExecutor(timeout=5)
            
            async def run_task(code):
                return executor.execute(code)
            
            # 并发执行多个任务
            tasks = [
                run_task(f"print({i})")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            assert len(results) == 5
        
        asyncio.run(run_tests())
    
    def test_cache_performance(self):
        """测试缓存性能"""
        from core.cost_optimizer import TokenCache
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            cache = TokenCache(db_path=f.name)
            
            # 写入缓存
            cache.set("test prompt", "test response", 10, 20)
            
            # 读取缓存
            import time
            start = time.time()
            for _ in range(100):
                cache.get("test prompt")
            elapsed = time.time() - start
            
            # 应该在 1 秒内完成
            assert elapsed < 1.0


# ==================== 边界测试 ====================

class TestEdgeCases:
    """边界测试"""
    
    def test_empty_inputs(self):
        """测试空输入"""
        from agents.sandbox import execute_code
        
        result = execute_code("")
        # 空代码应该不报错
        assert result is not None
    
    def test_invalid_tool_execution(self):
        """测试无效工具执行"""
        from agents.tools import get_tool_registry
        
        registry = get_tool_registry()
        result = registry.execute_tool("nonexistent_tool")
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_sandbox_security(self):
        """测试沙箱安全性"""
        from agents.sandbox import execute_code
        
        # 尝试执行危险代码
        result = execute_code("import os; os.system('echo test')")
        
        # 应该被阻止
        assert result.success is False
        assert "Security" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
