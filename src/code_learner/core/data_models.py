"""核心数据模型定义

定义系统中使用的所有数据结构和类型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class Function:
    """函数信息数据模型"""
    name: str
    code: str
    start_line: int
    end_line: int
    file_path: str
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    calls: List[str] = field(default_factory=list)  # 调用的其他函数
    called_by: List[str] = field(default_factory=list)  # 被哪些函数调用
    
    def __post_init__(self):
        """数据验证"""
        if self.start_line < 0:
            raise ValueError("start_line must be non-negative")
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        if not self.name.strip():
            raise ValueError("function name cannot be empty")


@dataclass
class FileInfo:
    """文件信息数据模型"""
    path: str
    name: str
    size: int
    last_modified: datetime
    functions: List[Function] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)  # #include 依赖
    
    @classmethod
    def from_path(cls, file_path: Path) -> 'FileInfo':
        """从文件路径创建FileInfo"""
        stat = file_path.stat()
        return cls(
            path=str(file_path),
            name=file_path.name,
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime)
        )


@dataclass
class ParsedCode:
    """解析后的代码结构"""
    file_info: FileInfo
    functions: List[Function]
    ast_data: Optional[Dict[str, Any]] = None  # 原始AST数据
    
    def get_function_by_name(self, name: str) -> Optional[Function]:
        """根据名称查找函数"""
        for func in self.functions:
            if func.name == name:
                return func
        return None
    
    def get_function_calls(self) -> Dict[str, List[str]]:
        """获取函数调用关系图"""
        return {func.name: func.calls for func in self.functions}


@dataclass
class EmbeddingData:
    """向量嵌入数据模型"""
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not self.id.strip():
            raise ValueError("embedding id cannot be empty")
        if not self.text.strip():
            raise ValueError("embedding text cannot be empty")
        if not self.embedding:
            raise ValueError("embedding vector cannot be empty")


@dataclass
class QueryResult:
    """查询结果数据模型"""
    question: str
    answer: str
    confidence: float
    sources: List[Dict[str, Any]] = field(default_factory=list)
    context: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class AnalysisSession:
    """分析会话数据模型"""
    id: str
    project_path: str
    status: str  # 'running', 'completed', 'failed'
    started_at: datetime
    completed_at: Optional[datetime] = None
    files_processed: int = 0
    functions_found: int = 0
    errors: List[str] = field(default_factory=list)
    
    def mark_completed(self):
        """标记会话完成"""
        self.status = 'completed'
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str):
        """标记会话失败"""
        self.status = 'failed'
        self.completed_at = datetime.now()
        self.errors.append(error)
    
    def add_progress(self, files_count: int, functions_count: int):
        """更新进度"""
        self.files_processed += files_count
        self.functions_found += functions_count


# 类型别名
FunctionCallGraph = Dict[str, List[str]]
EmbeddingVector = List[float]
MetadataDict = Dict[str, Any] 