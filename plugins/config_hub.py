"""
配置共享模块
- Agent 配置模板
- 配置导入导出
- 配置推荐
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib


@dataclass
class AgentConfigTemplate:
    """Agent 配置模板"""
    id: str
    name: str
    description: str
    agent_type: str
    config: Dict
    tags: List[str] = field(default_factory=list)
    author: str = ""
    version: str = "1.0.0"
    
    # 使用统计
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "config": self.config,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentConfigTemplate':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            agent_type=data.get("agent_type", ""),
            config=data.get("config", {}),
            tags=data.get("tags", []),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0)
        )


class ConfigHub:
    """配置中心"""
    
    def __init__(self, data_dir: str = "config_hub"):
        self.data_dir = Path(data_dir)
        self._templates: Dict[str, AgentConfigTemplate] = {}
        self._user_configs: Dict[str, Dict] = {}
        
        self._init_dirs()
        self._load_templates()
    
    def _init_dirs(self):
        """初始化目录"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "templates").mkdir(exist_ok=True)
        (self.data_dir / "user_configs").mkdir(exist_ok=True)
    
    def _load_templates(self):
        """加载模板"""
        templates_dir = self.data_dir / "templates"
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                template = AgentConfigTemplate.from_dict(data)
                self._templates[template.id] = template
            except Exception as e:
                print(f"Failed to load template {template_file}: {e}")
    
    def save_template(self, template: AgentConfigTemplate) -> str:
        """保存配置模板"""
        template.id = self._generate_id(template.name)
        template.updated_at = time.time()
        
        self._templates[template.id] = template
        
        # 保存到文件
        template_path = self.data_dir / "templates" / f"{template.id}.json"
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
        
        return template.id
    
    def create_template(self, name: str, agent_type: str, 
                       config: Dict, description: str = "",
                       tags: List[str] = None, author: str = "") -> str:
        """创建配置模板"""
        template = AgentConfigTemplate(
            id="",
            name=name,
            description=description,
            agent_type=agent_type,
            config=config,
            tags=tags or [],
            author=author
        )
        return self.save_template(template)
    
    def get_template(self, template_id: str) -> Optional[AgentConfigTemplate]:
        """获取配置模板"""
        return self._templates.get(template_id)
    
    def search_templates(self, query: str, agent_type: str = None,
                        tags: List[str] = None) -> List[AgentConfigTemplate]:
        """搜索配置模板"""
        results = []
        query_lower = query.lower()
        
        for template in self._templates.values():
            # 类型过滤
            if agent_type and template.agent_type != agent_type:
                continue
            
            # 标签过滤
            if tags and not any(t in template.tags for t in tags):
                continue
            
            # 搜索匹配
            score = 0
            if query_lower in template.name.lower():
                score += 3
            if query_lower in template.description.lower():
                score += 1
            if query_lower in template.agent_type.lower():
                score += 2
            
            if score > 0 or (not query):
                results.append((score, template))
        
        results.sort(key=lambda x: (-x[0], -x[1].rating, -x[1].downloads))
        return [t for _, t in results]
    
    def apply_template(self, template_id: str, 
                      overrides: Dict = None) -> Optional[Dict]:
        """应用配置模板"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        config = template.config.copy()
        
        # 应用覆盖
        if overrides:
            config.update(overrides)
        
        template.downloads += 1
        return config
    
    def rate_template(self, template_id: str, rating: int) -> bool:
        """评分模板"""
        template = self.get_template(template_id)
        if not template:
            return False
        
        total = template.rating * template.rating_count + rating
        template.rating_count += 1
        template.rating = total / template.rating_count
        
        return True
    
    def export_config(self, config: Dict, name: str = "") -> str:
        """导出配置"""
        if not name:
            name = f"config_{int(time.time())}"
        
        config_path = self.data_dir / "user_configs" / f"{name}.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return str(config_path)
    
    def import_config(self, config_path: str) -> Optional[Dict]:
        """导入配置"""
        path = Path(config_path)
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Failed to import config: {e}")
            return None
    
    def get_recommendations(self, agent_type: str, 
                           limit: int = 5) -> List[AgentConfigTemplate]:
        """获取推荐配置"""
        templates = [
            t for t in self._templates.values()
            if t.agent_type == agent_type
        ]
        templates.sort(key=lambda t: (-t.rating, -t.downloads))
        return templates[:limit]
    
    def get_popular_templates(self, limit: int = 10) -> List[AgentConfigTemplate]:
        """获取热门配置"""
        templates = list(self._templates.values())
        templates.sort(key=lambda t: (-t.downloads, -t.rating))
        return templates[:limit]
    
    def _generate_id(self, name: str) -> str:
        """生成 ID"""
        return hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]


# 预定义配置模板
DEFAULT_TEMPLATES = {
    "codewriter_standard": {
        "name": "标准代码生成",
        "agent_type": "codewriter",
        "config": {
            "temperature": 0.7,
            "max_tokens": 4096,
            "system_prompt": "你是一个专业的代码生成助手。生成高质量、可维护的代码。",
            "top_p": 0.9
        },
        "tags": ["代码生成", "标准", "通用"],
        "description": "适用于一般代码生成任务的标准配置"
    },
    "codereviewer_strict": {
        "name": "严格代码审查",
        "agent_type": "codereviewer",
        "config": {
            "temperature": 0.3,
            "max_tokens": 2048,
            "system_prompt": "你是一个严格的代码审查专家。仔细检查每个细节。",
            "top_p": 0.8
        },
        "tags": ["代码审查", "严格", "质量"],
        "description": "严格的代码审查配置，适合生产代码"
    },
    "debugger_detailed": {
        "name": "详细调试",
        "agent_type": "debugger",
        "config": {
            "temperature": 0.4,
            "max_tokens": 4096,
            "system_prompt": "你是一个耐心的调试专家。提供详细的分析和解释。",
            "top_p": 0.9
        },
        "tags": ["调试", "详细", "教学"],
        "description": "提供详细的调试分析，适合学习"
    },
    "architect_enterprise": {
        "name": "企业架构设计",
        "agent_type": "architect",
        "config": {
            "temperature": 0.5,
            "max_tokens": 8192,
            "system_prompt": "你是资深企业架构师。考虑可扩展性、安全性和成本。",
            "top_p": 0.9
        },
        "tags": ["架构", "企业", "设计"],
        "description": "企业级架构设计配置"
    }
}


def init_default_templates(hub: ConfigHub = None):
    """初始化默认模板"""
    if hub is None:
        hub = get_config_hub()
    
    for key, template_data in DEFAULT_TEMPLATES.items():
        # 检查是否已存在
        existing = hub.search_templates(template_data["name"])
        if existing:
            continue
        
        hub.create_template(
            name=template_data["name"],
            agent_type=template_data["agent_type"],
            config=template_data["config"],
            description=template_data["description"],
            tags=template_data["tags"],
            author="system"
        )


# 全局实例
_hub: Optional[ConfigHub] = None


def get_config_hub() -> ConfigHub:
    """获取配置中心实例"""
    global _hub
    if _hub is None:
        _hub = ConfigHub()
        init_default_templates(_hub)
    return _hub
