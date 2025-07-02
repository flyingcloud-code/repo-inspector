# Neo4j图数据库存储接口改进方案

## 问题概述

根据审查，Neo4j图数据库存储接口在项目中的使用存在以下几个主要问题：

1. 接口使用不一致，有些地方使用高级API，有些地方直接执行Cypher查询
2. 函数代码获取逻辑不统一，`get_function_code`方法中的查询没有使用`CONTAINS`关系
3. 错误处理不完善，很多地方捕获异常后只记录日志，没有进一步处理
4. 项目隔离不完整，节点创建时添加了project_id，但关系创建时不一定添加
5. 代码存储问题，函数节点创建时没有直接存储代码内容

## 改进方案

### 1. 修复函数代码获取方法

`get_function_code`方法是最关键的问题之一，需要优先修复：

```python
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
            # 使用CONTAINS关系进行查询，确保获取正确的函数
            query = """
            MATCH (file:File)-[:CONTAINS]->(f:Function {name: $name})
            WHERE f.project_id = $project_id OR NOT EXISTS(f.project_id)
            RETURN f.code as code, file.path as file_path, 
                   f.start_line as start_line, f.end_line as end_line
            LIMIT 1
            """
            
            params = {
                "name": function_name,
                "project_id": self.project_id
            }
            
            result = session.run(query, params)
            record = result.single()
            
            if not record:
                logger.warning(f"函数 '{function_name}' 未找到")
                return None
            
            # 优先使用存储的代码
            if record.get("code"):
                return record["code"]
            
            # 如果没有存储代码但有位置信息，从文件读取
            if record.get("file_path") and record.get("start_line") and record.get("end_line"):
                code = self._read_function_from_file(
                    record["file_path"], 
                    record["start_line"], 
                    record["end_line"]
                )
                
                # 如果成功读取代码，更新数据库中的代码字段
                if code:
                    update_query = """
                    MATCH (file:File)-[:CONTAINS]->(f:Function {name: $name})
                    WHERE f.project_id = $project_id OR NOT EXISTS(f.project_id)
                    SET f.code = $code
                    """
                    
                    update_params = {
                        "name": function_name,
                        "project_id": self.project_id,
                        "code": code
                    }
                    
                    try:
                        session.run(update_query, update_params)
                        logger.info(f"更新了函数 {function_name} 的代码")
                    except Exception as update_error:
                        logger.warning(f"更新函数代码失败: {update_error}")
                
                return code
            
            return None
                
    except Exception as e:
        logger.error(f"从Neo4j检索函数代码失败: {e}")
        return None
```

### 2. 修复get_function_by_name方法

```python
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
            # 使用CONTAINS关系进行查询
            query = """
            MATCH (file:File)-[:CONTAINS]->(f:Function {name: $function_name})
            WHERE (f.project_id = $project_id OR NOT EXISTS(f.project_id))
            RETURN f.name as name, f.file_path as file_path, f.code as code,
                   f.start_line as start_line, f.end_line as end_line,
                   f.docstring as docstring, f.parameters as parameters,
                   f.return_type as return_type, file.path as file_path
            LIMIT 1
            """
            
            # 准备查询参数
            params = {
                "function_name": function_name,
                "project_id": self.project_id
            }
            
            result = session.run(query, params)
            record = result.single()
            
            if not record:
                return None
                
            function_info = {
                "name": record["name"],
                "file_path": record["file_path"],
                "code": record["code"],
                "start_line": record["start_line"],
                "end_line": record["end_line"],
                "docstring": record["docstring"],
                "parameters": record["parameters"],
                "return_type": record["return_type"]
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
                    MATCH (file:File)-[:CONTAINS]->(f:Function {name: $name})
                    WHERE f.project_id = $project_id OR NOT EXISTS(f.project_id)
                    SET f.code = $code
                    """
                    
                    update_params = {
                        "name": function_name,
                        "project_id": self.project_id,
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
```

### 3. 修复get_function_callers和get_function_callees方法

```python
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
            # 使用CONTAINS关系确保正确的关联
            query = """
            MATCH (caller_file:File)-[:CONTAINS]->(caller:Function)-[:CALLS]->(callee:Function {name: $function_name})
            WHERE (caller.project_id = $project_id OR NOT EXISTS(caller.project_id))
            AND (callee.project_id = $project_id OR NOT EXISTS(callee.project_id))
            RETURN caller.name as name, caller.file_path as file_path, caller.code as code,
                   caller_file.path as file_path
            LIMIT 10
            """
            
            # 准备查询参数
            params = {
                "function_name": function_name,
                "project_id": self.project_id
            }
            
            result = session.run(query, params)
            
            callers = []
            for record in result:
                callers.append({
                    "name": record["name"],
                    "file_path": record["file_path"],
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
            # 使用CONTAINS关系确保正确的关联
            query = """
            MATCH (caller_file:File)-[:CONTAINS]->(caller:Function {name: $function_name})-[:CALLS]->(callee:Function)
            WHERE (caller.project_id = $project_id OR NOT EXISTS(caller.project_id))
            AND (callee.project_id = $project_id OR NOT EXISTS(callee.project_id))
            RETURN callee.name as name, callee.file_path as file_path, callee.code as code
            LIMIT 10
            """
            
            # 准备查询参数
            params = {
                "function_name": function_name,
                "project_id": self.project_id
            }
            
            result = session.run(query, params)
            
            callees = []
            for record in result:
                callees.append({
                    "name": record["name"],
                    "file_path": record["file_path"],
                    "code": record["code"]
                })
                
            return callees
    except Exception as e:
        logger.error(f"❌ 获取被调用函数失败: {e}")
        return []
```

### 4. 修改create_function_node方法，直接存储代码

```python
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
        code: 函数代码（可选）
        
    Returns:
        bool: 创建是否成功
        
    Raises:
        StorageError: 创建失败时抛出异常
    """
    if not self.driver:
        raise StorageError("storage_connection", "Not connected to Neo4j database")
        
    try:
        # 如果没有提供代码，尝试从文件读取
        if code is None and file_path and start_line and end_line:
            try:
                code = self._read_function_from_file(file_path, start_line, end_line)
                if code:
                    logger.info(f"成功从文件读取函数代码: {name}")
                else:
                    logger.warning(f"无法从文件读取函数代码: {name}")
            except Exception as e:
                logger.warning(f"从文件读取函数代码失败: {e}")
        
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
```

### 5. 增加批量操作方法

```python
def batch_get_functions(self, function_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """批量获取函数信息
    
    Args:
        function_names: 函数名列表
        
    Returns:
        Dict[str, Dict[str, Any]]: 函数名到函数信息的映射
    """
    if not self.driver:
        raise StorageError("storage_connection", "Not connected to Neo4j database")
    
    if not function_names:
        return {}
    
    try:
        with self.driver.session() as session:
            # 使用参数化查询和UNWIND进行批量查询
            query = """
            UNWIND $function_names AS function_name
            MATCH (file:File)-[:CONTAINS]->(f:Function {name: function_name})
            WHERE (f.project_id = $project_id OR NOT EXISTS(f.project_id))
            RETURN f.name as name, f.file_path as file_path, f.code as code,
                   f.start_line as start_line, f.end_line as end_line,
                   f.docstring as docstring, f.parameters as parameters,
                   f.return_type as return_type
            """
            
            params = {
                "function_names": function_names,
                "project_id": self.project_id
            }
            
            result = session.run(query, params)
            
            functions = {}
            for record in result:
                name = record["name"]
                functions[name] = {
                    "name": name,
                    "file_path": record["file_path"],
                    "code": record["code"],
                    "start_line": record["start_line"],
                    "end_line": record["end_line"],
                    "docstring": record["docstring"],
                    "parameters": record["parameters"],
                    "return_type": record["return_type"]
                }
                
                # 如果没有代码但有位置信息，尝试从文件读取
                if not functions[name]["code"] and functions[name]["file_path"] and functions[name]["start_line"] and functions[name]["end_line"]:
                    try:
                        code = self._read_function_from_file(
                            functions[name]["file_path"],
                            functions[name]["start_line"],
                            functions[name]["end_line"]
                        )
                        if code:
                            functions[name]["code"] = code
                    except Exception as e:
                        logger.warning(f"从文件读取函数 {name} 代码失败: {e}")
            
            return functions
    except Exception as e:
        logger.error(f"批量获取函数失败: {e}")
        return {}
```

### 6. 增强错误处理

```python
def with_retry(max_retries=3, retry_delay=1.0):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(self, *args, **kwargs)
                except (TransientError, ServiceUnavailable) as e:
                    # 这些错误可能是临时的，可以重试
                    retries += 1
                    if retries < max_retries:
                        logger.warning(f"操作失败，将在 {retry_delay} 秒后重试 ({retries}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"操作失败，已达到最大重试次数: {e}")
                        raise StorageError(f"{func.__name__}_retry_failed", str(e))
                except Exception as e:
                    # 其他错误不重试
                    raise StorageError(f"{func.__name__}_failed", str(e))
        return wrapper
    return decorator

# 然后将装饰器应用于关键方法
@with_retry(max_retries=3, retry_delay=1.0)
def get_function_code(self, function_name: str) -> Optional[str]:
    # 方法实现...

@with_retry(max_retries=3, retry_delay=1.0)
def get_function_by_name(self, function_name: str) -> Optional[Dict[str, Any]]:
    # 方法实现...
```

## 实施计划

1. 首先修复`get_function_code`和`get_function_by_name`方法，这是最核心的问题
2. 然后修复`get_function_callers`和`get_function_callees`方法，确保使用CONTAINS关系
3. 修改`create_function_node`方法，直接存储代码内容
4. 添加批量操作方法，提高性能
5. 增强错误处理，添加重试机制
6. 更新文档和注释，确保接口使用清晰明了

## 测试策略

1. 使用`neo4j_function_query.py`工具测试修改后的函数代码获取方法
2. 比较修改前后的性能和结果一致性
3. 测试不同场景下的错误处理和重试机制
4. 验证项目隔离功能是否正常工作
5. 确保向后兼容性，不影响现有功能
