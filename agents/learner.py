"""
Agent 自学习模块
- 经验记忆和检索
- 反思和优化
- 行为模式学习
"""
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import sqlite3
from threading import Lock


@dataclass
class Experience:
    """经验记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""
    task_description: str = ""
    approach: str = ""
    result: str = ""
    success: bool = False
    feedback: str = ""
    rating: int = 0  # 1-5
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "task_description": self.task_description,
            "approach": self.approach,
            "result": self.result,
            "success": self.success,
            "feedback": self.feedback,
            "rating": self.rating,
            "created_at": self.created_at
        }


@dataclass
class Pattern:
    """学习到的模式"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    trigger_keywords: List[str] = field(default_factory=list)
    action_template: str = ""
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_keywords": self.trigger_keywords,
            "action_template": self.action_template,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count
        }


class ExperiencePool:
    """经验池"""
    
    def __init__(self, db_path: str = "experiences.db"):
        self.db_path = db_path
        self._lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id TEXT PRIMARY KEY,
                    task_type TEXT,
                    task_description TEXT,
                    approach TEXT,
                    result TEXT,
                    success INTEGER,
                    feedback TEXT,
                    rating INTEGER,
                    created_at REAL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    trigger_keywords TEXT,
                    action_template TEXT,
                    success_rate REAL,
                    usage_count INTEGER,
                    created_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_type ON experiences(task_type)")
    
    def add_experience(self, experience: Experience):
        """添加经验"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO experiences 
                    (id, task_type, task_description, approach, result, success, feedback, rating, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    experience.id,
                    experience.task_type,
                    experience.task_description,
                    experience.approach,
                    experience.result,
                    1 if experience.success else 0,
                    experience.feedback,
                    experience.rating,
                    experience.created_at,
                    json.dumps(experience.metadata)
                ))
    
    def search_similar(self, task_description: str, limit: int = 5) -> List[Experience]:
        """搜索相似任务的经验"""
        # 简单关键词匹配（实际可用向量数据库）
        keywords = task_description.lower().split()
        
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # 按关键词匹配度排序
                experiences = []
                cursor = conn.execute("""
                    SELECT * FROM experiences 
                    ORDER BY rating DESC, created_at DESC
                    LIMIT ?
                """, (limit * 3,))
                
                for row in cursor.fetchall():
                    desc = row[2].lower()
                    match_count = sum(1 for kw in keywords if kw in desc)
                    if match_count > 0:
                        experiences.append((match_count, row))
                
                # 按匹配度排序
                experiences.sort(key=lambda x: -x[0])
                
                # 转换为 Experience 对象
                results = []
                for _, row in experiences[:limit]:
                    exp = Experience(
                        id=row[0],
                        task_type=row[1],
                        task_description=row[2],
                        approach=row[3],
                        result=row[4],
                        success=bool(row[5]),
                        feedback=row[6],
                        rating=row[7],
                        created_at=row[8],
                        metadata=json.loads(row[9]) if row[9] else {}
                    )
                    results.append(exp)
                
                return results
    
    def get_successful_patterns(self, task_type: str = None) -> List[Pattern]:
        """获取成功模式"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM patterns 
                    WHERE success_rate > 0.7 AND usage_count >= 3
                    ORDER BY success_rate DESC
                """)
                
                patterns = []
                for row in cursor.fetchall():
                    pattern = Pattern(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        trigger_keywords=json.loads(row[3]) if row[3] else [],
                        action_template=row[4],
                        success_rate=row[5],
                        usage_count=row[6],
                        created_at=row[7]
                    )
                    if task_type is None or task_type in pattern.trigger_keywords:
                        patterns.append(pattern)
                
                return patterns
    
    def add_pattern(self, pattern: Pattern):
        """添加模式"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO patterns 
                    (id, name, description, trigger_keywords, action_template, success_rate, usage_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.id,
                    pattern.name,
                    pattern.description,
                    json.dumps(pattern.trigger_keywords),
                    pattern.action_template,
                    pattern.success_rate,
                    pattern.usage_count,
                    pattern.created_at
                ))
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM experiences")
                total_experiences = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM experiences WHERE success = 1")
                successful = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT AVG(rating) FROM experiences WHERE rating > 0")
                avg_rating = cursor.fetchone()[0] or 0
                
                cursor = conn.execute("SELECT COUNT(*) FROM patterns")
                total_patterns = cursor.fetchone()[0]
                
                return {
                    "total_experiences": total_experiences,
                    "successful_experiences": successful,
                    "success_rate": successful / total_experiences if total_experiences > 0 else 0,
                    "average_rating": avg_rating,
                    "learned_patterns": total_patterns
                }


class SelfLearner:
    """自学习器"""
    
    def __init__(self, experience_pool: ExperiencePool = None):
        self.pool = experience_pool or ExperiencePool()
        self._current_task_id: str = ""
        self._task_history: List[Dict] = []
    
    def start_task(self, task_id: str, task_description: str):
        """开始任务"""
        self._current_task_id = task_id
        self._task_history.append({
            "task_id": task_id,
            "description": task_description,
            "start_time": time.time()
        })
    
    def record_action(self, action: str, context: str = ""):
        """记录行动"""
        if self._task_history:
            self._task_history[-1].setdefault("actions", []).append({
                "action": action,
                "context": context,
                "timestamp": time.time()
            })
    
    def complete_task(self, result: str, success: bool, feedback: str = "", rating: int = 0):
        """完成任务并记录经验"""
        if not self._task_history:
            return
        
        task_record = self._task_history.pop()
        
        # 分析任务类型
        task_type = self._analyze_task_type(task_record["description"])
        
        # 创建经验记录
        experience = Experience(
            task_id=task_record["task_id"],
            task_type=task_type,
            task_description=task_record["description"],
            approach=json.dumps(task_record.get("actions", [])),
            result=result,
            success=success,
            feedback=feedback,
            rating=rating,
            metadata={
                "duration": time.time() - task_record["start_time"]
            }
        )
        
        self.pool.add_experience(experience)
        
        # 如果成功，尝试提取模式
        if success and rating >= 4:
            self._extract_pattern(experience)
        
        self._current_task_id = ""
    
    def _analyze_task_type(self, description: str) -> str:
        """分析任务类型"""
        description_lower = description.lower()
        
        task_types = {
            "code_generation": ["实现", "写一个", "创建", "generate", "implement"],
            "code_review": ["审查", "检查", "review", "audit"],
            "debugging": ["调试", "修复", "错误", "debug", "fix"],
            "optimization": ["优化", "性能", "optimize", "performance"],
            "testing": ["测试", "test", "unit test"],
            "documentation": ["文档", "注释", "document", "comment"],
        }
        
        for task_type, keywords in task_types.items():
            if any(kw in description_lower for kw in keywords):
                return task_type
        
        return "general"
    
    def _extract_pattern(self, experience: Experience):
        """从经验中提取模式"""
        try:
            actions = json.loads(experience.approach)
            if not actions:
                return
            
            # 提取关键步骤
            key_actions = [a["action"] for a in actions[:3]]  # 前 3 个步骤
            
            pattern = Pattern(
                name=f"Pattern_{experience.task_type}_{experience.id}",
                description=f"从任务 '{experience.task_description[:50]}' 中学到的模式",
                trigger_keywords=experience.task_description.lower().split()[:5],
                action_template="\n".join(key_actions),
                success_rate=experience.rating / 5.0,
                usage_count=1
            )
            
            self.pool.add_pattern(pattern)
        except:
            pass
    
    def get_suggestions(self, task_description: str) -> List[Dict]:
        """获取建议"""
        # 搜索相似经验
        experiences = self.pool.search_similar(task_description)
        
        suggestions = []
        for exp in experiences:
            suggestions.append({
                "type": "experience",
                "description": f"之前成功的做法：{exp.approach[:100]}",
                "rating": exp.rating,
                "success": exp.success
            })
        
        # 获取模式建议
        patterns = self.pool.get_successful_patterns()
        for pattern in patterns:
            suggestions.append({
                "type": "pattern",
                "name": pattern.name,
                "template": pattern.action_template,
                "success_rate": pattern.success_rate
            })
        
        return suggestions
    
    def reflect(self) -> Dict:
        """反思学习"""
        stats = self.pool.get_statistics()
        
        # 分析弱点
        weak_areas = []
        if stats["success_rate"] < 0.5:
            weak_areas.append("整体成功率较低")
        
        if stats["average_rating"] < 3:
            weak_areas.append("用户满意度有待提高")
        
        return {
            "statistics": stats,
            "weak_areas": weak_areas,
            "recommendations": self._generate_recommendations(stats)
        }
    
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if stats["total_experiences"] < 10:
            recommendations.append("积累更多使用经验以提高学习效果")
        
        if stats["success_rate"] < 0.7:
            recommendations.append("分析失败案例，优化任务处理策略")
        
        if stats["learned_patterns"] < 5:
            recommendations.append("需要更多高质量任务以学习有效模式")
        
        return recommendations


# 全局实例
_learner: Optional[SelfLearner] = None


def get_learner() -> SelfLearner:
    global _learner
    if _learner is None:
        _learner = SelfLearner()
    return _learner
