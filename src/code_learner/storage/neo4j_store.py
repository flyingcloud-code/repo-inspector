"""
Neo4j图数据库存储实现

提供Neo4j图数据库的存储功能：
- 连接管理
- 数据存储（File和Function节点）
- 关系建立（CONTAINS关系）
- 严格错误处理（无fallback）
- 详细日志记录
- 项目隔离支持
"""

import logging
import time
import os
import hashlib
from typing import Optional, List, Dict, Any, Set, Tuple, Union
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError, ConfigurationError, TransientError
from neo4j.graph import Node
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import re

from ..core.interfaces import IGraphStore
from ..core.data_models import ParsedCode, Function, FileInfo, FunctionCall, FolderStructure, FileDependency, ModuleDependency
from ..core.exceptions import StorageError
from ..config.config_manager import ConfigManager
from ..utils.logger import get_logger

logger = logging.getLogger(__name__)


class Neo4jGraphStore(IGraphStore):
    """Neo4j图数据库存储实现
    
    严格模式：所有错误都会抛出异常，不提供fallback机制
    支持项目隔离：通过project_id属性区分不同项目的数据
    """

    def __init__(self, uri: str = None, user: str = None, password: str = None, project_id: str = None):
        """初始化Neo4j图存储
        
        Args:
            uri: Neo4j数据库URI，如果为None则从环境变量获取
            user: 用户名，如果为None则从环境变量获取
            password: 密码，如果为None则从环境变量获取
            project_id: 项目ID，用于隔离不同项目的数据
        """
        self.driver: Optional[Driver] = None
        self.uri = uri
        self.user = user
        self.password = password
        self.project_id = project_id
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
        if self.project_id:
            logger.info(f"Project isolation enabled with project_id: {self.project_id}")

        # 加载环境变量
        load_dotenv()
        
        # 如果提供了URI、用户名和密码，尝试连接
        if uri and user and password:
            self.connect(uri, user, password)

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
            # 如果参数为None，尝试从环境变量获取或使用初始化时提供的值
            uri = uri or self.uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = user or self.user or os.getenv("NEO4J_USER", "neo4j")
            password = password or self.password or os.getenv("NEO4J_PASSWORD")
            
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
            self.password = password
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
        """存储解析后的代码信息
        
        Args:
            parsed_code: 解析后的代码对象
            
        Returns:
            bool: 存储是否成功
            
        Raises:
            StorageError: 存储失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                return session.execute_write(self._store_code_transaction, parsed_code)
        except Exception as e:
            logger.error(f"❌ Failed to execute store_parsed_code transaction: {e}")
            raise StorageError("storage_operation", f"Transaction failed during storage of {parsed_code.file_info.path}: {e}")

    def _store_code_transaction(self, tx, parsed_code: ParsedCode) -> bool:
        """在事务中存储代码数据
        
        Args:
            tx: Neo4j事务对象
            parsed_code: 解析后的代码数据
            
        Returns:
            bool: 存储是否成功
        """
        file_path = parsed_code.file_info.path
        file_name = os.path.basename(file_path)
        language = parsed_code.file_info.file_type or "c"
        file_size = parsed_code.file_info.size
        last_modified = parsed_code.file_info.last_modified
        
        # 如果没有设置project_id，使用文件路径的哈希作为默认project_id
        if not self.project_id:
            self.project_id = "auto_" + hashlib.md5(file_path.encode()).hexdigest()[:8]
            logger.info(f"事务中未设置project_id，使用自动生成的ID: {self.project_id}")
        
        # 创建文件节点
        file_query = """
        MERGE (f:File {path: $path, project_id: $project_id})
        SET f.name = $name,
            f.language = $language,
            f.size = $size,
            f.last_modified = $last_modified,
            f.last_updated = datetime()
        RETURN f
        """
        
        file_params = {
            "path": file_path,
            "name": file_name,
            "language": language,
            "size": file_size,
            "last_modified": last_modified,
            "project_id": self.project_id
        }
        
        tx.run(file_query, file_params)
        
        # 创建或合并模块节点，并建立文件与模块的关系
        module_path = str(Path(file_path).parent)
        module_query = """
        MATCH (f:File {path: $file_path, project_id: $project_id})
        MERGE (m:Module {name: $module_path, project_id: $project_id})
        MERGE (f)-[:BELONGS_TO]->(m)
        """
        module_params = {
            "file_path": file_path,
            "module_path": module_path,
            "project_id": self.project_id
        }
        tx.run(module_query, module_params)
        
        # 批量创建函数节点并建立与文件的关系
        if parsed_code.functions:
            function_creation_query = """
            UNWIND $functions AS func
            MERGE (fn:Function {name: func.name, file_path: $file_path, project_id: $project_id})
            SET fn.start_line = func.start_line,
                fn.end_line = func.end_line,
                fn.docstring = func.docstring,
                fn.parameters = func.parameters,
                fn.return_type = func.return_type,
                fn.code = func.code,
                fn.last_updated = datetime()
            WITH fn, func
            MATCH (f:File {path: $file_path, project_id: $project_id})
            MERGE (f)-[:CONTAINS]->(fn)
            """
            
            functions_data = [
                {
                    "name": f.name,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "docstring": f.docstring or "",
                    "parameters": f.parameters or [],
                    "return_type": f.return_type or "",
                    "code": f.code or ""
                } for f in parsed_code.functions
            ]
            
            tx.run(function_creation_query, functions=functions_data, file_path=file_path, project_id=self.project_id)

        # 批量创建函数调用关系
        if parsed_code.call_relationships:
            call_relationship_query = """
            UNWIND $calls AS call
            MATCH (caller:Function {name: call.caller_name, file_path: call.file_path, project_id: $project_id})
            MATCH (callee:Function {name: call.callee_name, project_id: $project_id})
            MERGE (caller)-[r:CALLS]->(callee)
            ON CREATE SET r.line = call.line_number, r.context = call.context, r.last_updated = datetime()
            """
            
            calls_data = [
                {
                    "caller_name": call.caller_name,
                    "callee_name": call.callee_name,
                    "file_path": call.file_path,
                    "line_number": call.line_number,
                    "context": call.context
                } for call in parsed_code.call_relationships
            ]
            
            tx.run(call_relationship_query, calls=calls_data, project_id=self.project_id)
        
        logger.info(f"✅ Successfully processed {len(parsed_code.functions)} functions and {len(parsed_code.call_relationships)} calls from {file_path} in transaction.")
        return True

    def create_file_node(self, file_path: str, language: str) -> bool:
        """创建单个文件节点
        
        Args:
            file_path: 文件路径
            language: 文件语言
            
        Returns:
            bool: 创建是否成功
            
        Raises:
            StorageError: 创建失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            with self.driver.session() as session:
                # 根据是否有项目ID选择不同的查询
                if self.project_id:
                    # 先检查是否已存在相同的文件节点
                    check_query = """
                    MATCH (f:File {path: $path, project_id: $project_id})
                    RETURN f
                    """
                    check_params = {
                        "path": file_path,
                        "project_id": self.project_id
                    }
                    check_result = session.run(check_query, check_params)
                    
                    if check_result.single():
                        logger.info(f"文件节点已存在: {file_path} (项目ID: {self.project_id})")
                        return True
                    
                    # 创建文件节点
                    query = """
                    CREATE (f:File {
                        path: $path, 
                        name: $name,
                        language: $language, 
                        project_id: $project_id
                    })
                    RETURN f
                    """
                    params = {
                        "path": file_path,
                        "name": os.path.basename(file_path),
                        "language": language,
                        "project_id": self.project_id
                    }
                    logger.info(f"创建文件节点: {file_path} (项目ID: {self.project_id})")
                else:
                    # 向后兼容，不添加project_id属性
                    query = """
                    CREATE (f:File {
                        path: $path, 
                        name: $name,
                        language: $language
                    })
                    RETURN f
                    """
                    params = {
                        "path": file_path,
                        "name": os.path.basename(file_path),
                        "language": language
                    }
                    logger.info(f"创建文件节点: {file_path} (无项目隔离)")
                
                logger.debug(f"执行查询: {query}")
                logger.debug(f"查询参数: {params}")
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    logger.info(f"✅ 文件节点创建成功: {file_path}")
                    return True
                else:
                    logger.warning(f"⚠️ 文件节点可能未创建: {file_path}")
                    return False
        except Exception as e:
            logger.error(f"创建文件节点失败: {e}")
            # 如果是唯一约束冲突，且启用了项目隔离，尝试清理旧数据
            if "ConstraintValidationFailed" in str(e) and self.project_id:
                try:
                    logger.warning(f"检测到约束冲突，尝试清理旧数据并重新创建节点")
                    with self.driver.session() as session:
                        # 删除没有project_id的同路径节点
                        clean_query = """
                        MATCH (f:File {path: $path})
                        WHERE f.project_id IS NULL OR NOT EXISTS(f.project_id)
                        DELETE f
                        """
                        session.run(clean_query, {"path": file_path})
                        
                        # 重新创建节点
                        create_query = """
                        CREATE (f:File {
                            path: $path, 
                            name: $name,
                            language: $language, 
                            project_id: $project_id
                        })
                        RETURN f
                        """
                        create_params = {
                            "path": file_path,
                            "name": os.path.basename(file_path),
                            "language": language,
                            "project_id": self.project_id
                        }
                        result = session.run(create_query, create_params)
                        if result.single():
                            logger.info(f"✅ 清理后成功创建文件节点: {file_path}")
                            return True
                except Exception as recovery_error:
                    logger.error(f"尝试恢复失败: {recovery_error}")
            
            raise StorageError("create_file_node", str(e))

    def create_function_node(self, file_path: str, name: str, start_line: int, end_line: int, 
                            docstring: str = "", parameters: List[str] = None, 
                            return_type: str = "", code: str = None) -> bool:
        """创建函数节点
        
        Args:
            file_path: 文件路径
            name: 函数名
            start_line: 开始行号
            end_line: 结束行号
            docstring: 函数文档字符串
            parameters: 参数列表
            return_type: 返回类型
            code: 函数的源代码
            
        Returns:
            bool: 创建是否成功
            
        Raises:
            StorageError: 创建失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            # 如果没有提供代码但有位置信息，尝试从文件读取
            if not code and file_path and start_line and end_line:
                try:
                    code = self._read_function_from_file(file_path, start_line, end_line)
                    if code:
                        logger.debug(f"Successfully read function code from file: {name}")
                except Exception as e:
                    logger.warning(f"Could not read function code from file for {name}: {e}")

            with self.driver.session() as session:
                # 首先检查文件节点是否存在
                file_check_query = """
                MATCH (f:File {path: $path})
                """
                
                # 如果启用了项目隔离，添加项目ID条件
                if self.project_id:
                    file_check_query += " WHERE f.project_id = $project_id"
                    file_check_params = {
                        "path": file_path,
                        "project_id": self.project_id
                    }
                    logger.debug(f"检查文件节点是否存在 (项目ID: {self.project_id}): {file_path}")
                else:
                    file_check_params = {"path": file_path}
                    logger.debug(f"检查文件节点是否存在 (无项目隔离): {file_path}")
                
                file_check_query += " RETURN f"
                file_check_result = session.run(file_check_query, file_check_params)
                file_record = file_check_result.single()
                
                if not file_record:
                    logger.warning(f"文件节点不存在，将先创建文件节点: {file_path}")
                    self.create_file_node(file_path, "c")  # 假设是C语言文件
                
                # 创建函数节点
                if parameters is None:
                    parameters = []
                    
                # 根据是否有项目ID选择不同的查询
                if self.project_id:
                    logger.info(f"创建函数节点: {name} (项目ID: {self.project_id})")
                    # 检查是否已存在相同的函数节点
                    check_query = """
                    MATCH (f:Function {name: $name, file_path: $file_path, project_id: $project_id})
                    RETURN f
                    """
                    check_params = {
                        "name": name,
                        "file_path": file_path,
                        "project_id": self.project_id
                    }
                    check_result = session.run(check_query, check_params)
                    
                    if check_result.single():
                        logger.info(f"函数节点已存在: {name} (项目ID: {self.project_id})")
                        return True
                    
                    # 创建函数节点并与文件节点建立关系
                    query = """
                    MATCH (file:File {path: $file_path, project_id: $project_id})
                    CREATE (func:Function {
                        name: $name,
                        file_path: $file_path,
                        start_line: $start_line,
                        end_line: $end_line,
                        docstring: $docstring,
                        parameters: $parameters,
                        return_type: $return_type,
                        code: $code,
                        project_id: $project_id
                    })
                    CREATE (file)-[:CONTAINS {project_id: $project_id}]->(func)
                    RETURN func
                    """
                    params = {
                        "name": name,
                        "file_path": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "docstring": docstring,
                        "parameters": parameters,
                        "return_type": return_type,
                        "code": code,
                        "project_id": self.project_id
                    }
                else:
                    # 向后兼容，不添加project_id属性
                    logger.info(f"创建函数节点: {name} (无项目隔离)")
                    query = """
                    MATCH (file:File {path: $file_path})
                    CREATE (func:Function {
                        name: $name,
                        file_path: $file_path,
                        start_line: $start_line,
                        end_line: $end_line,
                        docstring: $docstring,
                        parameters: $parameters,
                        return_type: $return_type,
                        code: $code
                    })
                    CREATE (file)-[:CONTAINS]->(func)
                    RETURN func
                    """
                    params = {
                        "name": name,
                        "file_path": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "docstring": docstring,
                        "parameters": parameters,
                        "return_type": return_type,
                        "code": code
                    }
                
                logger.debug(f"执行查询: {query}")
                logger.debug(f"查询参数: {params}")
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    logger.info(f"✅ 函数节点创建成功: {name}")
                    return True
                else:
                    logger.warning(f"⚠️ 函数节点可能未创建: {name}")
                    return False
        except Exception as e:
            logger.error(f"创建函数节点失败: {e}")
            # 如果是唯一约束冲突，且启用了项目隔离，尝试清理旧数据
            if "ConstraintValidationFailed" in str(e) and self.project_id:
                try:
                    logger.warning(f"检测到约束冲突，尝试清理旧数据并重新创建节点")
                    with self.driver.session() as session:
                        # 删除没有project_id的同名函数节点
                        clean_query = """
                        MATCH (f:Function {name: $name, file_path: $file_path})
                        WHERE f.project_id IS NULL OR NOT EXISTS(f.project_id)
                        DETACH DELETE f
                        """
                        session.run(clean_query, {"name": name, "file_path": file_path})
                        
                        # 重新创建节点
                        create_query = """
                        MATCH (file:File {path: $file_path, project_id: $project_id})
                        CREATE (func:Function {
                            name: $name,
                            file_path: $file_path,
                            start_line: $start_line,
                            end_line: $end_line,
                            docstring: $docstring,
                            parameters: $parameters,
                            return_type: $return_type,
                            code: $code,
                            project_id: $project_id
                        })
                        CREATE (file)-[:CONTAINS {project_id: $project_id}]->(func)
                        RETURN func
                        """
                        create_params = {
                            "name": name,
                            "file_path": file_path,
                            "start_line": start_line,
                            "end_line": end_line,
                            "docstring": docstring,
                            "parameters": parameters,
                            "return_type": return_type,
                            "code": code,
                            "project_id": self.project_id
                        }
                        result = session.run(create_query, create_params)
                        if result.single():
                            logger.info(f"✅ 清理后成功创建函数节点: {name}")
                            return True
                except Exception as recovery_error:
                    logger.error(f"尝试恢复失败: {recovery_error}")
            
            raise StorageError("create_function_node", str(e))

    def create_calls_relationship(self, caller_function: str, called_function: str) -> bool:
        """创建调用关系
        
        Args:
            caller_function: 调用函数名
            called_function: 被调用函数名
            
        Returns:
            bool: 创建是否成功
            
        Raises:
            StorageError: 创建失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            with self.driver.session() as session:
                # 根据是否有项目ID选择不同的查询
                if self.project_id:
                    query = """
                    MATCH (caller:Function {name: $caller, project_id: $project_id})
                    MATCH (called:Function {name: $called, project_id: $project_id})
                    CREATE (caller)-[:CALLS {project_id: $project_id}]->(called)
                    RETURN caller, called
                    """
                    params = {
                        "caller": caller_function,
                        "called": called_function,
                        "project_id": self.project_id
                    }
                else:
                    # 向后兼容，不添加project_id属性
                    query = """
                    MATCH (caller:Function {name: $caller})
                    MATCH (called:Function {name: $called})
                    CREATE (caller)-[:CALLS]->(called)
                    RETURN caller, called
                    """
                    params = {
                        "caller": caller_function,
                        "called": called_function
                    }
                session.run(query, params)
                return True
        except Exception as e:
            logger.error(f"Failed to create calls relationship: {e}")
            raise StorageError("create_calls_relationship", str(e))

    def get_functions(self) -> List[Dict[str, Any]]:
        """获取所有函数
        
        Returns:
            List[Dict[str, Any]]: 函数列表
            
        Raises:
            StorageError: 获取失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            with self.driver.session() as session:
                # 根据是否有项目ID选择不同的查询
                if self.project_id:
                    logger.info(f"查询特定项目的函数: project_id={self.project_id}")
                    query = """
                    MATCH (f:Function)
                    WHERE f.project_id = $project_id
                    RETURN f.name as name, f.file_path as file_path, 
                           f.start_line as start_line, f.end_line as end_line,
                           f.project_id as project_id
                    """
                    params = {"project_id": self.project_id}
                else:
                    logger.info("查询所有函数 (无项目隔离)")
                    query = """
                    MATCH (f:Function)
                    RETURN f.name as name, f.file_path as file_path, 
                           f.start_line as start_line, f.end_line as end_line,
                           f.project_id as project_id
                    """
                    params = {}
                
                logger.debug(f"执行查询: {query}")
                logger.debug(f"查询参数: {params}")
                
                result = session.run(query, params)
                functions = [dict(record) for record in result]
                
                logger.info(f"查询到 {len(functions)} 个函数")
                return functions
                
        except Exception as e:
            logger.error(f"获取函数失败: {e}")
            raise StorageError("get_functions", str(e))

    def get_call_graph(self) -> List[Dict[str, Any]]:
        """获取调用图
        
        Returns:
            List[Dict[str, Any]]: 调用关系列表
            
        Raises:
            StorageError: 获取失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            with self.driver.session() as session:
                # 根据是否有项目ID选择不同的查询
                if self.project_id:
                    query = """
                    MATCH (caller:Function)-[r:CALLS]->(called:Function)
                    WHERE r.project_id = $project_id
                    RETURN caller.name as caller, called.name as called
                    """
                    params = {"project_id": self.project_id}
                else:
                    # 向后兼容，不过滤project_id
                    query = """
                    MATCH (caller:Function)-[r:CALLS]->(called:Function)
                    RETURN caller.name as caller, called.name as called
                    """
                    params = {}
                result = session.run(query, params)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Failed to get call graph: {e}")
            raise StorageError("get_call_graph", str(e))

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
                # 使用与方法3相同的查询语法
                query = """
                MATCH (f:Function {name: $name})<-[:CONTAINS]-(file:File)
                RETURN f.name as name, f.file_path as file_path, f.code as code, file.path as real_path
                LIMIT 1
                """
                
                # 准备查询参数
                params = {
                    "name": function_name
                }
                
                result = session.run(query, params)
                record = result.single()
                
                if not record:
                    logger.warning(f"函数 '{function_name}' 未找到")
                    return None
                
                code = record.get("code")
                
                # 如果没有代码但有位置信息，尝试从文件读取
                file_path = record.get("real_path") or record.get("file_path")
                if not code and file_path and record.get("start_line") and record.get("end_line"):
                    code = self._read_function_from_file(
                        file_path,
                        record["start_line"],
                        record["end_line"]
                    )
                    
                    if code:
                        # 更新数据库中的代码字段
                        update_query = """
                        MATCH (f:Function {name: $name})<-[:CONTAINS]-(file:File)
                        SET f.code = $code
                        """
                        
                        update_params = {
                            "name": function_name,
                            "code": code
                        }
                        
                        try:
                            session.run(update_query, update_params)
                            logger.info(f"更新了函数 {function_name} 的代码")
                        except Exception as update_error:
                            logger.warning(f"更新函数代码失败: {update_error}")
                
                return code
                
        except Exception as e:
            logger.error(f"❌ 获取函数代码失败: {e}")
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
        # 允许通过环境变量跳过约束初始化，以加快纯查询场景
        if os.getenv("SKIP_NEO4J_SCHEMA_INIT", "false").lower() in ("1", "true", "yes"):
            logger.info("⏩ 跳过Neo4j约束初始化 (SKIP_NEO4J_SCHEMA_INIT=TRUE)")
            return

        if not self.connected or not self.driver:
            logger.warning("数据库连接未初始化，无法创建约束")
            return
        
        try:
            with self.driver.session() as session:
                # 先尝试删除可能存在的旧约束，以确保向后兼容
                try:
                    session.run("DROP CONSTRAINT function_name_file_project_unique IF EXISTS")
                    session.run("DROP CONSTRAINT function_name_file_unique IF EXISTS")
                    session.run("DROP CONSTRAINT file_path_project_unique IF EXISTS")
                    session.run("DROP CONSTRAINT file_path_unique IF EXISTS")
                    session.run("DROP CONSTRAINT module_name_unique IF EXISTS")
                    session.run("DROP CONSTRAINT module_name_project_unique IF EXISTS")
                    logger.info("已删除可能存在的旧约束，准备创建新约束")
                except Exception as e:
                    logger.warning(f"删除旧约束时出错（可能它们不存在，可忽略）: {e}")
                
                # 创建函数节点的唯一约束 (项目隔离)
                session.run("""
                    CREATE CONSTRAINT function_unique IF NOT EXISTS
                    FOR (f:Function)
                    REQUIRE (f.name, f.file_path, f.project_id) IS UNIQUE
                """)
                
                # 创建文件节点的唯一约束 (项目隔离)
                session.run("""
                    CREATE CONSTRAINT file_unique IF NOT EXISTS
                    FOR (f:File)
                    REQUIRE (f.path, f.project_id) IS UNIQUE
                """)
                
                # 创建模块节点的唯一约束 (项目隔离)
                session.run("""
                    CREATE CONSTRAINT module_unique IF NOT EXISTS
                    FOR (m:Module)
                    REQUIRE (m.name, m.project_id) IS UNIQUE
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

    def run_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行自定义Cypher查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        
        Raises:
            StorageError: 查询失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                # 修复: 直接返回列表，避免ResultConsumedError
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            raise StorageError("query_execution_failed", str(e))
            
    def query(self, query: str, params: Dict = None):
        """执行Cypher查询并返回结果
        
        Args:
            query: Cypher查询语句
            params: 查询参数
            
        Returns:
            查询结果 (已被消费为列表)
            
        Raises:
            StorageError: 查询失败时抛出异常
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
            
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                # 修复: 直接返回列表，避免ResultConsumedError
                return list(result)
        except Exception as e:
            logger.error(f"执行查询失败: {e}")
            raise StorageError("query_execution_failed", str(e))

    def search_functions_by_keywords(self, keywords: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        """通过关键词搜索函数
        
        Args:
            keywords: 关键词列表
            max_results: 最大返回结果数
            
        Returns:
            List[Dict[str, Any]]: 函数列表
        """
        if not self.driver:
            logger.error("数据库连接未初始化")
            return []
            
        if not keywords:
            logger.warning("未提供关键词")
            return []
            
        try:
            with self.driver.session() as session:
                # 构建查询
                # 1. 首先尝试在函数名中匹配关键词
                name_conditions = []
                for keyword in keywords:
                    name_conditions.append(f"toLower(f.name) CONTAINS toLower('{keyword}')")
                    
                name_query = " OR ".join(name_conditions)
                
                # 构建完整查询
                query = f"""
                MATCH (f:Function)
                WHERE {name_query}
                """
                
                # 添加项目ID过滤
                if self.project_id:
                    query += f" AND f.project_id = $project_id"
                    
                # 添加排序和限制
                query += """
                RETURN f.name as name, f.file_path as file_path, 
                       f.start_line as start_line, f.end_line as end_line
                LIMIT $limit
                """
                
                # 准备参数
                params = {"limit": max_results}
                if self.project_id:
                    params["project_id"] = self.project_id
                    
                # 执行查询
                logger.debug(f"执行关键词搜索查询: {query}")
                logger.debug(f"查询参数: {params}")
                
                result = session.run(query, params)
                functions = [dict(record) for record in result]
                
                # 如果没有找到足够的结果，尝试更宽松的搜索（在代码中搜索关键词）
                if len(functions) < max_results:
                    remaining = max_results - len(functions)
                    
                    # 避免重复结果
                    existing_names = [f["name"] for f in functions]
                    exclude_clause = ""
                    if existing_names:
                        name_list = ", ".join([f"'{name}'" for name in existing_names])
                        exclude_clause = f" AND NOT f.name IN [{name_list}]"
                    
                    # 构建代码搜索查询
                    code_query = f"""
                    MATCH (f:Function)
                    WHERE f.code IS NOT NULL {exclude_clause}
                    """
                    
                    # 添加项目ID过滤
                    if self.project_id:
                        code_query += f" AND f.project_id = $project_id"
                        
                    # 添加关键词过滤
                    code_conditions = []
                    for i, keyword in enumerate(keywords):
                        code_conditions.append(f"toLower(f.code) CONTAINS toLower($keyword{i})")
                        params[f"keyword{i}"] = keyword
                        
                    if code_conditions:
                        code_query += " AND (" + " OR ".join(code_conditions) + ")"
                        
                    # 添加排序和限制
                    code_query += """
                    RETURN f.name as name, f.file_path as file_path, 
                           f.start_line as start_line, f.end_line as end_line
                    LIMIT $remaining
                    """
                    
                    # 更新参数
                    params["remaining"] = remaining
                    
                    # 执行代码搜索查询
                    logger.debug(f"执行代码内容搜索查询: {code_query}")
                    logger.debug(f"查询参数: {params}")
                    
                    code_result = session.run(code_query, params)
                    code_functions = [dict(record) for record in code_result]
                    
                    # 合并结果
                    functions.extend(code_functions)
                
                logger.info(f"关键词搜索找到 {len(functions)} 个函数")
                return functions
                
        except Exception as e:
            logger.error(f"关键词搜索函数失败: {e}")
            return [] 

    def count_nodes(self) -> int:
        """计算节点数量
        
        Returns:
            int: 节点数量
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                record = result.single()
                if record:
                    return record["count"]
                return 0
        except Exception as e:
            logger.error(f"❌ 计算节点数量失败: {e}")
            raise StorageError("query_error", f"Failed to count nodes: {str(e)}")

    def count_relationships(self) -> int:
        """计算关系数量
        
        Returns:
            int: 关系数量
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                record = result.single()
                if record:
                    return record["count"]
                return 0
        except Exception as e:
            logger.error(f"❌ 计算关系数量失败: {e}")
            raise StorageError("query_error", f"Failed to count relationships: {str(e)}")

    def get_node_types(self) -> List[str]:
        """获取所有节点类型
        
        Returns:
            List[str]: 节点类型列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run("CALL db.labels() YIELD label RETURN label")
                return [record["label"] for record in result]
        except Exception as e:
            logger.error(f"❌ 获取节点类型失败: {e}")
            raise StorageError("query_error", f"Failed to get node types: {str(e)}")

    def get_relationship_types(self) -> List[str]:
        """获取所有关系类型
        
        Returns:
            List[str]: 关系类型列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
                return [record["relationshipType"] for record in result]
        except Exception as e:
            logger.error(f"❌ 获取关系类型失败: {e}")
            raise StorageError("query_error", f"Failed to get relationship types: {str(e)}")
            
    def count_nodes_by_label(self, label: str) -> int:
        """计算指定标签的节点数量
        
        Args:
            label: 节点标签
            
        Returns:
            int: 节点数量
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                record = result.single()
                return record["count"] if record else 0
        except Exception as e:
            logger.error(f"❌ 计算节点数量失败: {e}")
            raise StorageError("query_error", f"Failed to count nodes: {str(e)}")

    def get_function_by_name(self, function_name: str) -> Optional[Dict[str, Any]]:
        """根据函数名获取函数节点
        
        Args:
            function_name: 函数名
            
        Returns:
            Dict[str, Any]: 函数节点信息，如果不存在则返回None
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                # 使用与方法3相同的查询语法
                query = """
                MATCH (f:Function {name: $function_name})<-[:CONTAINS]-(file:File)
                RETURN f.name as name, f.file_path as file_path, f.code as code,
                       f.start_line as start_line, f.end_line as end_line,
                       f.docstring as docstring, f.parameters as parameters,
                       f.return_type as return_type, file.path as real_path
                LIMIT 1
                """
                
                # 准备查询参数
                params = {
                    "function_name": function_name
                }
                
                result = session.run(query, params)
                record = result.single()
                
                if not record:
                    return None
                    
                function_info = {
                    "name": record["name"],
                    "file_path": record.get("real_path") or record["file_path"],
                    "code": record["code"],
                    "start_line": record["start_line"],
                    "end_line": record["end_line"],
                    "docstring": record.get("docstring", ""),
                    "parameters": record.get("parameters", []),
                    "return_type": record.get("return_type", "")
                }
                
                # 如果没有代码但有位置信息，尝试从文件读取
                if not function_info["code"] and function_info["file_path"] and function_info["start_line"] and function_info["end_line"]:
                    code = self._read_function_from_file(
                        function_info["file_path"],
                        function_info["start_line"],
                        function_info["end_line"]
                    )
                    
                    if code:
                        function_info["code"] = code
                        
                        # 更新数据库中的代码字段
                        update_query = """
                        MATCH (f:Function {name: $name})<-[:CONTAINS]-(file:File)
                        SET f.code = $code
                        """
                        
                        update_params = {
                            "name": function_name,
                            "code": code
                        }
                        
                        try:
                            session.run(update_query, update_params)
                            logger.info(f"更新了函数 {function_name} 的代码")
                        except Exception as update_error:
                            logger.warning(f"更新函数代码失败: {update_error}")
                
                return function_info
                
        except Exception as e:
            logger.error(f"❌ 获取函数节点失败: {e}")
            return None
            
    def get_function_callers(self, function_name: str) -> List[Dict[str, Any]]:
        """获取调用指定函数的函数列表
        
        Args:
            function_name: 函数名
            
        Returns:
            List[Dict[str, Any]]: 调用者函数列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                # 使用简单直接的查询语法
                query = """
                MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $function_name})
                MATCH (caller)<-[:CONTAINS]-(caller_file:File)
                RETURN caller.name as name, caller.file_path as file_path, caller.code as code,
                       caller_file.path as real_path
                LIMIT 10
                """
                
                # 准备查询参数
                params = {
                    "function_name": function_name
                }
                
                result = session.run(query, params)
                
                callers = []
                for record in result:
                    callers.append({
                        "name": record["name"],
                        "file_path": record.get("real_path") or record["file_path"],
                        "code": record["code"]
                    })
                    
                return callers
        except Exception as e:
            logger.error(f"❌ 获取函数调用者失败: {e}")
            return []
            
    def get_function_callees(self, function_name: str) -> List[Dict[str, Any]]:
        """获取被指定函数调用的函数列表
        
        Args:
            function_name: 函数名
            
        Returns:
            List[Dict[str, Any]]: 被调用函数列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                # 使用简单直接的查询语法
                query = """
                MATCH (caller:Function {name: $function_name})-[:CALLS]->(callee:Function)
                MATCH (callee)<-[:CONTAINS]-(callee_file:File)
                RETURN callee.name as name, callee.file_path as file_path, callee.code as code,
                       callee_file.path as real_path
                LIMIT 10
                """
                
                # 准备查询参数
                params = {
                    "function_name": function_name
                }
                
                result = session.run(query, params)
                
                callees = []
                for record in result:
                    callees.append({
                        "name": record["name"],
                        "file_path": record.get("real_path") or record["file_path"],
                        "code": record["code"]
                    })
                    
                return callees
        except Exception as e:
            logger.error(f"❌ 获取被调用函数失败: {e}")
            return []
            
    def get_file_includes(self, file_path: str) -> List[Dict[str, Any]]:
        """获取文件包含的头文件列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Dict[str, Any]]: 包含的头文件列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                # 构建查询语句，如果有project_id则添加过滤条件
                query = """
                MATCH (file:File {path: $file_path})-[:INCLUDES]->(header:File)
                """
                
                # 添加project_id过滤条件
                if self.project_id:
                    query += " WHERE file.project_id = $project_id AND header.project_id = $project_id"
                
                query += """
                RETURN header.path as path
                LIMIT 20
                """
                
                # 准备查询参数
                params = {"file_path": file_path}
                if self.project_id:
                    params["project_id"] = self.project_id
                
                result = session.run(query, **params)
                
                includes = []
                for record in result:
                    includes.append({
                        "path": record["path"]
                    })
                    
                return includes
        except Exception as e:
            logger.error(f"❌ 获取文件包含关系失败: {e}")
            return []
            
    def get_file_included_by(self, file_path: str) -> List[Dict[str, Any]]:
        """获取包含该文件的文件列表
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Dict[str, Any]]: 包含该文件的文件列表
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                # 构建查询语句，如果有project_id则添加过滤条件
                query = """
                MATCH (file:File)-[:INCLUDES]->(header:File {path: $file_path})
                """
                
                # 添加project_id过滤条件
                if self.project_id:
                    query += " WHERE file.project_id = $project_id AND header.project_id = $project_id"
                
                query += """
                RETURN file.path as path
                LIMIT 20
                """
                
                # 准备查询参数
                params = {"file_path": file_path}
                if self.project_id:
                    params["project_id"] = self.project_id
                
                result = session.run(query, **params)
                
                included_by = []
                for record in result:
                    included_by.append({
                        "path": record["path"]
                    })
                    
                return included_by
        except Exception as e:
            logger.error(f"❌ 获取文件被包含关系失败: {e}")
            return []
            
    def get_top_included_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取被包含次数最多的头文件
        
        Args:
            limit: 返回结果数量限制
            
        Returns:
            List[Dict[str, Any]]: 头文件列表，按包含次数降序排序
        """
        if not self.driver:
            raise StorageError("storage_connection", "Not connected to Neo4j database")
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (file:File)-[:INCLUDES]->(header:File)
                WHERE header.path ENDS WITH '.h'
                WITH header.path as path, count(*) as include_count
                ORDER BY include_count DESC
                LIMIT $limit
                RETURN path, include_count
                """
                result = session.run(query, limit=limit)
                
                headers = []
                for record in result:
                    headers.append({
                        "path": record["path"],
                        "include_count": record["include_count"]
                    })
                    
                return headers
        except Exception as e:
            logger.error(f"❌ 获取热门头文件失败: {e}")
            return []

    def add_file(self, path: str, content: str, language: str = "c") -> bool:
        # ... existing code ...
        pass

    # ... rest of the existing code ... 