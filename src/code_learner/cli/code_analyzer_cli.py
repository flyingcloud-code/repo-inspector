#!/usr/bin/env python3
"""
C语言智能代码分析调试工具 - CLI工具

提供实用的命令行工具，直接处理实际C代码项目（如OpenSBI），
支持代码分析、查询、状态检查和导出功能。
"""

import argparse
import sys
import os
import time
import json
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import hashlib

from tqdm import tqdm

from ..config.config_manager import ConfigManager
from ..parser.c_parser import CParser
from ..storage.neo4j_store import Neo4jGraphStore
from ..llm.service_factory import ServiceFactory
from ..core.exceptions import StorageError, ParseError, ConfigurationError
from ..utils.logger import get_logger
from ..llm.code_qa_service import CodeQAService
from ..llm.code_embedder import CodeEmbedder
from ..llm.code_chunker import CodeChunker

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """代码分析器 - 处理实际C代码项目"""
    
    def __init__(self, project_path: Path, output_dir: Optional[Path] = None,
               include_pattern: str = "*.c,*.h", exclude_pattern: str = None,
               threads: int = 4, project_id: Optional[str] = None):
        """初始化代码分析器
        
        Args:
            project_path: 项目路径
            output_dir: 输出目录，默认为项目路径下的.analysis目录
            include_pattern: 包含的文件模式，逗号分隔
            exclude_pattern: 排除的文件模式，逗号分隔
            threads: 并行处理线程数
            project_id: 项目ID，用于项目隔离
        """
        self.project_path = project_path
        self.output_dir = output_dir or project_path / ".analysis"
        self.include_pattern = include_pattern.split(",") if include_pattern else ["*.c", "*.h"]
        self.exclude_pattern = exclude_pattern.split(",") if exclude_pattern else []
        self.threads = threads
        
        # 生成项目ID（如果未提供）
        if project_id is None:
            project_id = self._generate_project_id(project_path)
        self.project_id = project_id
        
        # 初始化解析器
        self.parser = CParser()
        
        # 初始化存储（带项目隔离）
        config = ConfigManager().get_config()
        self.graph_store = Neo4jGraphStore(project_id=self.project_id)
        self.graph_store.connect(
            config.database.neo4j_uri,
            config.database.neo4j_user,
            config.database.neo4j_password
        )
        
        # 初始化嵌入相关组件
        self.service_factory = ServiceFactory()
        self.embedding_engine = self.service_factory.get_embedding_engine()
        self.vector_store = self.service_factory.create_vector_store(project_id=self.project_id)
        self.code_chunker = CodeChunker()
        self.code_embedder = CodeEmbedder(
            embedding_engine=self.embedding_engine,
            vector_store=self.vector_store
        )
        
        # 初始化其他服务
        self.dependency_service = ServiceFactory.get_dependency_service()
        self.call_graph_service = ServiceFactory.get_call_graph_service()
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"代码分析器初始化完成，项目ID: {self.project_id}")
    
    def _generate_project_id(self, project_path: Path) -> str:
        """生成项目ID
        
        Args:
            project_path: 项目路径
            
        Returns:
            str: 项目ID
        """
        abs_path = str(project_path.resolve())
        hash_value = hashlib.md5(abs_path.encode()).hexdigest()[:8]
        return f"auto_{hash_value}"
    
    def analyze(self, incremental: bool = False, generate_embeddings: bool = True) -> Dict[str, Any]:
        """分析项目
        
        Args:
            incremental: 是否进行增量分析
            generate_embeddings: 是否生成向量嵌入
            
        Returns:
            Dict[str, Any]: 分析结果统计
        """
        start_time = time.time()
        
        # 获取所有匹配的文件
        files = self._get_target_files(incremental)
        total_files = len(files)
        
        print(f"开始分析项目: {self.project_path}")
        print(f"项目ID: {self.project_id}")
        print(f"目标文件数: {total_files}")
        
        # 使用线程池并行处理
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self._process_file, file): file for file in files}
            
            # 显示进度
            with tqdm(total=total_files, desc="分析进度") as pbar:
                for future in concurrent.futures.as_completed(futures):
                    file = futures[future]
                    try:
                        result = future.result()
                        if result:  # 只添加成功的结果
                            results.append(result)
                    except Exception as e:
                        print(f"处理文件 {file} 时出错: {e}")
                    finally:
                        pbar.update(1)
        
        # 构建依赖关系
        print("分析文件间依赖关系...")
        project_deps = self.dependency_service.analyze_project(self.project_path)
        
        # 生成向量嵌入
        embedding_stats = {}
        if generate_embeddings:
            print("生成向量嵌入...")
            embedding_stats = self._generate_embeddings(results)
        
        # 保存分析结果
        self._save_analysis_results(results, project_deps)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 返回统计信息
        stats = {
            "project_id": self.project_id,
            "total_files": total_files,
            "processed_files": len(results),
            "total_functions": sum(len(r.functions) for r in results if r),
            "file_dependencies": len(project_deps.file_dependencies),
            "module_dependencies": len(project_deps.module_dependencies),
            "circular_dependencies": len(project_deps.circular_dependencies),
            "elapsed_time": elapsed,
            "embeddings": embedding_stats
        }
        
        print(f"分析完成，耗时: {elapsed:.2f}秒")
        print(f"共处理 {stats['processed_files']} 个文件，发现 {stats['total_functions']} 个函数")
        if generate_embeddings and embedding_stats:
            print(f"生成嵌入向量: {embedding_stats.get('total_chunks', 0)} 个代码块")
        
        return stats
    
    def _get_target_files(self, incremental: bool) -> List[Path]:
        """获取需要处理的文件
        
        Args:
            incremental: 是否进行增量分析
            
        Returns:
            List[Path]: 文件路径列表
        """
        all_files = []
        
        # 遍历项目目录
        for pattern in self.include_pattern:
            all_files.extend(self.project_path.glob(f"**/{pattern}"))
        
        # 应用排除模式
        if self.exclude_pattern:
            filtered_files = []
            for file in all_files:
                exclude = False
                rel_path = file.relative_to(self.project_path)
                for pattern in self.exclude_pattern:
                    if Path(str(rel_path)).match(pattern):
                        exclude = True
                        break
                if not exclude:
                    filtered_files.append(file)
            all_files = filtered_files
        
        # 增量分析 - 只处理修改过的文件
        if incremental:
            # 获取已处理文件的最后修改时间
            processed_files = {}
            try:
                cache_file = self.output_dir / "processed_files.json"
                if cache_file.exists():
                    with open(cache_file, 'r') as f:
                        processed_files = json.load(f)
            except Exception as e:
                logger.warning(f"无法加载已处理文件缓存: {e}")
            
            # 只保留修改过的文件
            filtered_files = []
            for file in all_files:
                mtime = file.stat().st_mtime
                if str(file) not in processed_files or mtime > processed_files[str(file)]:
                    filtered_files.append(file)
            
            print(f"增量分析: 共 {len(filtered_files)}/{len(all_files)} 个文件需要处理")
            all_files = filtered_files
        
        return all_files
    
    def _process_file(self, file_path: Path):
        """处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[ParsedCode]: 解析结果
        """
        try:
            # 解析文件
            parsed_code = self.parser.parse_file(file_path)
            
            # 存储到图数据库
            self.graph_store.store_parsed_code(parsed_code)
            
            # 更新处理文件缓存
            self._update_processed_file_cache(file_path)
            
            return parsed_code
        except Exception as e:
            logger.error(f"处理文件 {file_path} 失败: {e}")
            return None
    
    def _update_processed_file_cache(self, file_path: Path):
        """更新处理文件缓存
        
        Args:
            file_path: 文件路径
        """
        cache_file = self.output_dir / "processed_files.json"
        processed_files = {}
        
        # 加载现有缓存
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    processed_files = json.load(f)
            except Exception:
                pass
        
        # 更新缓存
        processed_files[str(file_path)] = file_path.stat().st_mtime
        
        # 保存缓存
        try:
            with open(cache_file, 'w') as f:
                json.dump(processed_files, f)
        except Exception as e:
            logger.warning(f"无法更新处理文件缓存: {e}")
    
    def _save_analysis_results(self, results, project_deps):
        """保存分析结果
        
        Args:
            results: 解析结果列表
            project_deps: 项目依赖关系
        """
        # 保存函数列表
        functions_file = self.output_dir / "functions.json"
        functions_data = []
        for result in results:
            for func in result.functions:
                functions_data.append({
                    "name": func.name,
                    "file_path": func.file_path,
                    "start_line": func.start_line,
                    "end_line": func.end_line,
                    "calls": func.calls
                })
        
        with open(functions_file, 'w') as f:
            json.dump(functions_data, f, indent=2)
        
        # 保存依赖关系
        deps_file = self.output_dir / "dependencies.json"
        with open(deps_file, 'w') as f:
            json.dump(project_deps.to_dict(), f, indent=2)
        
        # 保存分析摘要
        summary_file = self.output_dir / "summary.md"
        with open(summary_file, 'w') as f:
            f.write(f"# 项目分析摘要: {self.project_path.name}\n\n")
            f.write(f"分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 文件统计\n\n")
            f.write(f"- 总文件数: {len(results)}\n")
            f.write(f"- 总函数数: {sum(len(r.functions) for r in results)}\n")
            f.write(f"- 文件依赖数: {len(project_deps.file_dependencies)}\n")
            f.write(f"- 模块依赖数: {len(project_deps.module_dependencies)}\n")
            
            if project_deps.circular_dependencies:
                f.write("\n## 循环依赖\n\n")
                for i, cycle in enumerate(project_deps.circular_dependencies):
                    f.write(f"{i+1}. {' -> '.join(cycle)}\n")
        
        print(f"分析结果已保存到: {self.output_dir}")
    
    def _generate_embeddings(self, results: List[Any]) -> Dict[str, Any]:
        """生成向量嵌入
        
        Args:
            results: 解析结果列表
            
        Returns:
            Dict[str, Any]: 嵌入统计信息
        """
        try:
            # 确保嵌入引擎已加载模型
            if not self.embedding_engine.model:
                print("加载嵌入模型...")
                self.embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
            
            # 收集所有已处理的文件进行分块
            all_chunks = []
            total_functions = 0
            processed_files = set()
            
            for result in results:
                if not result or not hasattr(result, 'functions'):
                    continue
                    
                # 获取文件路径 - ParsedCode对象有file_info属性
                file_path = None
                if hasattr(result, 'file_info') and result.file_info and hasattr(result.file_info, 'path'):
                    file_path = str(result.file_info.path)
                elif hasattr(result, 'functions') and result.functions and result.functions[0].file_path:
                    # 备用方案：从第一个函数获取文件路径
                    file_path = result.functions[0].file_path
                
                if file_path and file_path not in processed_files:
                    processed_files.add(file_path)
                    
                    # 使用tree-sitter对整个文件进行语义分块
                    try:
                        file_chunks = self.code_chunker.chunk_file_by_tree_sitter(file_path)
                        all_chunks.extend(file_chunks)
                        print(f"文件 {file_path} 生成了 {len(file_chunks)} 个代码块")
                    except Exception as e:
                        logger.warning(f"文件 {file_path} tree-sitter分块失败，回退到按大小分块: {e}")
                        # 回退到按大小分块
                        file_chunks = self.code_chunker.chunk_file_by_size(file_path)
                        all_chunks.extend(file_chunks)
                        print(f"文件 {file_path} 按大小分块生成了 {len(file_chunks)} 个代码块")
                
                # 统计函数数量
                if hasattr(result, 'functions'):
                    total_functions += len(result.functions)
            
            print(f"从 {len(processed_files)} 个文件，{total_functions} 个函数生成了 {len(all_chunks)} 个代码块")
            
            if not all_chunks:
                print("没有代码块需要嵌入")
                return {"total_chunks": 0, "total_functions": total_functions, "total_files": len(processed_files)}
            
            # 使用项目特定的集合名称
            collection_name = "code_embeddings"
            
            # 批量生成嵌入
            success = self.code_embedder.embed_code_chunks(all_chunks, collection_name)
            
            if success:
                print(f"✅ 成功生成 {len(all_chunks)} 个嵌入向量")
                return {
                    "total_chunks": len(all_chunks),
                    "total_functions": total_functions,
                    "total_files": len(processed_files),
                    "collection_name": self.vector_store.get_collection_name(collection_name),
                    "success": True
                }
            else:
                print("❌ 嵌入生成失败")
                return {
                    "total_chunks": 0,
                    "total_functions": total_functions,
                    "total_files": len(processed_files),
                    "success": False
                }
                
        except Exception as e:
            logger.error(f"生成嵌入时出错: {e}", exc_info=True)
            print(f"❌ 嵌入生成出错: {e}")
            return {"error": str(e), "success": False}


class InteractiveQuerySession:
    """交互式问答会话 - 直接针对实际代码库"""
    
    def __init__(self, project_path: Path, history_file: Optional[Path] = None,
               focus_function: Optional[str] = None, focus_file: Optional[str] = None):
        """初始化交互式问答会话
        
        Args:
            project_path: 项目路径
            history_file: 历史记录文件
            focus_function: 聚焦的函数
            focus_file: 聚焦的文件
        """
        self.project_path = project_path
        self.history_file = history_file
        self.focus_function = focus_function
        self.focus_file = focus_file
        
        # 根据项目路径生成项目ID
        abs_path = str(project_path.resolve())
        self.project_id = "auto_" + hashlib.md5(abs_path.encode()).hexdigest()[:8]
        
        # 创建带项目ID的问答服务
        self.qa_service = CodeQAService(project_id=self.project_id)
        self.history = []
        
        # 加载历史记录
        if history_file and history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"无法加载历史记录: {e}")
    
    def start(self, direct_query=None):
        """启动交互式问答会话或执行直接查询
        
        Args:
            direct_query: 直接执行的查询，不进入交互模式
        """
        focus_info = ""
        if self.focus_function:
            focus_info = f"函数: {self.focus_function}"
        elif self.focus_file:
            focus_info = f"文件: {self.focus_file}"
            
        print(f"代码问答会话 - 项目: {self.project_path} {focus_info}")
        
        # 如果提供了直接查询，执行后退出
        if direct_query:
            try:
                # 构建上下文
                context = {
                    "project_path": str(self.project_path),
                    "focus_function": self.focus_function,
                    "focus_file": self.focus_file
                }
                
                print(f"查询: {direct_query}")
                print("处理中...")
                answer = self.qa_service.ask_question(direct_query, context)
                
                # 显示答案
                print(f"\n{answer}\n")
                
                # 保存到历史记录
                self.history.append({"question": direct_query, "answer": answer})
                
                # 保存历史记录
                if self.history_file:
                    try:
                        with open(self.history_file, "w") as f:
                            json.dump(self.history, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"无法保存历史记录: {e}")
                
                return
            except Exception as e:
                print(f"\n错误: {e}")
                return
        
        # 交互模式
        print("输入'exit'或'quit'退出，输入'help'获取帮助\n")
        
        while True:
            try:
                # 使用简单的输入提示
                question = input("> ")
                
                if question.lower() in ["exit", "quit"]:
                    break
                elif question.lower() == "help":
                    self._print_help()
                    continue
                
                # 构建上下文
                context = {
                    "project_path": str(self.project_path),
                    "focus_function": self.focus_function,
                    "focus_file": self.focus_file
                }
                
                # 调用问答服务
                print("处理中...")
                answer = self.qa_service.ask_question(question, context)
                
                # 显示答案
                print(f"\n{answer}\n")
                
                # 保存到历史记录
                self.history.append({"question": question, "answer": answer})
                
            except KeyboardInterrupt:
                print("\n会话已中断")
                break
            except Exception as e:
                print(f"\n错误: {e}")
        
        # 保存历史记录
        if self.history_file:
            try:
                with open(self.history_file, "w") as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"无法保存历史记录: {e}")
        
        print("会话已结束")
    
    def _print_help(self):
        """打印帮助信息"""
        help_text = """
可用命令:
  exit, quit - 退出会话
  help       - 显示此帮助

示例问题:
  - 函数X的作用是什么？
  - 哪些函数调用了函数Y？
  - 文件Z中定义了哪些函数？
  - 项目中有哪些循环依赖？
  - 哪个模块依赖最多？
  - 文件A和文件B之间的依赖关系是什么？
"""
        print(help_text)


def check_system_status(verbose: bool = False) -> Dict[str, Any]:
    """检查系统状态
    
    检查Neo4j、Chroma、LLM服务等组件的状态
    
    Args:
        verbose: 是否显示详细信息
        
    Returns:
        Dict[str, Any]: 状态信息
    """
    print("检查系统状态...")
    
    # 确保.env文件被加载
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
    import os
    
    status = {
        "neo4j": {"status": "unknown"},
        "chroma": {"status": "unknown"},
        "llm": {"status": "unknown"}
    }
    
    # 检查Neo4j连接
    try:
        print("检查Neo4j连接...")
        graph_store = ServiceFactory.get_graph_store()
        node_count = graph_store.count_nodes()
        rel_count = graph_store.count_relationships()
        
        status["neo4j"] = {
            "status": "healthy" if node_count > 0 else "warning",
            "nodes": node_count,
            "relationships": rel_count,
            "uri": graph_store.uri
        }
        
        if verbose:
            # 获取更详细的Neo4j信息
            print("获取Neo4j详细信息...")
            node_types = graph_store.get_node_types()
            rel_types = graph_store.get_relationship_types()
            
            status["neo4j"]["node_types"] = node_types
            status["neo4j"]["relationship_types"] = rel_types
            
            # 获取函数和文件统计
            function_count = graph_store.count_nodes_by_label("Function")
            file_count = graph_store.count_nodes_by_label("File")
            
            status["neo4j"]["function_count"] = function_count
            status["neo4j"]["file_count"] = file_count
        
        print(f"Neo4j状态: {'✅' if status['neo4j']['status'] == 'healthy' else '⚠️'}")
        print(f"  - 节点数: {node_count:,}")
        print(f"  - 关系数: {rel_count:,}")
        
    except Exception as e:
        status["neo4j"] = {"status": "error", "message": str(e)}
        print(f"Neo4j连接错误: {e}")
    
    # 检查Chroma向量数据库
    try:
        print("检查Chroma向量数据库...")
        factory = ServiceFactory()
        vector_store = factory.get_vector_store()
        
        collections = vector_store.list_collections()
        collection_details = {}
        total_chunks = 0
        
        for collection_name in collections:
            try:
                count = vector_store.count_documents(collection_name)
                collection_details[collection_name] = count
                total_chunks += count
            except Exception:
                collection_details[collection_name] = "error"
        
        status["chroma"] = {
            "status": "healthy" if collections else "warning",
            "collections": len(collections),
            "collection_names": collections,
            "total_chunks": total_chunks
        }
        
        if verbose:
            # 获取更详细的集合信息
            print("获取Chroma详细信息...")
            status["chroma"]["collection_details"] = collection_details
            
            # 获取一个示例chunk的metadata
            if collections and total_chunks > 0:
                try:
                    sample_collection = collections[0]
                    sample_results = vector_store.query_embeddings(
                        query_vector=[0.0] * 768,  # 假设向量维度为768
                        n_results=1,
                        collection_name=sample_collection
                    )
                    if sample_results:
                        status["chroma"]["sample_metadata"] = sample_results[0].get("metadata", {})
                except Exception as e:
                    status["chroma"]["sample_error"] = str(e)
        
        print(f"Chroma状态: {'✅' if status['chroma']['status'] == 'healthy' else '⚠️'}")
        print(f"  - 集合数: {len(collections)}")
        print(f"  - 总chunks数: {total_chunks:,}")
        
    except Exception as e:
        status["chroma"] = {"status": "error", "message": str(e)}
        print(f"Chroma连接错误: {e}")
    
    # 检查嵌入模型
    try:
        print("检查嵌入模型...")
        embedding_engine = ServiceFactory.get_embedding_engine()
        model_info = {
            "name": embedding_engine.model_name,
            "dimensions": embedding_engine.get_dimensions(),
            "device": embedding_engine.device
        }
        
        status["embedding"] = {
            "status": "healthy" if embedding_engine.model else "error",
            "model": model_info
        }
        
        print(f"嵌入模型状态: {'✅' if status['embedding']['status'] == 'healthy' else '⚠️'}")
        print(f"  - 模型: {model_info['name']}")
        print(f"  - 维度: {model_info['dimensions']}")
        
    except Exception as e:
        status["embedding"] = {"status": "error", "message": str(e)}
        print(f"嵌入模型错误: {e}")
    
    # 检查LLM服务
    try:
        print("检查LLM服务...")
        # 直接检查环境变量
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("❌ OPENROUTER_API_KEY未设置或为空")
            status["llm"] = {
                "status": "error",
                "message": "OPENROUTER_API_KEY未设置"
            }
        else:
            chatbot = ServiceFactory.get_chatbot()
            model_info = {
                "model": chatbot.model_name,
                "max_tokens": chatbot.max_tokens
            }
            
            # 只检查配置，不实际调用API
            status["llm"] = {
                "status": "configured",
                "model": model_info,
                "api_key": api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
            }
            
            print(f"LLM服务状态: ✅")
            print(f"  - 模型: {model_info['model']}")
            print(f"  - API密钥: {len(api_key) if len(api_key) > 10 else '***'}")
        
    except Exception as e:
        status["llm"] = {"status": "error", "message": str(e)}
        print(f"LLM服务错误: {e}")
    
    # 检查多源检索系统状态
    try:
        print("检查多源检索系统...")
        
        # 检查配置
        config = ConfigManager().get_config()
        enhanced_query_enabled = config.enhanced_query.enabled
        
        retrieval_sources = []
        if config.enhanced_query.sources["vector"]["enabled"]:
            retrieval_sources.append("vector")
        if config.enhanced_query.sources["call_graph"]["enabled"]:
            retrieval_sources.append("call_graph")
        if config.enhanced_query.sources["dependency"]["enabled"]:
            retrieval_sources.append("dependency")
        
        status["enhanced_query"] = {
            "status": "enabled" if enhanced_query_enabled else "disabled",
            "sources": retrieval_sources,
            "rerank_enabled": config.enhanced_query.rerank_enabled,
            "final_top_k": config.enhanced_query.final_top_k
        }
        
        print(f"多源检索系统: {'✅' if enhanced_query_enabled else '⚠️'}")
        print(f"  - 启用的源: {', '.join(retrieval_sources)}")
        print(f"  - Rerank: {'启用' if config.enhanced_query.rerank_enabled else '禁用'}")
        
    except Exception as e:
        status["enhanced_query"] = {"status": "error", "message": str(e)}
        print(f"多源检索系统错误: {e}")
    
    # 总体状态
    all_healthy = all(
        component["status"] in ["healthy", "configured"] 
        for component in [status["neo4j"], status["chroma"], status["embedding"], status["llm"]]
    )
    
    status["overall"] = "healthy" if all_healthy else "warning"
    
    print()
    print(f"系统总体状态: {'✅ 健康' if all_healthy else '⚠️ 警告'}")
    
    return status


def analyze_code(project_path: str, output_dir: str = None, incremental: bool = False,
               include_pattern: str = None, exclude_pattern: str = None,
               threads: int = None, verbose: bool = False, project_id: str = None) -> Dict[str, Any]:
    """分析代码
    
    封装代码分析功能，方便其他模块调用
    
    Args:
        project_path: 项目路径
        output_dir: 输出目录
        incremental: 是否进行增量分析
        include_pattern: 包含的文件模式
        exclude_pattern: 排除的文件模式
        threads: 并行处理线程数
        verbose: 是否显示详细日志
        project_id: 项目ID，用于数据隔离
        
    Returns:
        Dict[str, Any]: 分析结果统计
    """
    # 设置日志级别
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 转换路径
    project_path = Path(project_path)
    if not project_path.exists() or not project_path.is_dir():
        raise ValueError(f"项目路径不存在: {project_path}")
    
    output_dir = Path(output_dir) if output_dir else None
    
    # 创建分析器
    analyzer = CodeAnalyzer(
        project_path=project_path,
        output_dir=output_dir,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        threads=threads or 4,
        project_id=project_id
    )
    
    # 执行分析
    stats = analyzer.analyze(incremental=incremental, generate_embeddings=True)
    
    return stats


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器
    """
    parser = argparse.ArgumentParser(
        description="C语言智能代码分析调试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # analyze命令 - 分析C代码项目
    analyze_parser = subparsers.add_parser("analyze", help="分析C代码项目")
    analyze_parser.add_argument("project_path", help="项目路径")
    analyze_parser.add_argument("--output-dir", "-o", help="输出目录")
    analyze_parser.add_argument("--incremental", "-i", action="store_true", 
                              help="增量分析（只分析变更文件）")
    analyze_parser.add_argument("--include", help="包含的文件模式 (例如: '*.c,*.h')")
    analyze_parser.add_argument("--exclude", help="排除的文件模式 (例如: 'test/*')")
    analyze_parser.add_argument("--threads", "-t", type=int, default=4,
                              help="并行处理线程数")
    
    # query命令 - 交互式代码问答
    query_parser = subparsers.add_parser("query", help="交互式代码问答")
    query_parser.add_argument("--project", "-p", required=True, 
                            help="项目路径")
    query_parser.add_argument("--query", "-q", help="直接执行查询，不进入交互模式")
    query_parser.add_argument("--history", "-H", help="保存历史记录的文件")
    query_parser.add_argument("--function", "-f", help="聚焦于特定函数")
    query_parser.add_argument("--file", help="聚焦于特定文件")
    query_parser.add_argument("--verbose", "-v", action="store_true", 
                            help="显示详细日志")
    
    # status命令 - 系统状态检查
    status_parser = subparsers.add_parser("status", help="系统状态检查")
    status_parser.add_argument("--verbose", "-v", action="store_true", 
                             help="显示详细信息")
    
    # export命令 - 导出分析结果
    export_parser = subparsers.add_parser("export", help="导出分析结果")
    export_parser.add_argument("--project", "-p", required=True, 
                            help="项目路径")
    export_parser.add_argument("--format", "-f", choices=["json", "md", "html", "dot"],
                            default="json", help="导出格式")
    export_parser.add_argument("--output", "-o", required=True,
                            help="输出文件路径")
    export_parser.add_argument("--type", "-t", choices=["calls", "deps", "all"],
                            default="all", help="导出数据类型")
    
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """主函数
    
    Args:
        argv: 命令行参数，默认为None（使用sys.argv）
        
    Returns:
        int: 退出码
    """
    if argv is None:
        argv = sys.argv[1:]
    
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        return 1
    
    # 设置日志级别
    logger = get_logger(__name__)
    
    try:
        if args.command == "analyze":
            # 分析项目
            project_path = Path(args.project_path)
            if not project_path.exists() or not project_path.is_dir():
                print(f"错误: 项目路径不存在: {project_path}")
                return 1
            
            output_dir = Path(args.output_dir) if args.output_dir else None
            
            analyzer = CodeAnalyzer(
                project_path=project_path,
                output_dir=output_dir,
                include_pattern=args.include,
                exclude_pattern=args.exclude,
                threads=args.threads
            )
            
            analyzer.analyze(incremental=args.incremental, generate_embeddings=True)
            return 0
        
        elif args.command == "query":
            # 交互式问答
            project_path = Path(args.project)
            if not project_path.exists() or not project_path.is_dir():
                print(f"错误: 项目路径不存在: {project_path}")
                return 1
            
            history_file = Path(args.history) if args.history else None
            
            # 设置日志级别
            if args.verbose:
                logging.basicConfig(level=logging.DEBUG)
            
            session = InteractiveQuerySession(
                project_path=project_path,
                history_file=history_file,
                focus_function=args.function,
                focus_file=args.file
            )
            
            session.start(args.query)
            return 0
        
        elif args.command == "status":
            # 系统状态检查
            status = check_system_status(verbose=args.verbose)
            
            print("\n系统状态检查结果:")
            print(f"整体状态: {status['overall']}")
            print("\n组件状态:")
            
            for component, info in status.items():
                if component != "overall":
                    status_str = info.get("status", "unknown")
                    if status_str == "healthy":
                        status_emoji = "✅"
                    elif status_str == "degraded":
                        status_emoji = "⚠️"
                    elif status_str == "error" or status_str == "unhealthy":
                        status_emoji = "❌"
                    else:
                        status_emoji = "❓"
                    
                    print(f"{status_emoji} {component}: {status_str}")
                    
                    if args.verbose:
                        # 特殊处理不同组件的详细信息
                        if component == "vector_database" and "details" in info:
                            details = info["details"]
                            print(f"  - collections: {info.get('collections', 0)}")
                            print(f"  - total_chunks: {info.get('total_chunks', 0)}")
                            
                            if "chunk_distribution" in details:
                                print("  - chunk_distribution:")
                                for project_id, project_info in details["chunk_distribution"].items():
                                    print(f"    * project_{project_id}: {project_info['total_chunks']} chunks in {project_info['collections']} collections")
                            
                            if "collection_names" in details:
                                print(f"  - active_collections: {', '.join(details['collection_names'][:3])}{'...' if len(details['collection_names']) > 3 else ''}")
                        
                        elif component == "database" and "details" in info:
                            details = info["details"]
                            if details:
                                for key, value in details.items():
                                    if isinstance(value, dict):
                                        print(f"  - {key}:")
                                        for sub_key, sub_value in value.items():
                                            print(f"    * {sub_key}: {sub_value}")
                                    else:
                                        print(f"  - {key}: {value}")
                        
                        else:
                            # 默认处理其他组件
                            for key, value in info.items():
                                if key not in ["status", "error", "details"]:
                                    print(f"  - {key}: {value}")
                            
                            if "details" in info and info["details"]:
                                for detail_key, detail_value in info["details"].items():
                                    print(f"  - {detail_key}: {detail_value}")
                    
                    if "error" in info:
                        print(f"  错误: {info['error']}")
            
            return 0
        
        elif args.command == "export":
            # 导出分析结果
            project_path = Path(args.project)
            if not project_path.exists() or not project_path.is_dir():
                print(f"错误: 项目路径不存在: {project_path}")
                return 1
            
            output_path = Path(args.output)
            
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if args.type in {"calls", "all"}:
                    call_graph_service = ServiceFactory.get_call_graph_service()
                    entry_functions = call_graph_service.find_entry_functions() or ["main"]
                    main_function = entry_functions[0]
                    print(f"生成函数调用图: {main_function}")
                    call_graph_service.export_call_graph(
                        main_function,
                        output_path.with_suffix(f".calls.{args.format}"),
                        args.format
                    )
            except Exception as e:
                logger.warning(f"导出调用图失败: {e}")

            try:
                if args.type in {"deps", "all"}:
                    dependency_service = ServiceFactory.get_dependency_service()
                    print("生成依赖关系图")
                    dependency_service.export_dependency_graph(
                        output_path.with_suffix(f".deps.{args.format}"),
                        args.format
                    )
            except Exception as e:
                logger.warning(f"导出依赖关系失败: {e}")

            # 写入导出摘要到指定 output_path
            summary = {
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "project": str(project_path),
                "export_format": args.format,
                "included_types": args.type,
                "files": []
            }

            if args.type in {"calls", "all"}:
                summary["files"].append(str(output_path.with_suffix(f".calls.{args.format}")))
            if args.type in {"deps", "all"}:
                summary["files"].append(str(output_path.with_suffix(f".deps.{args.format}")))

            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    if args.format == "json":
                        json.dump(summary, f, ensure_ascii=False, indent=2)
                    else:
                        f.write("# 导出摘要\n\n")
                        for file in summary["files"]:
                            f.write(f"- {file}\n")
            except Exception as e:
                logger.error(f"无法写入导出摘要文件: {e}")
                return 1

            print(f"导出完成: {output_path}")
            return 0
        
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\n操作已取消")
        return 130
    except Exception as e:
        print(f"错误: {e}")
        logger.exception("执行过程中发生错误")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 