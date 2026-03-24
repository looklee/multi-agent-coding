"""
插件系统模块
- 插件定义和加载
- 插件生命周期管理
- 插件依赖解析
"""
import os
import json
import importlib
import importlib.util
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import hashlib


@dataclass
class PluginManifest:
    """插件清单"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "main"
    plugins_dir: str = ""
    
    # 元数据
    homepage: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "homepage": self.homepage,
            "license": self.license,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginManifest':
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", "main"),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT"),
            tags=data.get("tags", [])
        )
    
    @classmethod
    def from_file(cls, path: str) -> 'PluginManifest':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class Plugin:
    """插件基类"""
    
    name: str = ""
    version: str = ""
    
    def __init__(self, context: 'PluginContext'):
        self.context = context
        self.enabled = False
    
    def on_load(self):
        """插件加载时调用"""
        pass
    
    def on_unload(self):
        """插件卸载时调用"""
        pass
    
    def on_enable(self):
        """插件启用时调用"""
        self.enabled = True
    
    def on_disable(self):
        """插件禁用时调用"""
        self.enabled = False


class PluginContext:
    """插件上下文"""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.services: Dict[str, Any] = {}
    
    def register_service(self, name: str, service: Any):
        """注册服务"""
        self.services[name] = service
    
    def get_service(self, name: str) -> Optional[Any]:
        """获取服务"""
        return self.services.get(name)
    
    def set_data(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)


class PluginLoader:
    """插件加载器"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self._plugins: Dict[str, Plugin] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._contexts: Dict[str, PluginContext] = {}
    
    def discover_plugins(self) -> List[PluginManifest]:
        """发现插件"""
        manifests = []
        
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return manifests
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            manifest_path = plugin_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = PluginManifest.from_file(str(manifest_path))
                    manifest.plugins_dir = str(plugin_dir)
                    manifests.append(manifest)
                    self._manifests[manifest.name] = manifest
                except Exception as e:
                    print(f"Failed to load manifest for {plugin_dir}: {e}")
        
        return manifests
    
    def load_plugin(self, name: str) -> Optional[Plugin]:
        """加载插件"""
        if name in self._plugins:
            return self._plugins[name]
        
        manifest = self._manifests.get(name)
        if not manifest:
            return None
        
        # 检查依赖
        for dep in manifest.dependencies:
            if dep not in self._plugins:
                print(f"Missing dependency: {dep}")
                return None
        
        # 加载插件模块
        plugin_path = Path(manifest.plugins_dir) / f"{manifest.entry_point}.py"
        if not plugin_path.exists():
            print(f"Plugin entry point not found: {plugin_path}")
            return None
        
        try:
            # 动态导入
            spec = importlib.util.spec_from_file_location(
                name, str(plugin_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取插件类
            plugin_class = getattr(module, 'Plugin', None)
            if not plugin_class:
                print(f"No Plugin class found in {name}")
                return None
            
            # 创建插件实例
            context = PluginContext()
            plugin = plugin_class(context)
            plugin.name = manifest.name
            plugin.version = manifest.version
            
            # 调用加载钩子
            plugin.on_load()
            
            self._plugins[name] = plugin
            self._contexts[name] = context
            
            return plugin
            
        except Exception as e:
            print(f"Failed to load plugin {name}: {e}")
            return None
    
    def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        if name not in self._plugins:
            return False
        
        plugin = self._plugins[name]
        plugin.on_unload()
        
        del self._plugins[name]
        del self._contexts[name]
        
        return True
    
    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        if name not in self._plugins:
            # 尝试加载
            plugin = self.load_plugin(name)
            if not plugin:
                return False
        
        plugin = self._plugins[name]
        plugin.on_enable()
        return True
    
    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        if name not in self._plugins:
            return False
        
        plugin = self._plugins[name]
        plugin.on_disable()
        return True
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> List[Plugin]:
        """获取所有插件"""
        return list(self._plugins.values())
    
    def get_loaded_plugins(self) -> List[str]:
        """获取已加载插件列表"""
        return list(self._plugins.keys())


class PluginManager:
    """插件管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.loader = PluginLoader()
        self._hook_registry: Dict[str, List[Callable]] = {}
        self._initialized = True
    
    def discover_and_load(self):
        """发现并加载所有插件"""
        manifests = self.loader.discover_plugins()
        
        for manifest in manifests:
            self.loader.load_plugin(manifest.name)
    
    def register_hook(self, hook_name: str, callback: Callable, plugin_name: str = ""):
        """注册钩子"""
        if hook_name not in self._hook_registry:
            self._hook_registry[hook_name] = []
        
        self._hook_registry[hook_name].append({
            "callback": callback,
            "plugin": plugin_name
        })
    
    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """触发钩子"""
        if hook_name not in self._hook_registry:
            return []
        
        results = []
        for hook in self._hook_registry[hook_name]:
            try:
                result = hook["callback"](*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook {hook_name} failed: {e}")
        
        return results
    
    def install_plugin(self, plugin_data: Dict) -> bool:
        """安装插件"""
        # 创建插件目录
        name = plugin_data.get("name", "")
        version = plugin_data.get("version", "")
        
        plugins_dir = Path(self.loader.plugins_dir)
        plugin_dir = plugins_dir / name
        
        if plugin_dir.exists():
            print(f"Plugin {name} already installed")
            return False
        
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # 写入清单
        manifest = PluginManifest(
            name=name,
            version=version,
            description=plugin_data.get("description", ""),
            author=plugin_data.get("author", ""),
            dependencies=plugin_data.get("dependencies", [])
        )
        
        manifest_path = plugin_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest.to_dict(), f, indent=2)
        
        # 写入代码
        code = plugin_data.get("code", "")
        if code:
            entry_point = plugin_data.get("entry_point", "main")
            code_path = plugin_dir / f"{entry_point}.py"
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
        
        # 刷新并加载
        self.loader.discover_plugins()
        self.loader.load_plugin(name)
        
        return True
    
    def uninstall_plugin(self, name: str) -> bool:
        """卸载插件"""
        # 先禁用和卸载
        self.loader.unload_plugin(name)
        
        # 删除目录
        plugin_dir = Path(self.loader.plugins_dir) / name
        if plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin_dir)
        
        # 从清单中移除
        if name in self._manifests:
            del self._manifests[name]
        
        return True
    
    def get_plugin_info(self, name: str) -> Optional[Dict]:
        """获取插件信息"""
        manifest = self.loader._manifests.get(name)
        if not manifest:
            return None
        
        plugin = self.loader.get_plugin(name)
        
        return {
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "author": manifest.author,
            "enabled": plugin.enabled if plugin else False,
            "loaded": plugin is not None,
            "dependencies": manifest.dependencies
        }


# 全局实例
_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取插件管理器"""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


# 插件开发辅助函数
def create_plugin(name: str, version: str, description: str = ""):
    """创建插件装饰器"""
    def decorator(cls):
        cls.name = name
        cls.version = version
        return cls
    return decorator


def hook(hook_name: str):
    """钩子注册装饰器"""
    def decorator(func):
        func._hook_name = hook_name
        return func
    return decorator


# 示例插件
class ExamplePlugin(Plugin):
    """示例插件"""
    name = "example"
    version = "1.0.0"
    
    def on_load(self):
        print(f"Plugin {self.name} loaded")
        self.context.register_service("example_service", self)
    
    def on_enable(self):
        super().on_enable()
        print(f"Plugin {self.name} enabled")
    
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


if __name__ == "__main__":
    # 测试
    manager = get_plugin_manager()
    manager.discover_and_load()
    
    print("Loaded plugins:", manager.loader.get_loaded_plugins())
