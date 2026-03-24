"""
命令行工具 - 查看成本、日志、审核等
"""
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cmd_costs(args):
    """查看成本统计"""
    try:
        from core.cost_optimizer import get_cost_tracker
        tracker = get_cost_tracker()
        
        stats = tracker.get_stats(days=args.days)
        
        console.print(Panel(f"💰 成本统计 (最近 {args.days} 天)", style="green"))
        
        # 总览
        console.print(f"\n**总成本**: ¥{stats['total_cost']:.4f}")
        console.print(f"**总 Token**: {stats['total_tokens']:,}")
        
        # 按提供商
        if stats['by_provider']:
            table = Table(title="按提供商")
            table.add_column("提供商", style="cyan")
            table.add_column("成本 (¥)", style="green")
            table.add_column("Token", style="yellow")
            
            for provider, data in stats['by_provider'].items():
                table.add_row(
                    provider,
                    f"{data['cost']:.4f}",
                    f"{data['tokens']:,}"
                )
            console.print(table)
        
        # 按模型
        if stats['by_model']:
            table = Table(title="按模型")
            table.add_column("模型", style="cyan")
            table.add_column("成本 (¥)", style="green")
            table.add_column("Token", style="yellow")
            
            for model, data in stats['by_model'].items():
                table.add_row(
                    model,
                    f"{data['cost']:.4f}",
                    f"{data['tokens']:,}"
                )
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")


def cmd_logs(args):
    """查看执行日志"""
    try:
        from core.tracer import get_logger
        logger = get_logger()
        
        if args.task_id:
            # 查看特定任务
            trace = logger.get_trace(args.task_id)
            if trace:
                console.print(Panel(f"📋 任务追溯：{args.task_id}", style="blue"))
                console.print(f"\n**描述**: {trace.description}")
                console.print(f"**状态**: {trace.status}")
                console.print(f"**事件数**: {len(trace.events)}")
                
                if args.export:
                    content = logger.export_trace(args.task_id, format=args.export)
                    console.print(content)
                else:
                    # 显示决策链
                    console.print("\n\n## 决策链")
                    for event in trace.get_decision_chain():
                        console.print(f"  • {event['event_type']} - {event.get('agent_name', '')}")
            else:
                console.print(f"[yellow]未找到任务 {args.task_id}[/yellow]")
        else:
            # 最近任务
            traces = logger.get_recent_traces(limit=args.limit)
            
            table = Table(title=f"最近 {len(traces)} 个任务")
            table.add_column("任务 ID", style="cyan")
            table.add_column("描述", style="white")
            table.add_column("状态", style="green")
            table.add_column("事件数", style="yellow")
            
            for trace in traces:
                desc = trace.description[:40] + "..." if len(trace.description) > 40 else trace.description
                table.add_row(
                    trace.task_id,
                    desc,
                    trace.status,
                    str(len(trace.events))
                )
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")


def cmd_reviews(args):
    """查看审核请求"""
    try:
        from core.human_in_loop import get_human_in_loop
        hil = get_human_in_loop()
        
        pending = hil.get_pending_reviews()
        
        if not pending:
            console.print("[green]✓ 没有待审核的请求[/green]")
            return
        
        console.print(Panel(f"👤 待审核请求 ({len(pending)} 个)", style="yellow"))
        
        for review in pending:
            console.print(f"\n[bold]ID[/bold]: {review.id}")
            console.print(f"[bold]任务[/bold]: {review.task_id}")
            console.print(f"[bold]Agent[/bold]: {review.agent_name}")
            console.print(f"[bold]原因[/bold]: {review.reason}")
            console.print(f"[bold]内容[/bold]: {review.content[:200]}...")
            console.print(f"[bold]等待时间[/bold]: {int((review.created_at - review.created_at) / 60)} 分钟")
            console.print("---")
            
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")


def cmd_cache(args):
    """查看缓存统计"""
    try:
        from core.cost_optimizer import get_cache
        cache = get_cache()
        
        stats = cache.get_stats()
        
        console.print(Panel("💾 缓存统计", style="cyan"))
        console.print(f"\n**缓存条目**: {stats['cache_size']}")
        console.print(f"**命中次数**: {stats['total_hits']}")
        console.print(f"**节省 Token**: {stats['tokens_saved']:,}")
        
        if args.clear:
            cache.clear_expired()
            console.print("\n[green]✓ 已清理过期缓存[/green]")
            
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")


def cmd_approve(args):
    """批准审核"""
    try:
        from core.human_in_loop import get_human_in_loop
        hil = get_human_in_loop()
        
        if args.approve:
            success = hil.approve(args.approve, reviewer="cli", feedback=args.feedback)
            if success:
                console.print(f"[green]✓ 已批准审核 {args.approve}[/green]")
            else:
                console.print(f"[red]审核 {args.approve} 不存在[/red]")
        elif args.reject:
            success = hil.reject(args.reject, reviewer="cli", feedback=args.feedback)
            if success:
                console.print(f"[green]✓ 已拒绝审核 {args.reject}[/green]")
            else:
                console.print(f"[red]审核 {args.reject} 不存在[/red]")
            
    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent 工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # costs 命令
    costs_parser = subparsers.add_parser("costs", help="查看成本统计")
    costs_parser.add_argument("--days", "-d", type=int, default=7, help="统计天数")
    costs_parser.set_defaults(func=cmd_costs)
    
    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="查看执行日志")
    logs_parser.add_argument("--task-id", "-t", help="任务 ID")
    logs_parser.add_argument("--limit", "-l", type=int, default=10, help="显示数量")
    logs_parser.add_argument("--export", "-e", choices=["json", "markdown"], help="导出格式")
    logs_parser.set_defaults(func=cmd_logs)
    
    # reviews 命令
    reviews_parser = subparsers.add_parser("reviews", help="查看审核请求")
    reviews_parser.set_defaults(func=cmd_reviews)
    
    # cache 命令
    cache_parser = subparsers.add_parser("cache", help="查看缓存")
    cache_parser.add_argument("--clear", action="store_true", help="清理过期缓存")
    cache_parser.set_defaults(func=cmd_cache)
    
    # approve 命令
    approve_parser = subparsers.add_parser("approve", help="审核操作")
    approve_parser.add_argument("--approve", "-a", help="批准审核 ID")
    approve_parser.add_argument("--reject", "-r", help="拒绝审核 ID")
    approve_parser.add_argument("--feedback", "-f", default="", help="审核反馈")
    approve_parser.set_defaults(func=cmd_approve)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
