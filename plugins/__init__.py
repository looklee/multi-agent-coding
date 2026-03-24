"""
Plugins package
"""
from plugins.plugin_system import (
    Plugin, PluginContext, PluginLoader, PluginManager,
    get_plugin_manager, create_plugin, hook
)
from plugins.marketplace import (
    ToolMarketplace, ToolInfo, ToolReview,
    get_marketplace, register_tool
)
from plugins.config_hub import (
    ConfigHub, AgentConfigTemplate,
    get_config_hub, init_default_templates
)

__all__ = [
    # Plugin system
    "Plugin",
    "PluginContext",
    "PluginLoader",
    "PluginManager",
    "get_plugin_manager",
    "create_plugin",
    "hook",
    
    # Marketplace
    "ToolMarketplace",
    "ToolInfo",
    "ToolReview",
    "get_marketplace",
    "register_tool",
    
    # Config hub
    "ConfigHub",
    "AgentConfigTemplate",
    "get_config_hub",
    "init_default_templates",
]
