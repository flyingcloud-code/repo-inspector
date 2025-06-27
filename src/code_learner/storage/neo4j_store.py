"""
Neo4j图数据库存储实现

提供Neo4j图数据库的存储功能：
- 连接管理
- 数据存储（File和Function节点）
- 关系建立（CONTAINS关系）
- 严格错误处理（无fallback）
- 详细日志记录
"""

import logging
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError, ConfigurationError, TransientError
from pathlib import Path
import os
import time
from datetime import datetime
from dotenv import load_dotenv

from ..core.interfaces import IGraphStore
from ..core.data_models import ParsedCode, Function, FileInfo, FunctionCall, FolderStructure, FileDependency, ModuleDependency
from ..core.exceptions import StorageError
from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger

logger = logging.getLogger(__name__)


class Neo4jGraphStore(IGraphStore):
    """Neo4j图数据库存储实现
    
    严格模式：所有错误都会抛出异常，不提供fallback机制
    """

    def __init__(self):
        """初始化Neo4j图存储"""
        self.driver: Optional[Driver] = None
        self.uri = None
        self.user = None
        self.connected = False
        
        # 根据配置设置日志级别
        try:
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # 如果开启verbose模式，设置DEBUG级别
            if config.app.verbose:
                logger.setLevel(logging.DEBUG)
                logger.debug("🔧 Verbose mode enabled - setting Neo4j logger to DEBUG level")
            elif config.app.debug:
                logger.setLevel(logging.DEBUG)
                logger.debug("🔧 Debug mode enabled - setting Neo4j logger to DEBUG level")
            
            self.verbose = config.app.verbose
            self.debug = config.app.debug
            
        except Exception as e:
            # 如果配置加载失败，使用默认设置
            logger.warning(f"Failed to load config for logging setup: {e}")
            self.verbose = False
            self.debug = False
        
        logger.info("Neo4jGraphStore initialized in strict mode (no fallbacks)")
        if self.verbose:
            logger.debug("🔧 Verbose logging enabled for detailed operation tracking")

        # 加载环境变量
        load_dotenv()

    def connect(self, uri: str = None, user: str = None, password: str = None) -> bool:
        """连接到Neo4j数据库
        
        Args:
            uri: 数据库URI，如果为None则从环境变量获取
            user: 用户名，如果为None则从环境变量获取
            password: 密码，如果为None则从环境变量获取
            
        Returns:
            bool: 连接是否成功
            
        Raises:
            StorageError: 连接失败时抛出异常（无fallback）
        """
        logger.info(f"Attempting to connect to Neo4j at {uri} with user '{user}'")
        logger.debug(f"Connection config: max_pool_size=50, timeout=60s")
        
        try:
            # 如果参数为None，尝试从环境变量获取
            uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = user or os.getenv("NEO4J_USER", "neo4j")
            password = password or os.getenv("NEO4J_PASSWORD")
            
            if not password:
                logger.error("未提供Neo4j密码，请设置NEO4J_PASSWORD环境变量")
                return False
            
            # 使用上下文管理器确保资源正确释放
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(user, password),
                # 性能优化配置
                max_connection_pool_size=50,
                connection_acquisition_timeout=60.0
            )
            
            # 立即验证连接
            self.driver.verify_connectivity()
            
            self.uri = uri
            self.user = user
            self.connected = True
            
            logger.info("✅ Successfully connected to Neo4j database")
            logger.debug(f"Driver info: {self.driver}")
            
            # 初始化数据库约束
            self._initialize_constraints()
            
            return True
            
        except (ServiceUnavailable, AuthError, ConfigurationError) as e:
            error_msg = f"Neo4j connection failed: {e}"
            logger.error(f"❌ {error_msg}")
            self.driver = None
            self.connected = False
            raise StorageError("connection_failed", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected connection error: {e}"
            logger.error(f"❌ {error_msg}")
            self.driver = None
            self.connected = False
            raise StorageError("connection_error", error_msg)

    def store_parsed_code(self, parsed_code: ParsedCode) -> bool:
        """存储解析后的代码数据
        
        Args:
            parsed_code: 解析后的代码数据
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            StorageError: 存储失败时抛出异常（无fallback）
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        file_path = parsed_code.file_info.path
        func_count = len(parsed_code.functions)
        
        logger.info(f"📁 Storing parsed code for file: {file_path}")
        logger.debug(f"File details: name={parsed_code.file_info.name}, size={parsed_code.file_info.size}")
        logger.debug(f"Function count: {func_count}")
        
        if func_count > 0:
            func_names = [f.name for f in parsed_code.functions]
            logger.debug(f"Functions to store: {func_names}")
        
        try:
            with self.driver.session() as session:
                logger.debug("Session created, starting transaction...")
                
                # 使用事务函数确保数据一致性
                result = session.execute_write(self._store_code_transaction, parsed_code)
                
                logger.info(f"✅ Successfully stored {func_count} functions from {file_path}")
                logger.debug(f"Transaction result: {result}")
                return True
                    
        except Neo4jError as e:
            error_msg = f"Neo4j error during storage of {file_path}: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("transaction_failed", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during storage of {file_path}: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("storage_operation", error_msg)

    def _store_code_transaction(self, tx, parsed_code: ParsedCode) -> bool:
        """存储代码的事务函数
        
        Args:
            tx: Neo4j事务对象
            parsed_code: 解析后的代码数据
            
        Returns:
            bool: 事务是否成功
            
        Raises:
            Exception: 事务失败时抛出异常（无fallback）
        """
        file_info = parsed_code.file_info
        file_path = file_info.path
        
        logger.debug(f"🔄 Starting transaction for file: {file_path}")
        
        try:
            # 1. 创建或更新文件节点
            logger.debug("Step 1: Creating/updating File node")
            file_query = """
            MERGE (f:File {path: $path})
            SET f.name = $name,
                f.size = $size,
                f.last_modified = $last_modified,
                f.updated = datetime()
            RETURN f
            """
            
            file_params = {
                'path': file_info.path,
                'name': file_info.name,
                'size': file_info.size,
                'last_modified': file_info.last_modified.isoformat()
            }
            logger.debug(f"File query params: {file_params}")
            
            file_result = tx.run(file_query, **file_params)
            file_record = file_result.single()
            logger.debug(f"File node created/updated: {file_record}")
            
            # 2. 批量创建函数节点和CONTAINS关系
            if parsed_code.functions:
                logger.debug(f"Step 2: Creating {len(parsed_code.functions)} Function nodes and relationships")
                
                functions_data = []
                for func in parsed_code.functions:
                    func_data = {
                        'name': func.name,
                        'start_line': func.start_line,
                        'end_line': func.end_line,
                        'code': func.code,
                        'file_path': file_info.path
                    }
                    functions_data.append(func_data)
                    logger.debug(f"Prepared function data: {func.name} ({func.start_line}-{func.end_line})")
                
                # 批量创建函数节点和关系
                batch_query = """
                UNWIND $functions as func
                MATCH (f:File {path: func.file_path})
                MERGE (fn:Function {name: func.name, file_path: func.file_path})
                SET fn.start_line = func.start_line,
                    fn.end_line = func.end_line,
                    fn.code = func.code,
                    fn.updated = datetime()
                MERGE (f)-[:CONTAINS]->(fn)
                RETURN fn.name as created_function
                """
                
                logger.debug(f"Executing batch query with {len(functions_data)} functions")
                batch_result = tx.run(batch_query, functions=functions_data)
                
                created_functions = [record["created_function"] for record in batch_result]
                logger.debug(f"Created functions: {created_functions}")
            else:
                logger.debug("No functions to create for this file")
            
            logger.debug(f"✅ Transaction completed successfully for file: {file_path}")
            
            # 3. 存储函数调用关系 (Story 2.1.3)
            if parsed_code.call_relationships:
                logger.debug(f"Step 3: Creating {len(parsed_code.call_relationships)} CALLS relationships")
                
                calls_data = []
                for call in parsed_code.call_relationships:
                    call_data = {
                        'caller': call.caller_name,
                        'callee': call.callee_name,
                        'call_type': call.call_type,
                        'line_no': call.line_number,
                        'context': call.context
                    }
                    calls_data.append(call_data)
                    logger.debug(f"Prepared call relationship: {call.caller_name} -> {call.callee_name} ({call.call_type})")
                
                # 批量创建调用关系
                calls_query = """
                UNWIND $calls as call
                MERGE (caller:Function {name: call.caller})
                MERGE (callee:Function {name: call.callee})
                MERGE (caller)-[rel:CALLS]->(callee)
                SET rel.call_type = call.call_type,
                    rel.line_no = call.line_no,
                    rel.context = call.context,
                    rel.updated = datetime()
                RETURN caller.name as caller_name, callee.name as callee_name
                """
                
                logger.debug(f"Executing calls query with {len(calls_data)} relationships")
                calls_result = tx.run(calls_query, calls=calls_data)
                
                created_calls = [(record["caller_name"], record["callee_name"]) for record in calls_result]
                logger.debug(f"Created call relationships: {created_calls}")
            else:
                logger.debug("No call relationships to create for this file")
            
            return True
            
        except Exception as e:
            error_msg = f"Transaction failed for file {file_path}: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("transaction_execution", error_msg)

    def clear_database(self) -> bool:
        """清空数据库中的所有数据
        
        Returns:
            bool: 清空是否成功
            
        Raises:
            StorageError: 清空失败时抛出异常（无fallback）
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        logger.warning("🗑️  Clearing ALL data from Neo4j database")
        logger.debug("This will delete all nodes and relationships")
        
        try:
            with self.driver.session() as session:
                logger.debug("Session created for database clear operation")
                
                result = session.execute_write(self._clear_database_transaction)
                
                logger.info("✅ Successfully cleared Neo4j database")
                logger.debug(f"Clear operation result: {result}")
                return True
                    
        except Neo4jError as e:
            error_msg = f"Neo4j error during database clear: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("clear_transaction_failed", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during database clear: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("clear_operation_failed", error_msg)

    def _clear_database_transaction(self, tx) -> bool:
        """清空数据库的事务函数
        
        Args:
            tx: Neo4j事务对象
            
        Returns:
            bool: 事务是否成功
            
        Raises:
            Exception: 事务失败时抛出异常（无fallback）
        """
        logger.debug("🔄 Starting database clear transaction")
        
        try:
            # 首先统计要删除的数据
            count_query = """
            MATCH (n) 
            OPTIONAL MATCH (n)-[r]-()
            RETURN count(distinct n) as node_count, 
                   count(distinct r) as relationship_count
            """
            count_result = tx.run(count_query)
            count_record = count_result.single()
            
            node_count = count_record["node_count"]
            rel_count = count_record["relationship_count"]
            
            logger.debug(f"About to delete: {node_count} nodes, {rel_count} relationships")
            
            # 删除所有关系和节点
            clear_query = """
            MATCH (n)
            DETACH DELETE n
            """
            
            clear_result = tx.run(clear_query)
            logger.debug(f"Clear query executed: {clear_result.consume().counters}")
            
            # 验证清空结果
            verify_query = "MATCH (n) RETURN count(n) as remaining_nodes"
            verify_result = tx.run(verify_query)
            remaining = verify_result.single()["remaining_nodes"]
            
            if remaining > 0:
                error_msg = f"Database clear incomplete: {remaining} nodes still exist"
                logger.error(f"❌ {error_msg}")
                raise StorageError("clear_incomplete", error_msg)
            
            logger.debug(f"✅ Database clear transaction completed: deleted {node_count} nodes, {rel_count} relationships")
            return True
            
        except Exception as e:
            error_msg = f"Clear transaction execution failed: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("clear_transaction_execution", error_msg)

    def close(self) -> None:
        """关闭数据库连接"""
        if self.driver:
            logger.info("🔌 Closing Neo4j connection")
            logger.debug("Closing driver and cleaning up resources")
            self.driver.close()
            self.driver = None
            self.connected = False
            logger.info("✅ Neo4j connection closed successfully")
        else:
            logger.debug("No active connection to close")

    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close()

    def __enter__(self):
        """上下文管理器入口"""
        logger.debug("Entering Neo4jGraphStore context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        logger.debug(f"Exiting Neo4jGraphStore context (exc_type: {exc_type})")
        self.close()

    # Story 2.1 新增方法 - 占位实现 (将在Story 2.1.5中正式实现)
    
    def store_call_relationship(self, caller: str, callee: str, call_type: str) -> bool:
        """存储函数调用关系 - 占位实现
        
        Args:
            caller: 调用者函数名
            callee: 被调用函数名  
            call_type: 调用类型
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.5中实现
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")

        if not caller or not callee:
            raise StorageError("invalid_params", "caller and callee must be non-empty")

        try:
            with self.driver.session() as session:
                query = (
                    "MERGE (caller:Function {name:$caller})\n"
                    "MERGE (callee:Function {name:$callee})\n"
                    "MERGE (caller)-[rel:CALLS]->(callee)\n"
                    "SET rel.call_type = $call_type, rel.updated = datetime()"
                )
                session.run(query, caller=caller, callee=callee, call_type=call_type)
            return True
        except Exception as e:
            logger.error(f"Failed to store CALLS relationship {caller}->{callee}: {e}")
            raise StorageError("call_relationship", str(e))
    
    def store_call_relationships_batch(self, call_relationships) -> bool:
        """批量存储函数调用关系 - 占位实现
        
        Args:
            call_relationships: 函数调用关系列表
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.5中实现
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")

        if not call_relationships:
            return True

        try:
            with self.driver.session() as session:
                batch_query = (
                    "UNWIND $rels as rel\n"
                    "MERGE (caller:Function {name: rel.caller})\n"
                    "MERGE (callee:Function {name: rel.callee})\n"
                    "MERGE (caller)-[r:CALLS]->(callee)\n"
                    "SET r.call_type = rel.call_type, r.updated = datetime()"
                )
                rel_dicts = [
                    {
                        "caller": r.caller_name,
                        "callee": r.callee_name,
                        "call_type": r.call_type,
                    }
                    for r in call_relationships
                ]
                session.run(batch_query, rels=rel_dicts)
            return True
        except Exception as e:
            logger.error(f"Failed to batch store call relationships: {e}")
            raise StorageError("call_relationship_batch", str(e))
    
    def query_function_calls(self, function_name: str):
        """查询函数直接调用的其他函数
        
        Args:
            function_name: 函数名
            
        Returns:
            List[str]: 被调用函数名列表
        """
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
        
        try:
            with self.driver.session() as session:
                # 查询函数直接调用的其他函数
                query = """
                MATCH (caller:Function {name: $name})-[:CALLS]->(callee:Function)
                RETURN callee.name as callee
                """
                result = session.run(query, name=function_name)
                
                # 提取被调用函数名
                callees = [record["callee"] for record in result.data()]
                
                logger.debug(f"函数 '{function_name}' 调用了 {len(callees)} 个函数")
                return callees
                
        except Exception as e:
            logger.error(f"查询函数调用失败: {e}")
            return []
    
    def query_function_callers(self, function_name: str):
        """查询调用指定函数的其他函数
        
        Args:
            function_name: 函数名
            
        Returns:
            List[str]: 调用者函数名列表
        """
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
        
        try:
            with self.driver.session() as session:
                # 查询调用指定函数的其他函数
                query = """
                MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})
                RETURN caller.name as caller
                """
                result = session.run(query, name=function_name)
                
                # 提取调用者函数名
                callers = [record["caller"] for record in result.data()]
                
                logger.debug(f"函数 '{function_name}' 被 {len(callers)} 个函数调用")
                return callers
                
        except Exception as e:
            logger.error(f"查询函数被调用失败: {e}")
            return []
            
    def get_function_code(self, function_name: str) -> Optional[str]:
        """获取函数代码
        
        Args:
            function_name: 函数名
            
        Returns:
            Optional[str]: 函数代码，如果不存在则返回None
        """
        if not self.driver:
            logger.error("数据库连接未初始化")
            return None
        
        try:
            with self.driver.session() as session:
                # 单次查询，获取函数代码或位置信息
                query = """
                MATCH (f:Function {name: $name})
                OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
                RETURN f.code as code, file.path as file_path, 
                       f.start_line as start_line, f.end_line as end_line
                """
                result = session.run(query, name=function_name)
                record = result.single()
                
                if not record:
                    logger.warning(f"函数 '{function_name}' 未找到")
                    return None
                
                # 优先使用存储的代码
                if record.get("code"):
                    return record["code"]
                
                # 如果没有存储代码但有位置信息，从文件读取
                if record.get("file_path") and record.get("start_line") and record.get("end_line"):
                    return self._read_function_from_file(
                        record["file_path"], 
                        record["start_line"], 
                        record["end_line"]
                    )
                
                return None
                    
        except Exception as e:
            logger.error(f"从Neo4j检索函数代码失败: {e}")
            return None
    
    def _read_function_from_file(self, file_path: str, start_line: int, end_line: int) -> Optional[str]:
        """从文件读取函数代码
        
        Args:
            file_path: 文件路径
            start_line: 起始行（从1开始）
            end_line: 结束行
            
        Returns:
            Optional[str]: 函数代码
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                if start_line <= len(lines) and end_line <= len(lines):
                    function_code = ''.join(lines[start_line-1:end_line])
                    return function_code
                else:
                    logger.warning(f"文件行数不足: {file_path}, 总行数: {len(lines)}, 请求行: {start_line}-{end_line}")
                    return None
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            return None
    
    def query_call_graph(self, root_function: str, max_depth: int = 5):
        """生成函数调用图谱
        
        Args:
            root_function: 根函数名
            max_depth: 最大查询深度
            
        Returns:
            Dict[str, Any]: 调用图谱数据结构 {nodes: [...], edges: [...]}
            
        Raises:
            StorageError: 查询失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")

        if not root_function.strip():
            raise StorageError("invalid_params", "root_function must be non-empty")

        try:
            with self.driver.session() as session:
                # 使用可变长度路径查询调用图
                # 注意：不能在MATCH模式中使用参数，需要字符串拼接
                query = f"""
                MATCH path = (root:Function {{name: $root_function}})-[:CALLS*1..{max_depth}]->(target:Function)
                WITH nodes(path) as path_nodes, relationships(path) as path_rels
                UNWIND path_nodes as node
                WITH COLLECT(DISTINCT {{id: node.name, name: node.name, file_path: node.file_path}}) as nodes,
                     path_rels
                UNWIND path_rels as rel
                WITH nodes, 
                     COLLECT(DISTINCT {{
                         source: startNode(rel).name, 
                         target: endNode(rel).name,
                         call_type: rel.call_type,
                         line_no: rel.line_no
                     }}) as edges
                RETURN nodes, edges
                """
                
                result = session.run(query, root_function=root_function)
                record = result.single()
                
                if record:
                    nodes = record["nodes"] or []
                    edges = record["edges"] or []
                else:
                    # 如果没有找到调用路径，至少返回根节点
                    root_query = "MATCH (f:Function {name: $root_function}) RETURN f"
                    root_result = session.run(root_query, root_function=root_function)
                    root_record = root_result.single()
                    
                    if root_record:
                        root_node = root_record["f"]
                        nodes = [{
                            "id": root_node["name"],
                            "name": root_node["name"],
                            "file_path": root_node.get("file_path", "unknown")
                        }]
                        edges = []
                    else:
                        nodes = []
                        edges = []
                
                return {
                    "nodes": nodes,
                    "edges": edges,
                    "root": root_function,
                    "max_depth": max_depth
                }
                
        except Exception as e:
            logger.error(f"Failed to query call graph for {root_function}: {e}")
            raise StorageError("call_graph_query", str(e))
    
    def find_unused_functions(self):
        """查找未被调用的函数 - 占位实现
        
        Returns:
            List[str]: 未使用函数名列表
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.5中实现
        """
        raise NotImplementedError("find_unused_functions will be implemented in Story 2.1.5")
    
    def store_folder_structure(self, folder_structure) -> bool:
        """存储文件夹结构信息 - 占位实现
        
        Args:
            folder_structure: 文件夹结构数据
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.5中实现
        """
        raise NotImplementedError("store_folder_structure will be implemented in Story 2.1.5")

    def store_file_dependencies(self, dependencies: List[FileDependency]) -> bool:
        """存储文件依赖关系
        
        Args:
            dependencies: 文件依赖关系列表
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"存储文件依赖关系: {len(dependencies)}个")
        
        if not self.driver:
            logger.error("数据库连接未初始化")
            return False
        
        try:
            with self.driver.session() as session:
                return session.execute_write(self._store_file_dependencies_tx, dependencies)
                
        except Exception as e:
            logger.error(f"存储文件依赖关系失败: {e}")
            return False
    
    def _store_file_dependencies_tx(self, tx, dependencies: List[FileDependency]) -> bool:
        """存储文件依赖关系的事务函数
        
        Args:
            tx: 事务对象
            dependencies: 文件依赖关系列表
            
        Returns:
            bool: 是否存储成功
        """
        try:
            # 批量创建文件依赖关系
            query = """
            UNWIND $dependencies AS dep
            MERGE (source:File {path: dep.source_file})
            MERGE (target:File {path: dep.target_file})
            MERGE (source)-[r:DEPENDS_ON {
                type: dep.dependency_type,
                is_system: dep.is_system
            }]->(target)
            SET r.line_number = dep.line_number,
                r.updated_at = datetime()
            """
            
            dependencies_data = [
                {
                    "source_file": dep.source_file,
                    "target_file": dep.target_file,
                    "dependency_type": dep.dependency_type,
                    "is_system": dep.is_system,
                    "line_number": dep.line_number
                }
                for dep in dependencies
            ]
            
            tx.run(query, dependencies=dependencies_data)
            return True
            
        except Exception as e:
            logger.error(f"存储文件依赖关系事务失败: {e}")
            raise
    
    def store_module_dependencies(self, dependencies: List[ModuleDependency]) -> bool:
        """存储模块依赖关系
        
        Args:
            dependencies: 模块依赖关系列表
            
        Returns:
            bool: 是否成功
        """
        logger.info(f"存储模块依赖关系: {len(dependencies)}个")
        
        if not self.driver:
            logger.error("数据库连接未初始化")
            return False
        
        try:
            with self.driver.session() as session:
                return session.execute_write(self._store_module_dependencies_tx, dependencies)
                
        except Exception as e:
            logger.error(f"存储模块依赖关系失败: {e}")
            return False
    
    def _store_module_dependencies_tx(self, tx, dependencies: List[ModuleDependency]) -> bool:
        """存储模块依赖关系的事务函数
        
        Args:
            tx: 事务对象
            dependencies: 模块依赖关系列表
            
        Returns:
            bool: 是否存储成功
        """
        try:
            # 批量创建模块依赖关系
            query = """
            UNWIND $dependencies AS dep
            MERGE (source:Module {name: dep.source_module})
            MERGE (target:Module {name: dep.target_module})
            MERGE (source)-[r:DEPENDS_ON]->(target)
            SET r.file_count = dep.file_count,
                r.strength = dep.strength,
                r.is_circular = dep.is_circular,
                r.updated_at = datetime()
            """
            
            dependencies_data = [
                {
                    "source_module": dep.source_module,
                    "target_module": dep.target_module,
                    "file_count": dep.file_count,
                    "strength": dep.strength,
                    "is_circular": dep.is_circular
                }
                for dep in dependencies
            ]
            
            tx.run(query, dependencies=dependencies_data)
            return True
            
        except Exception as e:
            logger.error(f"存储模块依赖关系事务失败: {e}")
            raise
    
    def query_file_dependencies(self, file_path: str = None) -> List[Dict[str, Any]]:
        """查询文件依赖关系
        
        Args:
            file_path: 文件路径，如果为None则查询所有文件依赖
            
        Returns:
            List[Dict[str, Any]]: 文件依赖关系列表
        """
        logger.info(f"查询文件依赖关系: {file_path if file_path else '所有'}")
        
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
        
        try:
            with self.driver.session() as session:
                if file_path:
                    # 查询特定文件的依赖
                    result = session.run(
                        """
                        MATCH (source:File {path: $file_path})-[r:DEPENDS_ON]->(target:File)
                        RETURN source.path AS source_file, target.path AS target_file,
                               r.type AS dependency_type, r.is_system AS is_system,
                               r.line_number AS line_number, r.context AS context
                        """,
                        file_path=file_path
                    )
                else:
                    # 查询所有文件依赖
                    result = session.run(
                        """
                        MATCH (source:File)-[r:DEPENDS_ON]->(target:File)
                        RETURN source.path AS source_file, target.path AS target_file,
                               r.type AS dependency_type, r.is_system AS is_system,
                               r.line_number AS line_number, r.context AS context
                        """
                    )
                
                dependencies = []
                for record in result:
                    dependency = {
                        "source_file": record["source_file"],
                        "target_file": record["target_file"],
                        "dependency_type": record["dependency_type"],
                        "is_system": record["is_system"],
                        "line_number": record["line_number"],
                        "context": record["context"]
                    }
                    dependencies.append(dependency)
                
                logger.debug(f"查询到 {len(dependencies)} 个文件依赖关系")
                return dependencies
        
        except Exception as e:
            logger.error(f"查询文件依赖关系失败: {e}")
            return []
    
    def query_module_dependencies(self, module_name: str = None) -> List[Dict[str, Any]]:
        """查询模块依赖关系
        
        Args:
            module_name: 模块名称，如果为None则查询所有模块依赖
            
        Returns:
            List[Dict[str, Any]]: 模块依赖关系列表
        """
        logger.info(f"查询模块依赖关系: {module_name if module_name else '所有'}")
        
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
        
        try:
            with self.driver.session() as session:
                if module_name:
                    # 查询特定模块的依赖
                    result = session.run(
                        """
                        MATCH (source:Module {name: $module_name})-[r:DEPENDS_ON]->(target:Module)
                        RETURN source.name AS source_module, target.name AS target_module,
                               r.file_count AS file_count, r.strength AS strength,
                               r.is_circular AS is_circular
                        """,
                        module_name=module_name
                    )
                else:
                    # 查询所有模块依赖
                    result = session.run(
                        """
                        MATCH (source:Module)-[r:DEPENDS_ON]->(target:Module)
                        RETURN source.name AS source_module, target.name AS target_module,
                               r.file_count AS file_count, r.strength AS strength,
                               r.is_circular AS is_circular
                        """
                    )
                
                dependencies = []
                for record in result:
                    # 查询该模块依赖涉及的文件
                    files_result = session.run(
                        """
                        MATCH (sf:File)-[:BELONGS_TO]->(source:Module {name: $source_module})
                        MATCH (tf:File)-[:BELONGS_TO]->(target:Module {name: $target_module})
                        MATCH (sf)-[:DEPENDS_ON]->(tf)
                        RETURN sf.path AS source_file, tf.path AS target_file
                        LIMIT 100
                        """,
                        source_module=record["source_module"],
                        target_module=record["target_module"]
                    )
                    
                    files = [(file["source_file"], file["target_file"]) for file in files_result]
                    
                    dependency = {
                        "source_module": record["source_module"],
                        "target_module": record["target_module"],
                        "file_count": record["file_count"],
                        "strength": record["strength"],
                        "is_circular": record["is_circular"],
                        "files": files
                    }
                    dependencies.append(dependency)
                
                logger.debug(f"查询到 {len(dependencies)} 个模块依赖关系")
                return dependencies
        
        except Exception as e:
            logger.error(f"查询模块依赖关系失败: {e}")
            return []
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖
        
        Returns:
            List[List[str]]: 循环依赖链列表
        """
        logger.info("检测循环依赖")
        
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
        
        try:
            with self.driver.session() as session:
                # 使用Neo4j的路径查找功能检测环
                result = session.run(
                    """
                    MATCH path = (m:Module)-[:DEPENDS_ON*2..10]->(m)
                    WITH nodes(path) AS modules
                    RETURN [module IN modules | module.name] AS cycle
                    LIMIT 100
                    """
                )
                
                circular_dependencies = []
                for record in result:
                    cycle = record["cycle"]
                    # 确保环的起点和终点相同
                    if cycle[0] == cycle[-1]:
                        # 去除重复的环
                        normalized_cycle = cycle[:-1]  # 移除最后一个重复元素
                        if normalized_cycle not in circular_dependencies:
                            circular_dependencies.append(normalized_cycle)
                
                logger.debug(f"检测到 {len(circular_dependencies)} 个循环依赖")
                return circular_dependencies
        
        except Exception as e:
            logger.error(f"检测循环依赖失败: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            Dict[str, Any]: 健康状态
        """
        try:
            if not self.driver:
                return {"status": "unhealthy", "error": "数据库连接未初始化"}
            
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                
                if record and record["test"] == 1:
                    # 获取节点和关系统计
                    stats_result = session.run("""
                        MATCH (n) 
                        OPTIONAL MATCH ()-[r]->() 
                        RETURN count(DISTINCT n) as nodes, count(r) as relationships
                    """)
                    stats = stats_result.single()
                    
                    return {
                        "status": "healthy", 
                        "uri": self.uri,
                        "user": self.user,
                        "nodes": stats["nodes"],
                        "relationships": stats["relationships"],
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {"status": "unhealthy", "error": "查询结果异常"}
                    
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _initialize_constraints(self):
        """初始化数据库约束和索引"""
        if not self.connected or not self.driver:
            logger.warning("数据库连接未初始化，无法创建约束")
            return
        
        try:
            with self.driver.session() as session:
                # 创建函数节点的唯一约束
                session.run("""
                    CREATE CONSTRAINT function_name_file_unique IF NOT EXISTS
                    FOR (f:Function)
                    REQUIRE (f.name, f.file_path) IS UNIQUE
                """)
                
                # 创建文件节点的唯一约束
                session.run("""
                    CREATE CONSTRAINT file_path_unique IF NOT EXISTS
                    FOR (f:File)
                    REQUIRE f.path IS UNIQUE
                """)
                
                # 创建模块节点的唯一约束
                session.run("""
                    CREATE CONSTRAINT module_name_unique IF NOT EXISTS
                    FOR (m:Module)
                    REQUIRE m.name IS UNIQUE
                """)
                
                # 创建索引以提高查询性能
                session.run("""
                    CREATE INDEX function_name_index IF NOT EXISTS
                    FOR (f:Function)
                    ON (f.name)
                """)
                
                session.run("""
                    CREATE INDEX file_name_index IF NOT EXISTS
                    FOR (f:File)
                    ON (f.name)
                """)
                
                logger.info("Neo4j数据库约束和索引已初始化")
                
        except Exception as e:
            logger.error(f"创建数据库约束失败: {e}")
            # 约束创建失败不应该影响整体功能 

    def get_all_code_units(self) -> List[Dict[str, Any]]:
        """获取所有可嵌入的代码单元（函数和结构体）

        Returns:
            List[Dict[str, Any]]: 代码单元列表，每个单元包含 name, code, file_path, 等信息
        
        Raises:
            StorageError: 查询失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        logger.info("🚚 获取所有可嵌入的代码单元 (Functions, Structs)")

        try:
            with self.driver.session() as session:
                result = session.read_transaction(self._get_all_code_units_tx)
                code_units = [record.data() for record in result]
                logger.info(f"✅ 成功检索到 {len(code_units)} 个代码单元")
                return code_units

        except Neo4jError as e:
            error_msg = f"Neo4j error while fetching code units: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("transaction_failed", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error while fetching code units: {e}"
            logger.error(f"❌ {error_msg}")
            raise StorageError("storage_operation", error_msg)


    def _get_all_code_units_tx(self, tx) -> List[Dict[str, Any]]:
        """获取所有代码单元的事务函数
        
        Args:
            tx: Neo4j事务对象
            
        Returns:
            List[Dict[str, Any]]: 代码单元列表
        """
        query = """
        MATCH (n)
        WHERE n:Function OR n:Struct
        RETURN
            n.name as name,
            n.code as code,
            n.file_path as file_path,
            n.start_line as start_line,
            n.end_line as end_line,
            labels(n)[0] as node_type
        """
        logger.debug("Executing query to fetch all code units")
        result = tx.run(query)
        return result 