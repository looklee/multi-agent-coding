"""
多 Agent 编码助手 - 主入口
"""
import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from api.llm import LLMClient, create_client
from agents import create_agent, get_available_agents
from core.orchestrator import MultiAgentOrchestrator


console = Console()


def print_banner():
    """打印横幅"""
    console.print(Panel.fit(
        "[bold blue]Multi-Agent Coding Assistant[/bold blue]\n"
        "多 Agent 协作编码助手",
        style="blue"
    ))


def print_agents_table(orchestrator: MultiAgentOrchestrator):
    """打印 Agent 状态表"""
    table = Table(title="已注册 Agent")
    table.add_column("名称", style="cyan")
    table.add_column("专长", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("完成任务", style="magenta")
    
    for name, status in orchestrator.scheduler.get_agent_status().items():
        table.add_row(
            name,
            status.get("specialty", "-"),
            status.get("status", "unknown"),
            str(status.get("completed_tasks", 0))
        )
    
    console.print(table)


def interactive_mode(orchestrator: MultiAgentOrchestrator):
    """交互模式"""
    console.print("\n[bold green]进入交互模式[/bold green]")
    console.print("输入任务描述，输入 'quit' 退出\n")
    
    while True:
        try:
            task = console.input("[bold yellow]任务:[/bold yellow] ").strip()
            
            if task.lower() in ['quit', 'exit', 'q']:
                break
            
            if not task:
                continue
            
            console.print("\n[bold blue]正在处理任务...[/bold blue]\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(description="Agent 协作中...", total=None)
                
                results = orchestrator.run_sync(task, auto_decompose=True)
            
            console.print("\n[bold green]任务完成![/bold green]\n")
            
            for i, result in enumerate(results, 1):
                panel_style = "green" if result.success else "red"
                console.print(Panel(
                    result.output[:500] + ("..." if len(result.output) > 500 else ""),
                    title=f"Agent {result.agent_name} - 子任务 {i}",
                    style=panel_style
                ))
            
            console.print()
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]错误：{e}[/bold red]\n")


def single_task_mode(orchestrator: MultiAgentOrchestrator, task: str):
    """单次任务模式"""
    console.print(f"\n[bold blue]执行任务：{task}[/bold blue]\n")
    
    results = orchestrator.run_sync(task, auto_decompose=True)
    
    console.print("\n[bold green]执行完成![/bold green]\n")
    
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.success else "✗"
        console.print(f"\n[{status_icon}] Agent: {result.agent_name}")
        console.print(f"耗时：{result.duration:.2f}秒")
        console.print(Panel(result.output, title="输出"))


def main():
    parser = argparse.ArgumentParser(description="多 Agent 编码助手")
    parser.add_argument("--provider", "-p", default="qwen",
                       choices=["qwen", "doubao", "claude", "deepseek", "moonshot", "gemini"],
                       help="选择 LLM 提供商")
    parser.add_argument("--model", "-m", help="指定模型名称")
    parser.add_argument("--api-key", "-k", help="API Key（或使用环境变量）")
    parser.add_argument("--agent", "-a", action="append",
                       help="启用的 Agent（可多次指定）")
    parser.add_argument("--list-agents", action="store_true",
                       help="列出可用 Agent")
    parser.add_argument("task", nargs="?", help="任务描述（不填则进入交互模式）")
    
    args = parser.parse_args()
    
    print_banner()
    
    # 列出可用 Agent
    if args.list_agents:
        console.print("\n可用 Agent 类型:")
        for agent in get_available_agents():
            console.print(f"  - {agent}")
        return
    
    # 创建 LLM 客户端
    try:
        llm_client = create_client(
            provider=args.provider,
            api_key=args.api_key,
            model=args.model
        )
        console.print(f"[green]✓[/green] LLM 客户端已初始化：{args.provider}\n")
    except ValueError as e:
        console.print(f"[red]✗[/red] LLM 初始化失败：{e}")
        console.print("\n请设置环境变量或使用 --api-key 参数")
        console.print(f"需要的环境变量：{args.provider.upper()}_API_KEY")
        sys.exit(1)
    
    # 创建编排器
    orchestrator = MultiAgentOrchestrator(default_provider=args.provider)
    orchestrator.set_llm(llm_client)
    
    # 注册 Agent
    enabled_agents = args.agent or get_available_agents()
    for agent_type in enabled_agents:
        if agent_type in get_available_agents():
            agent = create_agent(agent_type, llm_client=llm_client)
            orchestrator.add_agent(agent_type, agent)
            console.print(f"[green]✓[/green] Agent 已注册：{agent_type}")
    
    console.print()
    print_agents_table(orchestrator)
    
    # 执行任务
    if args.task:
        single_task_mode(orchestrator, args.task)
    else:
        interactive_mode(orchestrator)
    
    console.print("\n[bold blue]再见！[/bold blue]\n")


if __name__ == "__main__":
    main()
