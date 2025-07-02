#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
import time
from typing import Optional

from code_learner.storage.neo4j_store import Neo4jGraphStore
from code_learner.llm.service_factory import ServiceFactory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_function(function_name: str, project_id: Optional[str] = None):
    """测试查询函数代码和调用关系
    
    Args:
        function_name: 函数名称
        project_id: 项目ID
    """
    logger.info(f"测试函数代码获取: {function_name}")
    
    # 方法1: 使用get_function_code方法
    start_time = time.time()
    store = Neo4jGraphStore(project_id=project_id)
    store.connect()
    
    try:
        code = store.get_function_code(function_name)
        elapsed = time.time() - start_time
        logger.info(f"方法1 (get_function_code) 耗时: {elapsed:.3f}秒")
        
        if code:
            logger.info(f"获取到代码 ({len(code)} 字符)")
        else:
            logger.warning(f"方法1未获取到代码")
    except Exception as e:
        logger.error(f"方法1失败: {e}")
    
    # 方法2: 使用get_function_by_name方法
    start_time = time.time()
    try:
        function_info = store.get_function_by_name(function_name)
        elapsed = time.time() - start_time
        logger.info(f"方法2 (get_function_by_name) 耗时: {elapsed:.3f}秒")
        
        if function_info:
            logger.info(f"获取到函数信息: {function_info['name']}, 文件: {function_info['file_path']}")
        else:
            logger.warning(f"方法2未获取到函数信息")
    except Exception as e:
        logger.error(f"方法2失败: {e}")
    
    # 方法3: 直接使用Neo4j查询
    start_time = time.time()
    try:
        query = """
        MATCH (f:Function {name: $name})<-[:CONTAINS]-(file:File)
        RETURN f.name as name, f.file_path as file_path, f.code as code, file.path as real_path
        LIMIT 1
        """
        
        with store.driver.session() as session:
            result = session.run(query, name=function_name)
            record = result.single()
            
            if record:
                logger.info(f"方法3找到函数: {record['name']}, 文件路径: {record['real_path']}")
                if record["code"]:
                    logger.info(f"代码长度: {len(record['code'])} 字符")
                else:
                    logger.warning("没有存储代码")
            else:
                logger.warning("方法3未找到函数")
                
        elapsed = time.time() - start_time
        logger.info(f"方法3 (直接查询) 耗时: {elapsed:.3f}秒")
    except Exception as e:
        logger.error(f"方法3查询失败: {e}")
    
    store.close()
    
    # 测试调用关系
    logger.info(f"测试函数调用关系: {function_name}")
    store = Neo4jGraphStore(project_id=project_id)
    store.connect()
    
    # 获取调用者
    start_time = time.time()
    try:
        callers = store.get_function_callers(function_name)
        elapsed = time.time() - start_time
        logger.info(f"获取调用者耗时: {elapsed:.3f}秒")
        
        if callers:
            logger.info(f"找到 {len(callers)} 个调用者:")
            for i, caller in enumerate(callers):
                logger.info(f"  调用者 {i+1}: {caller['name']}")
        else:
            logger.warning(f"未找到调用者")
    except Exception as e:
        logger.error(f"获取调用者失败: {e}")
    
    # 获取被调用者
    start_time = time.time()
    try:
        callees = store.get_function_callees(function_name)
        elapsed = time.time() - start_time
        logger.info(f"获取被调用者耗时: {elapsed:.3f}秒")
        
        if callees:
            logger.info(f"找到 {len(callees)} 个被调用者:")
            for i, callee in enumerate(callees):
                logger.info(f"  被调用者 {i+1}: {callee['name']}")
        else:
            logger.warning(f"未找到被调用者")
    except Exception as e:
        logger.error(f"获取被调用者失败: {e}")
    
    # 使用简单查询测试函数调用
    start_time = time.time()
    try:
        with store.driver.session() as session:
            # 查询函数调用的其他函数
            query = """
            MATCH (caller:Function {name: $name})-[:CALLS]->(callee:Function)
            RETURN callee.name as callee_name
            """
            result = session.run(query, name=function_name)
            callees = [record["callee_name"] for record in result]
            
        elapsed = time.time() - start_time
        logger.info(f"query_function_calls耗时: {elapsed:.3f}秒")
        
        if callees:
            logger.info(f"查询到 {len(callees)} 个被调用函数:")
            for i, callee in enumerate(callees):
                logger.info(f"  被调用函数 {i+1}: {callee}")
        else:
            logger.warning(f"query_function_calls未找到被调用者")
    except Exception as e:
        logger.error(f"query_function_calls失败: {e}")
    
    # 使用简单查询测试函数被调用
    start_time = time.time()
    try:
        with store.driver.session() as session:
            # 查询调用该函数的其他函数
            query = """
            MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})
            RETURN caller.name as caller_name
            """
            result = session.run(query, name=function_name)
            callers = [record["caller_name"] for record in result]
            
        elapsed = time.time() - start_time
        logger.info(f"query_function_callers耗时: {elapsed:.3f}秒")
        
        if callers:
            logger.info(f"查询到 {len(callers)} 个调用者函数:")
            for i, caller in enumerate(callers):
                logger.info(f"  调用者函数 {i+1}: {caller}")
        else:
            logger.warning(f"query_function_callers未找到调用者")
    except Exception as e:
        logger.error(f"query_function_callers失败: {e}")
    
    store.close()
    
    # 使用ServiceFactory测试
    logger.info(f"使用ServiceFactory测试: {function_name}")
    
    try:
        factory = ServiceFactory()
        graph_store = factory.get_graph_store()
        
        code = graph_store.get_function_code(function_name)
        if code:
            logger.info(f"获取到代码 ({len(code)} 字符)")
        else:
            logger.warning(f"未获取到代码")
        
        callers = graph_store.get_function_callers(function_name)
        if callers:
            logger.info(f"找到 {len(callers)} 个调用者")
        else:
            logger.warning(f"未找到调用者")
        
        callees = graph_store.get_function_callees(function_name)
        if callees:
            logger.info(f"找到 {len(callees)} 个被调用者")
        else:
            logger.warning(f"未找到被调用者")
        
        graph_store.close()
    except Exception as e:
        logger.error(f"ServiceFactory测试失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试Neo4j函数代码和调用关系查询")
    parser.add_argument("function_name", help="要查询的函数名")
    parser.add_argument("--project-id", help="项目ID")
    
    args = parser.parse_args()
    check_function(args.function_name, args.project_id) 