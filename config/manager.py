"""
配置管理模块
支持 YAML 配置文件加载和热重载
"""
import os
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading


@dataclass
class AgentConfig:
    """Agent 配置"""
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    top_p: float = 0.9


@dataclass
class ProviderConfig:
    """提供商配置"""
    base_url: str = ""
    model: str = ""
    api_key_env: str = ""


@dataclass
class AppConfig:
    """应用配置"""
    default_provider: str = "qwen"
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    scheduler_max_concurrent: int = 3
    scheduler_retry_attempts: int = 2
    scheduler_timeout: int = 300


class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更处理器"""
    
    def __init__(self, config_manager: 'ConfigManager'):
        self.config_manager = config_manager
    
    def on_modified(self, event):
        if event.src_path.endswith(('.yaml', '.yml')):
            self.config_manager._reload_from_file()


class ConfigManager:
    """配置管理器 - 支持热重载"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = None):
        if self._initialized:
            return
        
        self.config_path = config_path or self._find_config_file()
        self.config: AppConfig = AppConfig()
        self._file_hash: str = ""
        self._observers: list = []
        self._callbacks: list = []
        
        self._load_config()
        self._initialized = True
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        possible_paths = [
            Path("config/config.yaml"),
            Path("config.yaml"),
            Path("config/config.yml"),
            Path(__file__).parent / "config" / "config.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return ""
    
    def _load_config(self):
        """加载配置"""
        if not self.config_path or not os.path.exists(self.config_path):
            self._load_from_env()
            return
        
        self._reload_from_file()
        self._start_watcher()
    
    def _reload_from_file(self):
        """从文件重新加载配置"""
        if not os.path.exists(self.config_path):
            return
        
        # 检查文件是否真的变化
        with open(self.config_path, 'rb') as f:
            new_hash = hashlib.md5(f.read()).hexdigest()
        
        if new_hash == self._file_hash:
            return
        
        self._file_hash = new_hash
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self._parse_config(data)
            
            # 通知回调
            for callback in self._callbacks:
                try:
                    callback(self.config)
                except Exception:
                    pass
            
        except Exception as e:
            print(f"加载配置文件失败：{e}")
    
    def _parse_config(self, data: Dict[str, Any]):
        """解析配置数据"""
        if not data:
            return
        
        # 默认提供商
        if 'default_model' in data:
            self.config.default_provider = data['default_model'].get('provider', 'qwen')
        
        # 提供商配置
        if 'providers' in data:
            for name, prov_data in data['providers'].items():
                self.config.providers[name] = ProviderConfig(
                    base_url=prov_data.get('base_url', ''),
                    model=prov_data.get('model', ''),
                    api_key_env=prov_data.get('api_key_env', f"{name.upper()}_API_KEY")
                )
        
        # Agent 配置
        if 'agents' in data:
            for name, agent_data in data['agents'].items():
                self.config.agents[name] = AgentConfig(
                    temperature=agent_data.get('temperature', 0.7),
                    max_tokens=agent_data.get('max_tokens', 4096),
                    system_prompt=agent_data.get('system_prompt', ''),
                    top_p=agent_data.get('top_p', 0.9)
                )
        
        # 调度器配置
        if 'scheduler' in data:
            sched = data['scheduler']
            self.config.scheduler_max_concurrent = sched.get('max_concurrent_tasks', 3)
            self.config.scheduler_retry_attempts = sched.get('retry_attempts', 2)
            self.config.scheduler_timeout = sched.get('timeout_seconds', 300)
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        from dotenv import load_dotenv
        load_dotenv()
        
        # 默认提供商配置
        self.config.providers['qwen'] = ProviderConfig(
            base_url="https://dashscope.aliyuncs.com/api/v1",
            model="qwen-plus",
            api_key_env="QWEN_API_KEY"
        )
        self.config.providers['deepseek'] = ProviderConfig(
            base_url="",
            model="deepseek-chat",
            api_key_env="DEEPSEEK_API_KEY"
        )
        self.config.providers['moonshot'] = ProviderConfig(
            base_url="",
            model="moonshot-v1-8k",
            api_key_env="MOONSHOT_API_KEY"
        )
    
    def _start_watcher(self):
        """启动文件监听"""
        if not self.config_path:
            return
        
        observer = Observer()
        handler = ConfigChangeHandler(self)
        watch_dir = os.path.dirname(self.config_path) or "."
        observer.schedule(handler, watch_dir, recursive=False)
        observer.start()
        self._observers.append(observer)
    
    def on_config_change(self, callback):
        """注册配置变更回调"""
        self._callbacks.append(callback)
    
    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """获取 Agent 配置"""
        return self.config.agents.get(agent_type, AgentConfig())
    
    def get_provider_config(self, provider: str) -> ProviderConfig:
        """获取提供商配置"""
        return self.config.providers.get(provider, ProviderConfig())
    
    def reload(self):
        """手动重新加载配置"""
        self._reload_from_file()
    
    @property
    def all_agents(self) -> list:
        """获取所有配置的 Agent 类型"""
        return list(self.config.agents.keys())
    
    @property
    def all_providers(self) -> list:
        """获取所有配置的提供商"""
        return list(self.config.providers.keys())


# 全局配置实例
def get_config(config_path: str = None) -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(config_path)
