"""核心接口定义

定义系统中各个组件的抽象接口，遵循SOLID原则中的接口隔离原则
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Protocol
from pathlib import Path

from .data_models import (
    Function, FileInfo, ParsedCode, EmbeddingData, 
    QueryResult, FunctionCallGraph, EmbeddingVector,
    FunctionCall, FallbackStats, FolderStructure, 
    Documentation, AnalysisResult, FileDependency, ModuleDependency,
    ProjectDependencies
)


class IParser(Protocol):
    """解析器接口"""
    
    def parse_file(self, file_path: Path) -> ParsedCode:
        """解析单个文件"""
        ...
    
    def parse_directory(self, directory_path: Path, file_pattern: str = "*.c") -> List[ParsedCode]:
        """解析目录中的所有匹配文件"""
        ...
    
    def extract_function_calls(self, function_code: str) -> List[FunctionCall]:
        """提取函数调用关系"""
        ...

    def extract_file_dependencies(self, file_path: Path) -> List[FileDependency]:
        """提取文件依赖关系（主要是#include语句）
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[FileDependency]: 文件依赖关系列表
        """
        ...
    
    def analyze_project_dependencies(self, project_path: Path) -> ProjectDependencies:
        """分析项目依赖关系
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectDependencies: 项目依赖关系
        """
        ...


class IGraphStore(Protocol):
    """图存储接口"""
    
    def connect(self, uri: str, user: str, password: str) -> bool:
        """连接到图数据库"""
        ...
    
    def close(self) -> bool:
        """关闭连接"""
        ...
    
    def clear_database(self) -> bool:
        """清空数据库"""
        ...
    
    def store_parsed_code(self, parsed_code: ParsedCode) -> bool:
        """存储解析后的代码"""
        ...
    
    def query_function(self, function_name: str) -> Optional[Dict[str, Any]]:
        """查询函数"""
        ...
    
    def query_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """查询文件"""
        ...
    
    def store_call_relationship(self, caller_name: str, callee_name: str, call_type: str = "direct", 
                              line_no: int = 0, context: str = "") -> bool:
        """存储函数调用关系"""
        ...
    
    def query_call_graph(self, root_function: str, max_depth: int = 5) -> Dict[str, Any]:
        """生成函数调用图谱"""
        ...

    def store_file_dependencies(self, dependencies: List[FileDependency]) -> bool:
        """存储文件依赖关系
        
        Args:
            dependencies: 文件依赖关系列表
            
        Returns:
            bool: 是否成功
        """
        ...
    
    def store_module_dependencies(self, dependencies: List[ModuleDependency]) -> bool:
        """存储模块依赖关系
        
        Args:
            dependencies: 模块依赖关系列表
            
        Returns:
            bool: 是否成功
        """
        ...
    
    def query_file_dependencies(self, file_path: str = None) -> List[Dict[str, Any]]:
        """查询文件依赖关系
        
        Args:
            file_path: 文件路径，如果为None则查询所有文件依赖
            
        Returns:
            List[Dict[str, Any]]: 文件依赖关系列表
        """
        ...
    
    def query_module_dependencies(self, module_name: str = None) -> List[Dict[str, Any]]:
        """查询模块依赖关系
        
        Args:
            module_name: 模块名称，如果为None则查询所有模块依赖
            
        Returns:
            List[Dict[str, Any]]: 模块依赖关系列表
        """
        ...
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖
        
        Returns:
            List[List[str]]: 循环依赖链列表
        """
        ...


class IVectorStore(ABC):
    """向量数据库存储接口
    
    负责存储和检索代码的向量嵌入，支持多模态分析
    """
    
    @abstractmethod
    def create_collection(self, name: str) -> bool:
        """创建向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 创建是否成功
        """
        pass
    
    @abstractmethod
    def add_embeddings(self, embeddings: List[EmbeddingData]) -> bool:
        """批量添加向量嵌入
        
        Args:
            embeddings: 嵌入数据列表
            
        Returns:
            bool: 添加是否成功
        """
        pass
    
    @abstractmethod
    def search_similar(self, query_vector: EmbeddingVector, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 相似结果列表
        """
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """删除向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    # Story 2.1 新增方法
    @abstractmethod
    def store_function_embeddings(self, functions: List[Function]) -> bool:
        """存储函数向量嵌入
        
        Args:
            functions: 函数列表
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def store_documentation_embeddings(self, documentation: Documentation) -> bool:
        """存储文档向量嵌入
        
        Args:
            documentation: 文档信息
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """语义搜索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        pass


class IEmbeddingEngine(ABC):
    """嵌入生成引擎接口
    
    负责生成代码的向量嵌入，支持repo级别批量处理
    """
    
    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """加载嵌入模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 加载是否成功
        """
        pass
    
    @abstractmethod
    def encode_text(self, text: str) -> EmbeddingVector:
        """编码文本为向量
        
        Args:
            text: 输入文本
            
        Returns:
            EmbeddingVector: 向量嵌入
        """
        pass
    
    @abstractmethod
    def encode_function(self, function: Function) -> EmbeddingData:
        """编码函数为向量嵌入
        
        Args:
            function: 函数对象
            
        Returns:
            EmbeddingData: 嵌入数据
        """
        pass
    
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """批量编码文本 - repo级别必需
        
        Args:
            texts: 文本列表
            
        Returns:
            List[EmbeddingVector]: 向量列表
        """
        pass


class IChatBot(ABC):
    """聊天机器人接口
    
    负责与LLM交互，回答用户问题
    """
    
    @abstractmethod
    def initialize(self, api_key: str, model: str) -> bool:
        """初始化聊天机器人
        
        Args:
            api_key: API密钥
            model: 模型名称
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def ask_question(self, question: str, context: List[str]) -> QueryResult:
        """询问问题
        
        Args:
            question: 用户问题
            context: 上下文信息
            
        Returns:
            QueryResult: 查询结果
        """
        pass
    
    @abstractmethod
    def generate_summary(self, code: str) -> str:
        """生成代码摘要 - 用户明确需要的功能
        
        Args:
            code: 源代码
            
        Returns:
            str: 代码摘要
        """
        pass


class ICodeQAService(ABC):
    """代码问答服务接口
    
    整合所有组件，提供统一的问答服务
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化服务
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def embed_and_store_code(self, parsed_code: ParsedCode) -> bool:
        """嵌入并存储代码
        
        Args:
            parsed_code: 解析后的代码
            
        Returns:
            bool: 处理是否成功
        """
        pass
    
    @abstractmethod
    def ask_question(self, question: str) -> str:
        """询问关于代码的问题
        
        Args:
            question: 用户问题
            
        Returns:
            str: 答案
        """
        pass


# Story 2.1 新增接口

class IMultiModalAnalysisStrategy(ABC):
    """多路分析策略接口
    
    整合Tree-sitter、Neo4j、Chroma和文档分析的多路分析架构
    """
    
    @abstractmethod
    def analyze_repository(self, repo_path: Path) -> AnalysisResult:
        """分析代码仓库
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            AnalysisResult: 多路分析结果
        """
        pass
    
    @abstractmethod
    def analyze_folder_structure(self, repo_path: Path) -> FolderStructure:
        """分析文件夹结构
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            FolderStructure: 文件夹结构信息
        """
        pass
    
    @abstractmethod
    def extract_documentation(self, repo_path: Path) -> Documentation:
        """提取文档信息
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            Documentation: 文档信息
        """
        pass
    
    @abstractmethod
    def structured_analysis(self, repo_path: Path) -> List[Function]:
        """结构化代码分析
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            List[Function]: 函数列表
        """
        pass
    
    @abstractmethod
    def semantic_analysis(self, repo_path: Path) -> List[EmbeddingData]:
        """语义向量分析
        
        Args:
            repo_path: 仓库路径
            
        Returns:
            List[EmbeddingData]: 向量嵌入列表
        """
        pass


class IRAGRetrievalStrategy(ABC):
    """RAG召回策略接口
    
    实现混合召回策略，结合语义和结构化检索
    """
    
    @abstractmethod
    def retrieve_context(self, query: str) -> str:
        """检索上下文信息
        
        Args:
            query: 查询文本
            
        Returns:
            str: 检索到的上下文
        """
        pass
    
    @abstractmethod
    def semantic_retrieval(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """语义检索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            List[Dict]: 语义检索结果
        """
        pass
    
    @abstractmethod
    def structural_retrieval(self, query: str) -> List[Dict[str, Any]]:
        """结构化检索
        
        Args:
            query: 查询文本
            
        Returns:
            List[Dict]: 结构化检索结果
        """
        pass
    
    @abstractmethod
    def merge_retrieval_results(self, semantic_results: List[Dict], 
                              structural_results: List[Dict]) -> str:
        """融合检索结果
        
        Args:
            semantic_results: 语义检索结果
            structural_results: 结构化检索结果
            
        Returns:
            str: 融合后的上下文
        """
        pass


class IMetaDataStore(ABC):
    """元数据存储接口
    
    用于存储fallback统计、性能指标等元数据信息
    """
    
    @abstractmethod
    def store_fallback_stats(self, stats: FallbackStats) -> bool:
        """存储fallback统计信息
        
        Args:
            stats: fallback统计数据
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def store_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """存储性能指标
        
        Args:
            metrics: 性能指标数据
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def get_fallback_report(self) -> Dict[str, Any]:
        """获取fallback使用报告
        
        Returns:
            Dict[str, Any]: fallback报告数据
        """
        pass
    
    @abstractmethod
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能总结
        
        Returns:
            Dict[str, Any]: 性能总结数据
        """
        pass


# 添加新接口
class ICallGraphService(Protocol):
    """函数调用图谱服务接口"""
    
    def analyze_file(self, file_path: Path) -> List[FunctionCall]:
        """分析文件中的函数调用关系
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[FunctionCall]: 函数调用关系列表
        """
        ...
    
    def analyze_project(self, project_path: Path) -> Dict[str, List[FunctionCall]]:
        """分析项目中的函数调用关系
        
        Args:
            project_path: 项目路径
            
        Returns:
            Dict[str, List[FunctionCall]]: 按文件分组的函数调用关系
        """
        ...
    
    def generate_call_graph(self, root_function: str, max_depth: int = 5, 
                          output_format: str = "mermaid") -> str:
        """生成函数调用图
        
        Args:
            root_function: 根函数名
            max_depth: 最大深度
            output_format: 输出格式（mermaid, json, ascii, html）
            
        Returns:
            str: 调用图
        """
        ...
    
    def export_call_graph(self, root_function: str, output_path: Path, 
                        output_format: str = "mermaid") -> bool:
        """导出函数调用图
        
        Args:
            root_function: 根函数名
            output_path: 输出路径
            output_format: 输出格式
            
        Returns:
            bool: 导出是否成功
        """
        ...


class IDependencyService(Protocol):
    """依赖关系分析服务接口"""
    
    def analyze_file(self, file_path: Path) -> List[FileDependency]:
        """分析文件依赖关系
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[FileDependency]: 文件依赖关系列表
        """
        ...
    
    def analyze_project(self, project_path: Path) -> ProjectDependencies:
        """分析项目依赖关系
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectDependencies: 项目依赖关系
        """
        ...
    
    def generate_dependency_graph(self, output_format: str = "mermaid", 
                                scope: str = "module", focus_item: str = None) -> str:
        """生成依赖图
        
        Args:
            output_format: 输出格式（mermaid, json, ascii, html）
            scope: 作用域（file, module）
            focus_item: 聚焦项（文件路径或模块名）
            
        Returns:
            str: 依赖图
        """
        ...
    
    def export_dependency_graph(self, output_path: Path, output_format: str = "mermaid", 
                              scope: str = "module", focus_item: str = None) -> bool:
        """导出依赖图
        
        Args:
            output_path: 输出路径
            output_format: 输出格式
            scope: 作用域
            focus_item: 聚焦项
            
        Returns:
            bool: 导出是否成功
        """
        ...
    
    def get_circular_dependencies(self) -> List[List[str]]:
        """获取循环依赖
        
        Returns:
            List[List[str]]: 循环依赖链列表
        """
        ... 