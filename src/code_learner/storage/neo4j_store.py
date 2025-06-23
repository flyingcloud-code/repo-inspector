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
from typing import Optional
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError

from ..core.interfaces import IGraphStore
from ..core.data_models import ParsedCode
from ..core.exceptions import StorageError
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class Neo4jGraphStore(IGraphStore):
    """Neo4j图数据库存储实现
    
    严格模式：所有错误都会抛出异常，不提供fallback机制
    """

    def __init__(self):
        """初始化Neo4j图存储"""
        self.driver: Optional[Driver] = None
        
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

    def connect(self, uri: str, user: str, password: str) -> bool:
        """连接到Neo4j数据库
        
        Args:
            uri: Neo4j数据库URI (如 bolt://localhost:7687)
            user: 用户名
            password: 密码
            
        Returns:
            bool: 连接是否成功
            
        Raises:
            StorageError: 连接失败时抛出异常（无fallback）
        """
        logger.info(f"Attempting to connect to Neo4j at {uri} with user '{user}'")
        logger.debug(f"Connection config: max_pool_size=50, timeout=60s")
        
        try:
            # 创建驱动连接
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(user, password),
                # 性能优化配置
                max_connection_pool_size=50,
                connection_acquisition_timeout=60.0
            )
            
            logger.debug("Driver created, verifying connectivity...")
            
            # 验证连接
            self.driver.verify_connectivity()
            
            logger.info("✅ Successfully connected to Neo4j database")
            logger.debug(f"Driver info: {self.driver}")
            return True
            
        except ServiceUnavailable as e:
            error_msg = f"Neo4j service unavailable at {uri}: {e}"
            logger.error(f"❌ {error_msg}")
            self.driver = None
            raise StorageError("connection_unavailable", error_msg)
            
        except AuthError as e:
            error_msg = f"Authentication failed for user '{user}': {e}"
            logger.error(f"❌ {error_msg}")
            self.driver = None
            raise StorageError("authentication_failed", error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected connection error: {e}"
            logger.error(f"❌ {error_msg}")
            self.driver = None
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