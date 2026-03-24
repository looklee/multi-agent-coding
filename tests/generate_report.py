"""
测试报告生成器
"""
import subprocess
import json
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

console = Console()


def run_tests():
    """运行测试"""
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--json-report"],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    return result.stdout, result.returncode


def generate_report():
    """生成测试报告"""
    console.print(Panel.fit(
        "[bold blue]Multi-Agent Coding Assistant - 全功能测试报告[/bold blue]\n"
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        style="blue"
    ))
    
    # 运行测试
    console.print("\n[bold]正在运行测试...[/bold]\n")
    
    try:
        stdout, returncode = run_tests()
    except subprocess.TimeoutExpired:
        console.print("[red]测试超时[/red]")
        return
    
    # 解析结果
    lines = stdout.split('\n')
    
    passed = 0
    failed = 0
    skipped = 0
    total = 0
    
    test_results = []
    
    for line in lines:
        if 'PASSED' in line:
            passed += 1
            total += 1
            if '::' in line:
                test_name = line.split('::')[1].split()[0]
                test_results.append({"name": test_name, "status": "✓"})
        elif 'FAILED' in line:
            failed += 1
            total += 1
            if '::' in line:
                test_name = line.split('::')[1].split()[0]
                test_results.append({"name": test_name, "status": "✗"})
        elif 'SKIPPED' in line:
            skipped += 1
    
    # 显示摘要
    console.print("\n")
    
    summary_table = Table(title="测试摘要", show_header=True)
    summary_table.add_column("指标", style="cyan")
    summary_table.add_column("数量", style="green")
    
    summary_table.add_row("总测试数", str(total))
    summary_table.add_row("通过", str(passed))
    summary_table.add_row("失败", str(failed))
    summary_table.add_row("跳过", str(skipped))
    
    if total > 0:
        pass_rate = (passed / total) * 100
        summary_table.add_row("通过率", f"{pass_rate:.1f}%")
    
    console.print(summary_table)
    
    # 显示失败的测试详情
    if failed > 0:
        console.print("\n[bold red]失败的测试:[/bold red]\n")
        
        failed_table = Table(show_header=True)
        failed_table.add_column("测试名称", style="red")
        failed_table.add_column("状态", style="yellow")
        
        for result in test_results:
            if result["status"] == "✗":
                failed_table.add_row(result["name"], result["status"])
        
        console.print(failed_table)
    
    # 模块统计
    console.print("\n[bold]按模块统计:[/bold]\n")
    
    module_stats = {}
    for result in test_results:
        module = result["name"].split('[')[0].split('.')[0]
        if module not in module_stats:
            module_stats[module] = {"passed": 0, "failed": 0}
        
        if result["status"] == "✓":
            module_stats[module]["passed"] += 1
        else:
            module_stats[module]["failed"] += 1
    
    module_table = Table(show_header=True)
    module_table.add_column("模块", style="cyan")
    module_table.add_column("通过", style="green")
    module_table.add_column("失败", style="red")
    module_table.add_column("总数", style="yellow")
    
    for module, stats in sorted(module_stats.items()):
        total_module = stats["passed"] + stats["failed"]
        module_table.add_row(
            module,
            str(stats["passed"]),
            str(stats["failed"]),
            str(total_module)
        )
    
    console.print(module_table)
    
    # 最终状态
    console.print("\n")
    if failed == 0 and total > 0:
        console.print(Panel(
            f"[bold green]✓ 所有测试通过！({passed}/{total})[/bold green]",
            style="green"
        ))
    else:
        console.print(Panel(
            f"[bold yellow]⚠ {failed} 个测试失败 ({passed}/{total} 通过)[/bold yellow]",
            style="yellow"
        ))
    
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "modules": module_stats
    }


if __name__ == "__main__":
    generate_report()
