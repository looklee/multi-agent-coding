"""
使用示例：多 Agent 协作完成编程任务
"""
from api.llm import create_client, Message
from agents import create_agent
from core.orchestrator import MultiAgentOrchestrator


def example_1_basic():
    """示例 1：基础使用 - 代码生成 + 审查"""
    print("=" * 50)
    print("示例 1：基础代码生成与审查")
    print("=" * 50)
    
    # 创建客户端（使用 Qwen）
    llm = create_client(provider="qwen")
    
    # 创建代码生成 Agent
    code_writer = create_agent("codewriter", llm_client=llm)
    
    # 生成代码
    task = "用 Python 实现一个 LRU 缓存类，支持 get 和 put 操作"
    code = code_writer.execute_sync(task)
    
    print(f"\n生成的代码:\n{code[:500]}...\n")
    
    # 创建代码审查 Agent
    reviewer = create_agent("codereviewer", llm_client=llm)
    
    # 审查代码
    review = reviewer.execute_sync(f"请审查以下代码:\n\n{code}")
    print(f"\n审查意见:\n{review}\n")


def example_2_orchestrator():
    """示例 2：使用编排器自动分解任务"""
    print("=" * 50)
    print("示例 2：多 Agent 协作 - 完整功能实现")
    print("=" * 50)
    
    # 创建编排器
    orchestrator = MultiAgentOrchestrator()
    llm = create_client(provider="qwen")
    orchestrator.set_llm(llm)
    
    # 注册所有 Agent
    for agent_type in ["codewriter", "testgenerator", "docwriter"]:
        agent = create_agent(agent_type, llm_client=llm)
        orchestrator.add_agent(agent_type, agent)
    
    # 执行复杂任务（自动分解）
    task = "实现一个支持过期时间的缓存系统，包含单元测试和使用文档"
    
    print(f"\n任务：{task}\n")
    results = orchestrator.run_sync(task, auto_decompose=True)
    
    for i, result in enumerate(results, 1):
        print(f"\n--- 子任务 {i} ---")
        print(f"Agent: {result.agent_name}")
        print(f"耗时：{result.duration:.2f}s")
        print(f"输出:\n{result.output[:300]}{'...' if len(result.output) > 300 else ''}")


def example_3_custom_workflow():
    """示例 3：自定义工作流"""
    print("=" * 50)
    print("示例 3：自定义工作流 - 迭代改进")
    print("=" * 50)
    
    llm = create_client(provider="qwen")
    
    writer = create_agent("codewriter", llm_client=llm)
    reviewer = create_agent("codereviewer", llm_client=llm)
    debugger = create_agent("debugger", llm_client=llm)
    
    # 初始需求
    requirement = "实现一个快速排序算法"
    
    # 第一轮：生成代码
    print("\n[1/3] 生成初始代码...")
    code = writer.execute_sync(requirement)
    print(f"代码长度：{len(code)} 字符")
    
    # 第二轮：审查
    print("\n[2/3] 审查代码...")
    review = reviewer.execute_sync(f"审查以下代码:\n{code}")
    print(f"审查意见长度：{len(review)} 字符")
    
    # 第三轮：根据审查意见改进
    print("\n[3/3] 改进代码...")
    improved_code = writer.execute_sync(
        f"原始代码:\n{code}\n\n审查意见:\n{review}\n\n请根据审查意见改进代码"
    )
    print(f"改进后代码长度：{len(improved_code)} 字符")
    
    print("\n✓ 迭代完成!")


def example_4_parallel():
    """示例 4：并行执行"""
    print("=" * 50)
    print("示例 4：并行执行 - 多文件生成")
    print("=" * 50)
    
    import asyncio
    from core.orchestrator import TaskScheduler
    
    scheduler = TaskScheduler(max_concurrent=3)
    llm = create_client(provider="qwen")
    
    # 注册 Agent
    for name in ["writer1", "writer2", "writer3"]:
        agent = create_agent("codewriter", name=name, llm_client=llm)
        scheduler.register_agent(name, agent)
    
    # 创建并行任务
    tasks = [
        scheduler.create_task("实现冒泡排序"),
        scheduler.create_task("实现插入排序"),
        scheduler.create_task("实现选择排序"),
    ]
    
    print("\n并行执行 3 个排序算法实现...\n")
    
    # 并行执行
    results = asyncio.run(scheduler.execute_parallel(tasks))
    
    for i, result in enumerate(results, 1):
        print(f"\n任务 {i} 完成 by {result.agent_name}, 耗时：{result.duration:.2f}s")


def example_5_switch_provider():
    """示例 5：切换不同模型提供商"""
    print("=" * 50)
    print("示例 5：切换模型提供商")
    print("=" * 50)
    
    providers = [
        ("qwen", "qwen-coding-plus"),
        ("doubao", "doubao-pro-32k"),
    ]
    
    task = "用一句话解释什么是递归"
    
    for provider, model in providers:
        print(f"\n使用 {provider} ({model}):")
        try:
            llm = create_client(provider=provider, model=model)
            agent = create_agent("codewriter", llm_client=llm)
            response = agent.execute_sync(task)
            print(f"  回答：{response[:100]}...")
        except Exception as e:
            print(f"  错误：{e}")


if __name__ == "__main__":
    # 运行示例
    # 注意：需要先配置 API Key
    
    print("\n选择要运行的示例:")
    print("1. 基础代码生成与审查")
    print("2. 多 Agent 协作（编排器）")
    print("3. 自定义工作流（迭代改进）")
    print("4. 并行执行")
    print("5. 切换模型提供商")
    
    choice = input("\n输入序号 (1-5): ").strip()
    
    examples = {
        "1": example_1_basic,
        "2": example_2_orchestrator,
        "3": example_3_custom_workflow,
        "4": example_4_parallel,
        "5": example_5_switch_provider,
    }
    
    if choice in examples:
        examples[choice]()
    else:
        print("无效选择")
