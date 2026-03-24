"""
工具市场模块
- 工具注册和发现
- 工具评分和评论
- 工具推荐
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import hashlib


@dataclass
class ToolInfo:
    """工具信息"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    
    # 使用统计
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    
    # 元数据
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    homepage: str = ""
    license: str = "MIT"
    
    # 工具实现
    code: str = ""
    entry_point: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "homepage": self.homepage,
            "license": self.license
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ToolInfo':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0),
            homepage=data.get("homepage", ""),
            license=data.get("license", "MIT")
        )


@dataclass
class ToolReview:
    """工具评论"""
    id: str
    tool_id: str
    user: str
    rating: int
    comment: str
    created_at: float = field(default_factory=time.time)
    helpful_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "user": self.user,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at,
            "helpful_count": self.helpful_count
        }


class ToolMarketplace:
    """工具市场"""
    
    def __init__(self, data_dir: str = "marketplace_data"):
        self.data_dir = Path(data_dir)
        self._tools: Dict[str, ToolInfo] = {}
        self._reviews: Dict[str, List[ToolReview]] = {}
        self._categories: Dict[str, List[str]] = {}
        self._downloaded: Dict[str, str] = {}  # tool_id -> local_path
        
        self._init_dirs()
        self._load_catalog()
    
    def _init_dirs(self):
        """初始化目录"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "tools").mkdir(exist_ok=True)
        (self.data_dir / "catalog.json").touch(exist_ok=True)
    
    def _load_catalog(self):
        """加载目录"""
        catalog_path = self.data_dir / "catalog.json"
        if catalog_path.exists():
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for tool_data in data.get("tools", []):
                    tool = ToolInfo.from_dict(tool_data)
                    self._tools[tool.id] = tool
                
                for review_data in data.get("reviews", []):
                    review = ToolReview(
                        id=review_data["id"],
                        tool_id=review_data["tool_id"],
                        user=review_data["user"],
                        rating=review_data["rating"],
                        comment=review_data["comment"],
                        created_at=review_data.get("created_at", time.time())
                    )
                    
                    if review.tool_id not in self._reviews:
                        self._reviews[review.tool_id] = []
                    self._reviews[review.tool_id].append(review)
            except Exception as e:
                print(f"Failed to load catalog: {e}")
    
    def _save_catalog(self):
        """保存目录"""
        catalog = {
            "tools": [t.to_dict() for t in self._tools.values()],
            "reviews": [
                r.to_dict() 
                for reviews in self._reviews.values() 
                for r in reviews
            ]
        }
        
        with open(self.data_dir / "catalog.json", 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    def register_tool(self, tool_info: ToolInfo) -> str:
        """注册工具"""
        tool_info.id = self._generate_id(tool_info.name)
        tool_info.updated_at = time.time()
        
        self._tools[tool_info.id] = tool_info
        
        # 添加到分类
        if tool_info.category not in self._categories:
            self._categories[tool_info.category] = []
        self._categories[tool_info.category].append(tool_info.id)
        
        self._save_catalog()
        return tool_info.id
    
    def submit_tool(self, name: str, description: str, code: str,
                    category: str = "general", tags: List[str] = None,
                    author: str = "") -> str:
        """提交新工具"""
        tool_info = ToolInfo(
            id="",  # 将自动生成
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            author=author,
            code=code
        )
        
        tool_id = self.register_tool(tool_info)
        
        # 保存工具代码
        code_path = self.data_dir / "tools" / f"{tool_id}.py"
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return tool_id
    
    def get_tool(self, tool_id: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        return self._tools.get(tool_id)
    
    def search_tools(self, query: str, category: str = None,
                     tags: List[str] = None) -> List[ToolInfo]:
        """搜索工具"""
        results = []
        query_lower = query.lower()
        
        for tool in self._tools.values():
            # 分类过滤
            if category and tool.category != category:
                continue
            
            # 标签过滤
            if tags and not any(t in tool.tags for t in tags):
                continue
            
            # 搜索匹配
            score = 0
            if query_lower in tool.name.lower():
                score += 3
            if query_lower in tool.description.lower():
                score += 1
            if any(query_lower in tag.lower() for tag in tool.tags):
                score += 2
            
            if score > 0:
                results.append((score, tool))
        
        # 按评分排序
        results.sort(key=lambda x: (-x[0], -x[1].rating, -x[1].downloads))
        return [t for _, t in results]
    
    def browse_tools(self, category: str = None, limit: int = 20) -> List[ToolInfo]:
        """浏览工具"""
        tools = list(self._tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        # 按评分和下载量排序
        tools.sort(key=lambda t: (-t.rating, -t.downloads))
        return tools[:limit]
    
    def rate_tool(self, tool_id: str, rating: int, user: str = "anonymous") -> bool:
        """评分工具"""
        if tool_id not in self._tools:
            return False
        
        tool = self._tools[tool_id]
        
        # 更新平均评分
        total = tool.rating * tool.rating_count + rating
        tool.rating_count += 1
        tool.rating = total / tool.rating_count
        
        self._save_catalog()
        return True
    
    def add_review(self, tool_id: str, rating: int, comment: str,
                   user: str = "anonymous") -> ToolReview:
        """添加评论"""
        review = ToolReview(
            id=self._generate_id(f"{tool_id}_{user}_{time.time()}"),
            tool_id=tool_id,
            user=user,
            rating=rating,
            comment=comment
        )
        
        if tool_id not in self._reviews:
            self._reviews[tool_id] = []
        self._reviews[tool_id].append(review)
        
        self._save_catalog()
        return review
    
    def get_reviews(self, tool_id: str) -> List[ToolReview]:
        """获取评论"""
        return self._reviews.get(tool_id, [])
    
    def download_tool(self, tool_id: str) -> Optional[str]:
        """下载工具"""
        tool = self._tools.get(tool_id)
        if not tool:
            return None
        
        tool.downloads += 1
        self._save_catalog()
        
        # 返回工具代码路径
        code_path = self.data_dir / "tools" / f"{tool_id}.py"
        if code_path.exists():
            self._downloaded[tool_id] = str(code_path)
            return str(code_path)
        
        return None
    
    def get_downloaded_tool(self, tool_id: str) -> Optional[str]:
        """获取已下载工具的代码"""
        if tool_id in self._downloaded:
            path = self._downloaded[tool_id]
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def get_categories(self) -> Dict[str, int]:
        """获取分类列表"""
        return {
            cat: len(tools) 
            for cat, tools in self._categories.items()
        }
    
    def get_recommendations(self, tool_id: str, limit: int = 5) -> List[ToolInfo]:
        """获取推荐工具"""
        tool = self._tools.get(tool_id)
        if not tool:
            return []
        
        # 基于标签和分类推荐
        candidates = []
        for t in self._tools.values():
            if t.id == tool_id:
                continue
            
            score = 0
            if t.category == tool.category:
                score += 2
            score += len(set(t.tags) & set(tool.tags))
            
            if score > 0:
                candidates.append((score, t))
        
        candidates.sort(key=lambda x: (-x[0], -x[1].rating))
        return [t for _, t in candidates[:limit]]
    
    def _generate_id(self, name: str) -> str:
        """生成工具 ID"""
        return hashlib.md5(f"{name}_{time.time()}".encode()).hexdigest()[:12]


# 全局实例
_marketplace: Optional[ToolMarketplace] = None


def get_marketplace() -> ToolMarketplace:
    """获取工具市场实例"""
    global _marketplace
    if _marketplace is None:
        _marketplace = ToolMarketplace()
    return _marketplace


# 工具注册装饰器
def register_tool(name: str, category: str = "general", tags: List[str] = None):
    """工具注册装饰器"""
    def decorator(cls):
        cls._tool_info = ToolInfo(
            id="",
            name=name,
            description=cls.__doc__ or "",
            category=category,
            tags=tags or [],
            version=getattr(cls, '__version__', '1.0.0')
        )
        return cls
    return decorator
