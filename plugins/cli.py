"""
插件命令行工具
"""
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def cmd_plugins_list(args):
    """列出已安装插件"""
    from plugins import get_plugin_manager
    
    manager = get_plugin_manager()
    manager.discover_and_load()
    
    plugins = manager.loader.get_all_plugins()
    
    if not plugins:
        console.print("[yellow]没有已安装的插件[/yellow]")
        return
    
    table = Table(title="已安装插件")
    table.add_column("名称", style="cyan")
    table.add_column("版本", style="green")
    table.add_column("状态", style="yellow")
    table.add_column("描述", style="white")
    
    for plugin in plugins:
        status = "✓ 已启用" if plugin.enabled else "✗ 已禁用"
        table.add_row(
            plugin.name,
            plugin.version,
            status,
            getattr(plugin, 'description', "")[:50]
        )
    
    console.print(table)


def cmd_plugins_enable(args):
    """启用插件"""
    from plugins import get_plugin_manager
    
    manager = get_plugin_manager()
    
    if manager.loader.enable_plugin(args.name):
        console.print(f"[green]✓ 已启用插件：{args.name}[/green]")
    else:
        console.print(f"[red]✗ 无法启用插件：{args.name}[/red]")


def cmd_plugins_disable(args):
    """禁用插件"""
    from plugins import get_plugin_manager
    
    manager = get_plugin_manager()
    
    if manager.loader.disable_plugin(args.name):
        console.print(f"[green]✓ 已禁用插件：{args.name}[/green]")
    else:
        console.print(f"[red]✗ 无法禁用插件：{args.name}[/red]")


def cmd_marketplace_browse(args):
    """浏览工具市场"""
    from plugins import get_marketplace
    
    marketplace = get_marketplace()
    
    tools = marketplace.browse_tools(category=args.category, limit=args.limit)
    
    if not tools:
        console.print("[yellow]没有找到工具[/yellow]")
        return
    
    table = Table(title=f"工具市场 - {args.category or '全部'}")
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("评分", style="yellow")
    table.add_column("下载", style="green")
    
    for tool in tools:
        rating = f"⭐ {tool.rating:.1f}" if tool.rating > 0 else "未评分"
        table.add_row(
            tool.name,
            tool.description[:50] + ("..." if len(tool.description) > 50 else ""),
            rating,
            str(tool.downloads)
        )
    
    console.print(table)


def cmd_marketplace_search(args):
    """搜索工具"""
    from plugins import get_marketplace
    
    marketplace = get_marketplace()
    
    tools = marketplace.search_tools(
        args.query,
        category=args.category
    )
    
    if not tools:
        console.print("[yellow]没有找到匹配的工具[/yellow]")
        return
    
    table = Table(title=f"搜索结果：{args.query}")
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("标签", style="yellow")
    table.add_column("评分", style="green")
    
    for tool in tools:
        tags = ", ".join(tool.tags[:3])
        rating = f"⭐ {tool.rating:.1f}" if tool.rating > 0 else "未评分"
        table.add_row(
            tool.name,
            tool.description[:40] + ("..." if len(tool.description) > 40 else ""),
            tags,
            rating
        )
    
    console.print(table)


def cmd_marketplace_download(args):
    """下载工具"""
    from plugins import get_marketplace
    
    marketplace = get_marketplace()
    
    tool = marketplace.get_tool(args.tool_id)
    if not tool:
        console.print(f"[red]✗ 工具不存在：{args.tool_id}[/red]")
        return
    
    path = marketplace.download_tool(args.tool_id)
    if path:
        console.print(f"[green]✓ 已下载工具：{tool.name}[/green]")
        console.print(f"  路径：{path}")
    else:
        console.print(f"[red]✗ 下载失败[/red]")


def cmd_marketplace_rate(args):
    """评分工具"""
    from plugins import get_marketplace
    
    marketplace = get_marketplace()
    
    if marketplace.rate_tool(args.tool_id, args.rating):
        console.print(f"[green]✓ 评分成功：{args.rating} 星[/green]")
    else:
        console.print(f"[red]✗ 评分失败[/red]")


def cmd_config_list(args):
    """列出配置模板"""
    from plugins import get_config_hub
    
    hub = get_config_hub()
    
    templates = hub.search_templates(args.query or "")
    
    if not templates:
        console.print("[yellow]没有找到配置模板[/yellow]")
        return
    
    table = Table(title="配置模板")
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="green")
    table.add_column("描述", style="white")
    table.add_column("下载", style="yellow")
    
    for template in templates:
        table.add_row(
            template.name,
            template.agent_type,
            template.description[:40] + ("..." if len(template.description) > 40 else ""),
            str(template.downloads)
        )
    
    console.print(table)


def cmd_config_show(args):
    """显示配置详情"""
    from plugins import get_config_hub
    
    hub = get_config_hub()
    
    template = hub.get_template(args.template_id)
    if not template:
        console.print(f"[red]✗ 配置模板不存在：{args.template_id}[/red]")
        return
    
    console.print(Panel(
        f"[bold]{template.name}[/bold]\n\n"
        f"类型：{template.agent_type}\n"
        f"描述：{template.description}\n"
        f"作者：{template.author}\n"
        f"评分：⭐ {template.rating:.1f} ({template.rating_count} 次评分)\n"
        f"下载：{template.downloads} 次\n\n"
        f"[bold]配置内容:[/bold]\n"
        f"[code]{json.dumps(template.config, indent=2, ensure_ascii=False)}[/code]",
        title="配置模板详情"
    ))


def cmd_config_apply(args):
    """应用配置模板"""
    from plugins import get_config_hub
    
    hub = get_config_hub()
    
    config = hub.apply_template(args.template_id)
    if config:
        console.print("[green]✓ 配置已应用[/green]")
        console.print(f"\n[code]{json.dumps(config, indent=2, ensure_ascii=False)}[/code]")
    else:
        console.print(f"[red]✗ 配置模板不存在：{args.template_id}[/red]")


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent 插件工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # plugins 命令
    plugins_parser = subparsers.add_parser("plugins", help="插件管理")
    plugins_subparsers = plugins_parser.add_subparsers()
    
    # plugins list
    list_parser = plugins_subparsers.add_parser("list", help="列出插件")
    list_parser.set_defaults(func=cmd_plugins_list)
    
    # plugins enable
    enable_parser = plugins_subparsers.add_parser("enable", help="启用插件")
    enable_parser.add_argument("name", help="插件名称")
    enable_parser.set_defaults(func=cmd_plugins_enable)
    
    # plugins disable
    disable_parser = plugins_subparsers.add_parser("disable", help="禁用插件")
    disable_parser.add_argument("name", help="插件名称")
    disable_parser.set_defaults(func=cmd_plugins_disable)
    
    # marketplace 命令
    market_parser = subparsers.add_parser("marketplace", help="工具市场")
    market_subparsers = market_parser.add_subparsers()
    
    # marketplace browse
    browse_parser = market_subparsers.add_parser("browse", help="浏览工具")
    browse_parser.add_argument("--category", "-c", help="分类")
    browse_parser.add_argument("--limit", "-l", type=int, default=20, help="数量限制")
    browse_parser.set_defaults(func=cmd_marketplace_browse)
    
    # marketplace search
    search_parser = market_subparsers.add_parser("search", help="搜索工具")
    search_parser.add_argument("query", help="搜索词")
    search_parser.add_argument("--category", "-c", help="分类")
    search_parser.set_defaults(func=cmd_marketplace_search)
    
    # marketplace download
    download_parser = market_subparsers.add_parser("download", help="下载工具")
    download_parser.add_argument("tool_id", help="工具 ID")
    download_parser.set_defaults(func=cmd_marketplace_download)
    
    # marketplace rate
    rate_parser = market_subparsers.add_parser("rate", help="评分工具")
    rate_parser.add_argument("tool_id", help="工具 ID")
    rate_parser.add_argument("rating", type=int, choices=[1,2,3,4,5], help="评分 1-5")
    rate_parser.set_defaults(func=cmd_marketplace_rate)
    
    # config 命令
    config_parser = subparsers.add_parser("config", help="配置中心")
    config_subparsers = config_parser.add_subparsers()
    
    # config list
    config_list_parser = config_subparsers.add_parser("list", help="列出配置")
    config_list_parser.add_argument("--query", "-q", help="搜索词")
    config_list_parser.set_defaults(func=cmd_config_list)
    
    # config show
    config_show_parser = config_subparsers.add_parser("show", help="显示配置")
    config_show_parser.add_argument("template_id", help="模板 ID")
    config_show_parser.set_defaults(func=cmd_config_show)
    
    # config apply
    config_apply_parser = config_subparsers.add_parser("apply", help="应用配置")
    config_apply_parser.add_argument("template_id", help="模板 ID")
    config_apply_parser.set_defaults(func=cmd_config_apply)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
