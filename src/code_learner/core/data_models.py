"""核心数据模型定义

定义系统中使用的所有数据结构和类型
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

# 配置相关数据模型
@dataclass
class DatabaseConfig:
    """数据库配置"""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # 必须通过环境变量 NEO4J_PASSWORD 提供
    neo4j_database: str = "neo4j"
    sqlite_path: str = "./data/metadata.db"


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "code_embeddings"


@dataclass
class LLMConfig:
    """LLM配置"""
    embedding_model_name: str = "jinaai/jina-embeddings-v2-base-code"
    embedding_cache_dir: str = "~/.cache/torch/sentence_transformers/"
    embedding_batch_size: int = 32

    chat_api_key: str = ""
    chat_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    chat_model: str = "google/gemini-2.0-flash-001"
    chat_max_tokens: int = 8192
    chat_temperature: float = 1.0
    chat_top_p: float = 0.95


@dataclass
class ParserConfig:
    """解析器配置"""
    tree_sitter_language: str = "c"
    include_patterns: list = None
    exclude_patterns: list = None
    max_file_size: int = 10485760  # 10MB
    encoding: str = "utf-8"

    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = ["*.c", "*.h"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["*test*", "*example*", "*.bak"]


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/code_learner.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    cache_enabled: bool = True
    cache_ttl: int = 3600
    cache_max_size: int = 1000
    embedding_batch_size: int = 32
    parsing_batch_size: int = 10


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "C语言智能代码分析调试工具"
    version: str = "0.1.0"
    data_dir: str = "./data"
    logs_dir: str = "./logs"
    cache_dir: str = "./cache"
    debug: bool = False
    verbose: bool = False


@dataclass
class Config:
    """完整配置"""
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    llm: LLMConfig
    parser: ParserConfig
    logging: LoggingConfig
    performance: PerformanceConfig
    app: AppConfig
    enhanced_query: EnhancedQueryConfig
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """从字典创建配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            Config: 配置对象
        """
        database_config = DatabaseConfig()
        vector_store_config = VectorStoreConfig()
        llm_config = LLMConfig()
        parser_config = ParserConfig()
        logging_config = LoggingConfig()
        performance_config = PerformanceConfig()
        app_config = AppConfig()
        enhanced_query_config = EnhancedQueryConfig()
        
        # 解析数据库配置
        if "database" in config_dict:
            for key, value in config_dict["database"].items():
                if hasattr(database_config, key):
                    setattr(database_config, key, value)
        
        # 解析向量存储配置
        if "vector_store" in config_dict:
            for key, value in config_dict["vector_store"].items():
                if hasattr(vector_store_config, key):
                    setattr(vector_store_config, key, value)
        
        # 解析LLM配置
        if "llm" in config_dict:
            for key, value in config_dict["llm"].items():
                if hasattr(llm_config, key):
                    setattr(llm_config, key, value)
        
        # 解析解析器配置
        if "parser" in config_dict:
            for key, value in config_dict["parser"].items():
                if hasattr(parser_config, key):
                    setattr(parser_config, key, value)
        
        # 解析日志配置
        if "logging" in config_dict:
            for key, value in config_dict["logging"].items():
                if hasattr(logging_config, key):
                    setattr(logging_config, key, value)
        
        # 解析性能配置
        if "performance" in config_dict:
            for key, value in config_dict["performance"].items():
                if hasattr(performance_config, key):
                    setattr(performance_config, key, value)
        
        # 解析应用配置
        if "app" in config_dict:
            for key, value in config_dict["app"].items():
                if hasattr(app_config, key):
                    setattr(app_config, key, value)
        
        # 解析增强查询配置
        if "enhanced_query" in config_dict:
            for key, value in config_dict["enhanced_query"].items():
                if hasattr(enhanced_query_config, key):
                    setattr(enhanced_query_config, key, value)
        
        return cls(
            database=database_config,
            vector_store=vector_store_config,
            llm=llm_config,
            parser=parser_config,
            logging=logging_config,
            performance=performance_config,
            app=app_config,
            enhanced_query=enhanced_query_config
        )


@dataclass
class Function:
    """函数信息数据模型 - 扩展版本支持调用关系分析"""
    name: str
    code: str
    start_line: int
    end_line: int
    file_path: str
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    calls: List[str] = field(default_factory=list)  # 调用的其他函数
    called_by: List[str] = field(default_factory=list)  # 被哪些函数调用
    
    # Story 2.1.2 新增字段
    complexity_score: Optional[float] = None  # 复杂度评分
    is_static: bool = False  # 是否为静态函数
    is_inline: bool = False  # 是否为内联函数
    docstring: Optional[str] = None  # 函数文档字符串
    parameter_types: List[str] = field(default_factory=list)  # 参数类型列表
    local_variables: List[str] = field(default_factory=list)  # 局部变量
    macro_calls: List[str] = field(default_factory=list)  # 宏调用
    call_contexts: Dict[str, List[str]] = field(default_factory=dict)  # 调用上下文
    
    def __post_init__(self):
        """数据验证"""
        if self.start_line < 0:
            raise ValueError("start_line must be non-negative")
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        if not self.name.strip():
            raise ValueError("function name cannot be empty")
    
    def add_call(self, callee: str, context: str = ""):
        """添加函数调用关系
        
        Args:
            callee: 被调用函数名
            context: 调用上下文代码
        """
        if callee not in self.calls:
            self.calls.append(callee)
        
        if callee not in self.call_contexts:
            self.call_contexts[callee] = []
        if context and context not in self.call_contexts[callee]:
            self.call_contexts[callee].append(context)
    
    def add_caller(self, caller: str):
        """添加调用者关系
        
        Args:
            caller: 调用者函数名
        """
        if caller not in self.called_by:
            self.called_by.append(caller)
    
    def get_call_count(self) -> int:
        """获取调用其他函数的数量"""
        return len(self.calls)
    
    def get_caller_count(self) -> int:
        """获取被调用次数"""
        return len(self.called_by)
    
    def is_leaf_function(self) -> bool:
        """判断是否为叶子函数（不调用其他函数）"""
        return len(self.calls) == 0
    
    def is_entry_function(self) -> bool:
        """判断是否为入口函数（不被其他函数调用）"""
        return len(self.called_by) == 0
    
    def get_lines_of_code(self) -> int:
        """获取函数代码行数"""
        return self.end_line - self.start_line + 1
    
    def calculate_complexity_score(self) -> float:
        """计算函数复杂度评分"""
        if self.complexity_score is not None:
            return self.complexity_score
        
        # 简单的复杂度计算：基于代码行数和调用关系
        loc = self.get_lines_of_code()
        call_count = self.get_call_count()
        
        # 基础复杂度：代码行数 * 0.1
        base_complexity = loc * 0.1
        
        # 调用复杂度：调用函数数量 * 0.2
        call_complexity = call_count * 0.2
        
        # 总复杂度
        total_complexity = base_complexity + call_complexity
        
        self.complexity_score = round(total_complexity, 2)
        return self.complexity_score


@dataclass
class FileInfo:
    """文件信息数据模型 - 扩展版本支持多维度文件分析"""
    path: str
    name: str
    size: int
    last_modified: datetime
    functions: List[Function] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)  # #include 依赖
    
    # Story 2.1.2 新增字段
    file_type: str = "c"  # 文件类型：c, h, cpp, etc.
    encoding: str = "utf-8"  # 文件编码
    line_count: int = 0  # 总行数
    code_lines: int = 0  # 代码行数（非空非注释）
    comment_lines: int = 0  # 注释行数
    blank_lines: int = 0  # 空行数
    macro_definitions: List[str] = field(default_factory=list)  # 宏定义
    struct_definitions: List[str] = field(default_factory=list)  # 结构体定义
    global_variables: List[str] = field(default_factory=list)  # 全局变量
    typedefs: List[str] = field(default_factory=list)  # 类型定义
    header_comments: List[str] = field(default_factory=list)  # 文件头注释
    semantic_category: Optional[str] = None  # 语义分类
    
    @classmethod
    def from_path(cls, file_path: Path) -> 'FileInfo':
        """从文件路径创建FileInfo"""
        stat = file_path.stat()
        file_type = file_path.suffix.lstrip('.').lower() if file_path.suffix else 'unknown'
        
        return cls(
            path=str(file_path),
            name=file_path.name,
            size=stat.st_size,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            file_type=file_type
        )
    
    def add_function(self, function: Function):
        """添加函数信息"""
        if function not in self.functions:
            self.functions.append(function)
    
    def get_function_by_name(self, name: str) -> Optional[Function]:
        """根据名称查找函数"""
        for func in self.functions:
            if func.name == name:
                return func
        return None
    
    def get_function_count(self) -> int:
        """获取函数数量"""
        return len(self.functions)
    
    def get_total_loc(self) -> int:
        """获取总代码行数"""
        return sum(func.get_lines_of_code() for func in self.functions)
    
    def get_average_function_complexity(self) -> float:
        """获取平均函数复杂度"""
        if not self.functions:
            return 0.0
        
        total_complexity = sum(func.calculate_complexity_score() for func in self.functions)
        return round(total_complexity / len(self.functions), 2)
    
    def get_include_dependencies(self) -> List[str]:
        """获取include依赖列表"""
        return self.includes.copy()
    
    def calculate_file_metrics(self) -> Dict[str, Any]:
        """计算文件指标"""
        return {
            'function_count': self.get_function_count(),
            'total_loc': self.get_total_loc(),
            'average_complexity': self.get_average_function_complexity(),
            'include_count': len(self.includes),
            'macro_count': len(self.macro_definitions),
            'struct_count': len(self.struct_definitions),
            'global_var_count': len(self.global_variables),
            'file_size_kb': round(self.size / 1024, 2),
            'code_density': round(self.code_lines / max(self.line_count, 1), 2)
        }


@dataclass
class ParsedCode:
    """解析后的代码结构 - 扩展版本支持高级分析功能"""
    file_info: FileInfo
    functions: List[Function]
    ast_data: Optional[Dict[str, Any]] = None  # 原始AST数据
    
    # Story 2.1.2 新增字段
    parsing_time: float = 0.0  # 解析耗时（秒）
    parsing_method: str = "tree_sitter"  # 解析方法：tree_sitter, regex_fallback
    error_count: int = 0  # 解析错误数量
    warnings: List[str] = field(default_factory=list)  # 解析警告
    call_relationships: List[FunctionCall] = field(default_factory=list)  # 函数调用关系
    
    def get_function_by_name(self, name: str) -> Optional[Function]:
        """根据名称查找函数"""
        for func in self.functions:
            if func.name == name:
                return func
        return None
    
    def get_function_calls(self) -> Dict[str, List[str]]:
        """获取函数调用关系图"""
        return {func.name: func.calls for func in self.functions}
    
    def add_function_call_relationship(self, caller: str, callee: str, call_type: str, 
                                     line_number: int, context: str = ""):
        """添加函数调用关系
        
        Args:
            caller: 调用者函数名
            callee: 被调用函数名
            call_type: 调用类型
            line_number: 调用行号
            context: 调用上下文
        """
        call_rel = FunctionCall(
            caller_name=caller,
            callee_name=callee,
            call_type=call_type,
            line_number=line_number,
            file_path=self.file_info.path,
            context=context
        )
        self.call_relationships.append(call_rel)
        
        # 同时更新Function对象的调用关系
        caller_func = self.get_function_by_name(caller)
        if caller_func:
            caller_func.add_call(callee, context)
        
        callee_func = self.get_function_by_name(callee)
        if callee_func:
            callee_func.add_caller(caller)
    
    def get_call_relationships_by_caller(self, caller: str) -> List[FunctionCall]:
        """获取指定函数的所有调用关系"""
        return [call for call in self.call_relationships if call.caller_name == caller]
    
    def get_call_relationships_by_callee(self, callee: str) -> List[FunctionCall]:
        """获取调用指定函数的所有关系"""
        return [call for call in self.call_relationships if call.callee_name == callee]
    
    def get_function_call_graph(self) -> Dict[str, List[str]]:
        """获取函数调用图（基于call_relationships）"""
        call_graph = {}
        for call in self.call_relationships:
            if call.caller_name not in call_graph:
                call_graph[call.caller_name] = []
            if call.callee_name not in call_graph[call.caller_name]:
                call_graph[call.caller_name].append(call.callee_name)
        return call_graph
    
    def find_entry_functions(self) -> List[Function]:
        """查找入口函数（不被其他函数调用）"""
        all_callees = {call.callee_name for call in self.call_relationships}
        return [func for func in self.functions if func.name not in all_callees]
    
    def find_leaf_functions(self) -> List[Function]:
        """查找叶子函数（不调用其他函数）"""
        all_callers = {call.caller_name for call in self.call_relationships}
        return [func for func in self.functions if func.name not in all_callers]
    
    def calculate_cyclomatic_complexity(self) -> Dict[str, float]:
        """计算环形复杂度（简化版本）"""
        complexity_map = {}
        for func in self.functions:
            complexity_map[func.name] = func.calculate_complexity_score()
        return complexity_map
    
    def get_parsing_summary(self) -> Dict[str, Any]:
        """获取解析摘要"""
        return {
            'file_path': self.file_info.path,
            'file_size': self.file_info.size,
            'function_count': len(self.functions),
            'call_relationship_count': len(self.call_relationships),
            'parsing_time': self.parsing_time,
            'parsing_method': self.parsing_method,
            'error_count': self.error_count,
            'warning_count': len(self.warnings),
            'entry_function_count': len(self.find_entry_functions()),
            'leaf_function_count': len(self.find_leaf_functions())
        }
    
    def validate_call_relationships(self) -> List[str]:
        """验证调用关系的一致性"""
        validation_errors = []
        
        for call in self.call_relationships:
            # 检查调用者是否存在
            if not self.get_function_by_name(call.caller_name):
                validation_errors.append(f"Caller function '{call.caller_name}' not found in functions list")
            
            # 检查被调用者是否在同一文件中定义（可选检查）
            if not self.get_function_by_name(call.callee_name):
                # 这可能是外部函数调用，记录为信息而非错误
                pass
        
        return validation_errors


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


@dataclass
class ChatMessage:
    """聊天消息数据模型"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """数据验证"""
        if self.role not in ['system', 'user', 'assistant']:
            raise ValueError("role must be 'system', 'user', or 'assistant'")
        if not self.content.strip():
            raise ValueError("message content cannot be empty")


@dataclass
class ChatResponse:
    """聊天响应数据模型"""
    content: str
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """数据验证"""
        if not self.content.strip():
            raise ValueError("response content cannot be empty")
        if not self.model.strip():
            raise ValueError("model name cannot be empty")


# 类型别名
FunctionCallGraph = Dict[str, List[str]]
EmbeddingVector = List[float]
MetadataDict = Dict[str, Any]

# Story 2.1 新增数据模型

@dataclass
class FunctionCall:
    """函数调用关系数据模型"""
    caller_name: str
    callee_name: str
    call_type: str  # 'direct', 'pointer', 'member', 'recursive'
    line_number: int
    file_path: str
    context: str  # 调用上下文代码片段
    
    def __post_init__(self):
        """数据验证"""
        if not self.caller_name.strip():
            raise ValueError("caller_name cannot be empty")
        if not self.callee_name.strip():
            raise ValueError("callee_name cannot be empty")
        if self.call_type not in ['direct', 'pointer', 'member', 'recursive']:
            raise ValueError("call_type must be one of: direct, pointer, member, recursive")
        if self.line_number < 1:
            raise ValueError("line_number must be positive")


@dataclass  
class FallbackStats:
    """Fallback统计信息数据模型"""
    total_functions: int = 0
    treesitter_success: int = 0
    regex_fallback: int = 0
    fallback_reasons: Dict[str, int] = field(default_factory=dict)
    processing_times: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_success(self, processing_time: float):
        """记录成功解析"""
        self.total_functions += 1
        self.treesitter_success += 1
        self.processing_times.append(processing_time)
    
    def add_fallback(self, reason: str, processing_time: float):
        """记录fallback使用"""
        self.total_functions += 1
        self.regex_fallback += 1
        if reason not in self.fallback_reasons:
            self.fallback_reasons[reason] = 0
        self.fallback_reasons[reason] += 1
        self.processing_times.append(processing_time)
    
    @property
    def fallback_rate(self) -> float:
        """计算fallback使用率"""
        if self.total_functions == 0:
            return 0.0
        return self.regex_fallback / self.total_functions
    
    @property
    def average_processing_time(self) -> float:
        """计算平均处理时间"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)


@dataclass
class FolderInfo:
    """文件夹信息数据模型"""
    path: str
    name: str
    level: int
    file_count: int
    c_file_count: int
    h_file_count: int
    semantic_category: str  # 'core', 'driver', 'lib', 'test', 'util', etc.
    
    def __post_init__(self):
        """数据验证"""
        if not self.path.strip():
            raise ValueError("folder path cannot be empty")
        if self.level < 0:
            raise ValueError("folder level must be non-negative")
        if self.file_count < 0:
            raise ValueError("file_count must be non-negative")


@dataclass
class FolderStructure:
    """文件夹结构数据模型"""
    folders: List[FolderInfo] = field(default_factory=list)
    files: List[FileInfo] = field(default_factory=list)
    naming_patterns: Dict[str, int] = field(default_factory=dict)
    
    def add_folder(self, folder_info: FolderInfo):
        """添加文件夹信息"""
        self.folders.append(folder_info)
    
    def add_file(self, file_info: FileInfo):
        """添加文件信息"""
        self.files.append(file_info)
    
    def get_folders_by_category(self, category: str) -> List[FolderInfo]:
        """根据语义分类获取文件夹"""
        return [folder for folder in self.folders if folder.semantic_category == category]


@dataclass
class Documentation:
    """文档信息数据模型"""
    readme_files: Dict[str, str] = field(default_factory=dict)
    file_comments: Dict[str, List[str]] = field(default_factory=dict)
    api_docs: List[str] = field(default_factory=list)
    
    def add_readme(self, filename: str, content: str):
        """添加README文件内容"""
        self.readme_files[filename] = content
    
    def add_comments(self, filename: str, comments: List[str]):
        """添加文件注释"""
        self.file_comments[filename] = comments
    
    def get_all_text(self) -> str:
        """获取所有文档文本"""
        all_text = []
        for content in self.readme_files.values():
            all_text.append(content)
        for comments in self.file_comments.values():
            all_text.extend(comments)
        all_text.extend(self.api_docs)
        return "\n".join(all_text)


@dataclass
class AnalysisResult:
    """多路分析结果数据模型"""
    folder_structure: FolderStructure
    documentation: Documentation
    functions: List[Function]
    call_relationships: List[FunctionCall]
    function_embeddings: List[EmbeddingData]
    doc_embeddings: List[EmbeddingData]
    fallback_stats: FallbackStats
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def get_function_calls_by_caller(self, caller_name: str) -> List[FunctionCall]:
        """获取指定函数的所有调用"""
        return [call for call in self.call_relationships if call.caller_name == caller_name]
    
    def get_function_calls_by_callee(self, callee_name: str) -> List[FunctionCall]:
        """获取调用指定函数的所有调用关系"""
        return [call for call in self.call_relationships if call.callee_name == callee_name]


@dataclass
class FileDependency:
    """文件依赖关系

    表示一个文件对另一个文件的依赖关系，主要是通过#include语句建立的依赖
    """
    source_file: str  # 源文件路径
    target_file: str  # 目标文件路径
    dependency_type: str = "include"  # 'include', 'import', 'use'
    is_system: bool = False  # 是否系统头文件
    line_number: int = 0  # 引用行号
    context: str = ""  # 上下文代码片段

    def __str__(self) -> str:
        """返回可读的依赖描述"""
        dep_type = "系统" if self.is_system else "项目"
        return f"{self.source_file} -> {self.target_file} ({dep_type}{self.dependency_type}，行 {self.line_number})"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "dependency_type": self.dependency_type,
            "is_system": self.is_system,
            "line_number": self.line_number,
            "context": self.context
        }


@dataclass
class ModuleDependency:
    """模块依赖关系

    表示一个模块对另一个模块的依赖关系，通过文件依赖聚合计算得到
    """
    source_module: str  # 源模块名称
    target_module: str  # 目标模块名称
    file_count: int = 0  # 依赖文件数量
    strength: float = 0.0  # 依赖强度(0-1)
    is_circular: bool = False  # 是否循环依赖
    files: List[Tuple[str, str]] = field(default_factory=list)  # 依赖的文件对列表 [(源文件, 目标文件), ...]

    def __str__(self) -> str:
        """返回可读的依赖描述"""
        circular = "循环依赖" if self.is_circular else ""
        return f"{self.source_module} -> {self.target_module} ({self.file_count}文件, 强度{self.strength:.2f}) {circular}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "source_module": self.source_module,
            "target_module": self.target_module,
            "file_count": self.file_count,
            "strength": self.strength,
            "is_circular": self.is_circular,
            "files": self.files
        }
    
    def add_file_dependency(self, source_file: str, target_file: str) -> None:
        """添加文件依赖关系"""
        self.files.append((source_file, target_file))
        self.file_count = len(self.files)


@dataclass
class ProjectDependencies:
    """项目依赖关系

    包含项目中所有文件和模块的依赖关系
    """
    file_dependencies: List[FileDependency] = field(default_factory=list)
    module_dependencies: List[ModuleDependency] = field(default_factory=list)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    modularity_score: float = 0.0  # 模块化评分(0-1)
    
    def add_file_dependency(self, dependency: FileDependency) -> None:
        """添加文件依赖关系"""
        self.file_dependencies.append(dependency)
    
    def add_module_dependency(self, dependency: ModuleDependency) -> None:
        """添加模块依赖关系"""
        self.module_dependencies.append(dependency)
    
    def add_circular_dependency(self, dependency_chain: List[str]) -> None:
        """添加循环依赖链"""
        self.circular_dependencies.append(dependency_chain)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取依赖统计信息"""
        return {
            "file_dependencies_count": len(self.file_dependencies),
            "module_dependencies_count": len(self.module_dependencies),
            "circular_dependencies_count": len(self.circular_dependencies),
            "system_headers_count": sum(1 for d in self.file_dependencies if d.is_system),
            "project_headers_count": sum(1 for d in self.file_dependencies if not d.is_system),
            "modularity_score": self.modularity_score
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "file_dependencies": [d.to_dict() for d in self.file_dependencies],
            "module_dependencies": [d.to_dict() for d in self.module_dependencies],
            "circular_dependencies": self.circular_dependencies,
            "modularity_score": self.modularity_score,
            "stats": self.get_stats()
        }


class EnhancedQueryConfig:
    """增强查询配置
    
    包含多源检索系统的配置
    """
    def __init__(self):
        self.enabled = True
        self.sources = {
            "vector": {
                "enable": True,
                "top_k": 5,
                "min_relevance_score": 0.0
            },
            "call_graph": {
                "enable": True,
                "top_k": 5,
                "min_relevance_score": 0.0
            },
            "dependency": {
                "enable": True,
                "top_k": 5,
                "min_relevance_score": 0.0
            }
        }
        self.final_top_k = 5
        self.rerank_enabled = True
        self.parallel_retrieval = True
        self.timeout_seconds = 30
        self.prompt_template = "default"  # rerank prompt 模板
        
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "enabled": self.enabled,
            "sources": self.sources,
            "final_top_k": self.final_top_k,
            "rerank_enabled": self.rerank_enabled,
            "parallel_retrieval": self.parallel_retrieval,
            "timeout_seconds": self.timeout_seconds,
            "prompt_template": self.prompt_template
        }
        
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "EnhancedQueryConfig":
        """从字典创建配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            EnhancedQueryConfig: 配置对象
        """
        config = cls()
        
        # 设置基本属性
        if "enabled" in config_dict:
            config.enabled = config_dict["enabled"]
            
        if "final_top_k" in config_dict:
            config.final_top_k = config_dict["final_top_k"]
            
        if "rerank_enabled" in config_dict:
            config.rerank_enabled = config_dict["rerank_enabled"]
            
        if "parallel_retrieval" in config_dict:
            config.parallel_retrieval = config_dict["parallel_retrieval"]
            
        if "timeout_seconds" in config_dict:
            config.timeout_seconds = config_dict["timeout_seconds"]
        
        # 设置源配置
        if "sources" in config_dict:
            # 合并源配置，保留默认值
            for source_name, source_config in config_dict["sources"].items():
                if source_name in config.sources:
                    for key, value in source_config.items():
                        config.sources[source_name][key] = value
                else:
                    # 添加新源
                    config.sources[source_name] = source_config
        
        # 读取prompt_template
        if "prompt_template" in config_dict:
            config.prompt_template = config_dict["prompt_template"]
        
        return config


class EmbeddingConfig:
    """嵌入配置
    
    包含嵌入模型的配置
    """
    def __init__(self):
        self.model_name = "jinaai/jina-embeddings-v2-base-code"
        self.cache_dir = None
        self.batch_size = 32
        self.dimensions = 768 