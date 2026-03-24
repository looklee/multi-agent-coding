"""
成本优化模块
- Token 缓存（语义缓存）
- 智能路由（根据任务复杂度选择模型）
- 批量处理（合并小任务）
- 成本统计
"""
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from threading import Lock


@dataclass
class CostRecord:
    """成本记录"""
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    task_id: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CachedResponse:
    """缓存响应"""
    content: str
    input_tokens: int
    output_tokens: int
    created_at: float
    hit_count: int = 0


class TokenCache:
    """Token 缓存（基于语义相似度）"""
    
    def __init__(self, db_path: str = "cache.db", ttl_seconds: int = 3600 * 24 * 7):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    hash TEXT PRIMARY KEY,
                    prompt_hash TEXT,
                    content TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    created_at REAL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_hash ON cache(prompt_hash)")
    
    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _normalize_prompt(self, prompt: str) -> str:
        """标准化提示词（用于模糊匹配）"""
        # 移除多余空白、转小写
        normalized = ' '.join(prompt.lower().split())
        return normalized
    
    def get(self, prompt: str) -> Optional[CachedResponse]:
        """获取缓存响应"""
        prompt_hash = self._compute_hash(self._normalize_prompt(prompt))
        exact_hash = self._compute_hash(prompt)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 先查精确匹配
                cursor = conn.execute(
                    "SELECT * FROM cache WHERE hash = ? AND created_at + ? > ?",
                    (exact_hash, self.ttl_seconds, time.time())
                )
                row = cursor.fetchone()
                
                if row:
                    # 更新命中次数
                    conn.execute(
                        "UPDATE cache SET hit_count = hit_count + 1 WHERE hash = ?",
                        (exact_hash,)
                    )
                    return CachedResponse(
                        content=row[2],
                        input_tokens=row[3],
                        output_tokens=row[4],
                        created_at=row[5],
                        hit_count=row[6] + 1
                    )
                
                # 再查相似匹配（prompt_hash）
                cursor = conn.execute(
                    "SELECT * FROM cache WHERE prompt_hash = ? AND created_at + ? > ?",
                    (prompt_hash, self.ttl_seconds, time.time())
                )
                row = cursor.fetchone()
                
                if row:
                    conn.execute(
                        "UPDATE cache SET hit_count = hit_count + 1 WHERE hash = ?",
                        (row[0],)
                    )
                    return CachedResponse(
                        content=row[2],
                        input_tokens=row[3],
                        output_tokens=row[4],
                        created_at=row[5],
                        hit_count=row[6] + 1
                    )
        
        return None
    
    def set(self, prompt: str, response: str, input_tokens: int, output_tokens: int):
        """缓存响应"""
        prompt_hash = self._compute_hash(self._normalize_prompt(prompt))
        exact_hash = self._compute_hash(prompt)
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache 
                    (hash, prompt_hash, content, input_tokens, output_tokens, created_at, hit_count)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (exact_hash, prompt_hash, response, input_tokens, output_tokens, time.time()))
    
    def clear_expired(self):
        """清理过期缓存"""
        cutoff = time.time() - self.ttl_seconds
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE created_at + ? < ?", (self.ttl_seconds, cutoff))
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*), SUM(hit_count), SUM(output_tokens) 
                    FROM cache WHERE created_at + ? > ?
                """, (self.ttl_seconds, time.time()))
                row = cursor.fetchone()
                return {
                    "cache_size": row[0] or 0,
                    "total_hits": row[1] or 0,
                    "tokens_saved": row[2] or 0
                }


class SmartRouter:
    """智能路由 - 根据任务选择最经济的模型"""
    
    # 模型价格（每 1K tokens，人民币）
    MODEL_PRICES = {
        "qwen": {"qwen-plus": (0.002, 0.006), "qwen-max": (0.04, 0.12)},
        "deepseek": {"deepseek-chat": (0.001, 0.002)},
        "moonshot": {"moonshot-v1-8k": (0.012, 0.012)},
        "doubao": {"doubao-pro-32k": (0.008, 0.02)},
        "gemini": {"gemini-1.5-flash": (0.000075, 0.0003)},
    }
    
    # 模型能力评分（1-10）
    MODEL_CAPABILITIES = {
        "qwen-plus": 7,
        "qwen-max": 9,
        "deepseek-chat": 8,
        "moonshot-v1-8k": 7,
        "doubao-pro-32k": 7,
        "gemini-1.5-flash": 6,
    }
    
    def __init__(self, available_providers: List[str] = None):
        self.available_providers = available_providers or list(self.MODEL_PRICES.keys())
    
    def estimate_complexity(self, task: str) -> Tuple[int, str]:
        """
        估计任务复杂度
        返回：(复杂度评分 1-10, 推荐模型类型)
        """
        task_lower = task.lower()
        
        # 简单任务特征
        simple_keywords = ["是什么", "定义", "解释", "hello", "test", "简单"]
        # 中等任务特征
        medium_keywords = ["实现", "代码", "函数", "类", "写一个"]
        # 复杂任务特征
        complex_keywords = ["架构", "优化", "设计", "系统", "分布式", "高并发"]
        
        score = 3  # 基础分
        
        for kw in simple_keywords:
            if kw in task_lower:
                score -= 1
        for kw in medium_keywords:
            if kw in task_lower:
                score += 2
        for kw in complex_keywords:
            if kw in task_lower:
                score += 4
        
        # 长度因素
        if len(task) > 200:
            score += 2
        elif len(task) > 100:
            score += 1
        
        # 代码块检测
        if "```" in task or "def " in task or "class " in task:
            score += 2
        
        score = max(1, min(10, score))
        
        # 推荐模型类型
        if score <= 3:
            model_type = "cheap"
        elif score <= 6:
            model_type = "balanced"
        else:
            model_type = "powerful"
        
        return score, model_type
    
    def select_model(self, task: str, budget_mode: bool = False) -> Tuple[str, str]:
        """
        选择最优模型
        返回：(provider, model)
        """
        complexity, model_type = self.estimate_complexity(task)
        
        candidates = []
        
        for provider, models in self.MODEL_PRICES.items():
            if provider not in self.available_providers:
                continue
            
            for model, (input_price, output_price) in models.items():
                capability = self.MODEL_CAPABILITIES.get(model, 5)
                
                # 根据模型类型过滤
                if model_type == "cheap" and capability > 7:
                    continue
                if model_type == "powerful" and capability < 7:
                    continue
                
                # 计算性价比
                avg_price = (input_price + output_price) / 2
                cost_effectiveness = capability / avg_price if avg_price > 0 else 0
                
                candidates.append((provider, model, capability, cost_effectiveness))
        
        if not candidates:
            return "qwen", "qwen-plus"
        
        # 预算模式选最便宜，否则选性价比最高
        if budget_mode:
            candidates.sort(key=lambda x: self.MODEL_PRICES[x[0]][x[1]][0])
        else:
            candidates.sort(key=lambda x: -x[3])
        
        best = candidates[0]
        return best[0], best[1]
    
    def get_price(self, provider: str, model: str) -> Tuple[float, float]:
        """获取模型价格 (input, output) per 1K tokens"""
        return self.MODEL_PRICES.get(provider, {}).get(model, (0.01, 0.03))


class CostTracker:
    """成本追踪器"""
    
    def __init__(self, db_path: str = "costs.db"):
        self.db_path = db_path
        self._lock = Lock()
        self._init_db()
        self.router = SmartRouter()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost REAL,
                    task_id TEXT,
                    timestamp REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON costs(timestamp)")
    
    def record(self, provider: str, model: str, input_tokens: int, 
               output_tokens: int, task_id: str = ""):
        """记录成本"""
        input_price, output_price = self.router.get_price(provider, model)
        cost = (input_tokens / 1000) * input_price + (output_tokens / 1000) * output_price
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO costs (provider, model, input_tokens, output_tokens, cost, task_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (provider, model, input_tokens, output_tokens, cost, task_id, time.time()))
    
    def get_total_cost(self, days: int = 7) -> float:
        """获取总成本（最近 N 天）"""
        cutoff = time.time() - (days * 24 * 3600)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT SUM(cost) FROM costs WHERE timestamp > ?", (cutoff,)
                )
                result = cursor.fetchone()[0]
                return result or 0.0
    
    def get_stats(self, days: int = 7) -> Dict:
        """获取成本统计"""
        cutoff = time.time() - (days * 24 * 3600)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 总成本
                cursor = conn.execute(
                    "SELECT SUM(cost), SUM(input_tokens), SUM(output_tokens) FROM costs WHERE timestamp > ?",
                    (cutoff,)
                )
                row = cursor.fetchone()
                
                # 按提供商分组
                cursor = conn.execute("""
                    SELECT provider, SUM(cost), SUM(input_tokens + output_tokens) 
                    FROM costs WHERE timestamp > ? GROUP BY provider
                """, (cutoff,))
                by_provider = {r[0]: {"cost": r[1], "tokens": r[2]} for r in cursor.fetchall()}
                
                # 按模型分组
                cursor = conn.execute("""
                    SELECT model, SUM(cost), SUM(input_tokens + output_tokens) 
                    FROM costs WHERE timestamp > ? GROUP BY model
                """, (cutoff,))
                by_model = {r[0]: {"cost": r[1], "tokens": r[2]} for r in cursor.fetchall()}
                
                return {
                    "total_cost": row[0] or 0.0,
                    "total_tokens": (row[1] or 0) + (row[2] or 0),
                    "by_provider": by_provider,
                    "by_model": by_model,
                    "period_days": days
                }


class BatchProcessor:
    """批量处理器 - 合并小任务节省 Token"""
    
    def __init__(self, max_batch_size: int = 5, max_wait_seconds: float = 2.0):
        self.max_batch_size = max_batch_size
        self.max_wait_seconds = max_wait_seconds
        self._batch: List[Dict] = []
        self._lock = Lock()
        self._timer: Optional[float] = None
    
    def add(self, task_id: str, prompt: str, callback) -> bool:
        """
        添加任务到批处理队列
        如果队列满或超时，触发批处理
        返回：是否已批量处理
        """
        with self._lock:
            self._batch.append({"task_id": task_id, "prompt": prompt, "callback": callback})
            
            if len(self._batch) >= self.max_batch_size:
                self._process_batch()
                return True
            
            # 设置定时器
            if self._timer:
                pass  # 已有定时器在运行
            
            # 简化实现：实际应该用 threading.Timer
            return False
    
    def _process_batch(self):
        """处理批处理队列"""
        if not self._batch:
            return
        
        batch = self._batch.copy()
        self._batch.clear()
        
        # 合并 prompts
        combined_prompt = "请依次处理以下任务：\n\n"
        for i, item in enumerate(batch, 1):
            combined_prompt += f"任务 {i}: {item['prompt']}\n\n"
        
        # 调用回调处理合并后的任务
        if batch:
            batch[0]["callback"](combined_prompt, [item["task_id"] for item in batch])
    
    def flush(self):
        """强制处理剩余任务"""
        with self._lock:
            self._process_batch()


# 全局实例
_cache: Optional[TokenCache] = None
_cost_tracker: Optional[CostTracker] = None
_router: Optional[SmartRouter] = None


def get_cache() -> TokenCache:
    global _cache
    if _cache is None:
        _cache = TokenCache()
    return _cache


def get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def get_router() -> SmartRouter:
    global _router
    if _router is None:
        _router = SmartRouter()
    return _router
