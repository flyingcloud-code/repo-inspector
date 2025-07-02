#!/usr/bin/env python3
"""
Neo4j查询工具

用于直接查询Neo4j数据库，查看节点结构和关系
"""

import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_learner.storage.neo4j_store import Neo4jGraphStore

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def query_function_node(function_name: str, project_id: str = None):
    """查询函数节点
    
    Args:
        function_name: 函数名
        project_id: 项目ID
    """
    # 初始化Neo4j存储
    store = Neo4jGraphStore(project_id=project_id)
    
    try:
        # 连接到Neo4j数据库
        store.connect()
        
        # 查询函数节点
        query = """
            MATCH (n:Function)
            WHERE n.name = $function_name
            RETURN n
            LIMIT 1
            """
        params = {"function_name": function_name}
        
        logger.info(f"执行查询: {query}")
        logger.info(f"查询参数: {params}")
        
        result = store.query(query, params)
        
        # 处理结果
        found = False
        for record in result:
            if 'n' in record:
                node = record['n']
                logger.info(f"找到函数节点: {function_name}")
                logger.info(f"节点属性: {dict(node)}")
                found = True
                break
        
        if not found:
            logger.warning(f"未找到函数节点: {function_name}")
            
            # 尝试模糊匹配
            fuzzy_query = """
                MATCH (n:Function)
                WHERE n.name CONTAINS $function_name
                RETURN n.name as name
                LIMIT 10
                """
            
            logger.info(f"执行模糊匹配: {fuzzy_query}")
            
            fuzzy_result = store.query(fuzzy_query, params)
            
            functions = []
            for record in fuzzy_result:
                if 'name' in record:
                    functions.append(record['name'])
            
            if functions:
                logger.info(f"模糊匹配结果: {functions}")
            else:
                logger.warning("模糊匹配也未找到函数")
        
        # 查询文件信息
        file_query = """
            MATCH (f:Function)-[:DEFINED_IN]->(file:File)
            WHERE f.name = $function_name
            RETURN file.name as file_name, file.path as file_path
            LIMIT 1
            """
        
        logger.info(f"查询文件信息: {file_query}")
        
        file_result = store.query(file_query, params)
        
        found_file = False
        for record in file_result:
            if 'file_name' in record and 'file_path' in record:
                logger.info(f"文件名: {record['file_name']}")
                logger.info(f"文件路径: {record['file_path']}")
                found_file = True
                break
        
        if not found_file:
            logger.warning(f"未找到函数 {function_name} 的文件信息")
            
            # 尝试其他关系
            other_query = """
                MATCH (f:Function {name: $function_name})-[r]->(other)
                RETURN type(r) as relation_type, other
                LIMIT 10
                """
            
            logger.info(f"查询其他关系: {other_query}")
            
            other_result = store.query(other_query, params)
            
            relations = []
            for record in other_result:
                if 'relation_type' in record and 'other' in record:
                    relations.append({
                        'type': record['relation_type'],
                        'other': dict(record['other'])
                    })
            
            if relations:
                logger.info(f"其他关系: {relations}")
            else:
                logger.warning(f"未找到函数 {function_name} 的其他关系")
                
            # 查询反向关系
            reverse_query = """
                MATCH (other)-[r]->(f:Function {name: $function_name})
                RETURN type(r) as relation_type, other
                LIMIT 10
                """
                
            logger.info(f"查询反向关系: {reverse_query}")
            
            reverse_result = store.query(reverse_query, params)
            
            reverse_relations = []
            for record in reverse_result:
                if 'relation_type' in record and 'other' in record:
                    reverse_relations.append({
                        'type': record['relation_type'],
                        'other': dict(record['other'])
                    })
            
            if reverse_relations:
                logger.info(f"反向关系: {reverse_relations}")
            else:
                logger.warning(f"未找到函数 {function_name} 的反向关系")
        
        # 查询所有可能的关系类型
        relation_query = """
            MATCH ()-[r]->()
            RETURN DISTINCT type(r) as relation_type
            """
            
        logger.info(f"查询所有关系类型: {relation_query}")
        
        relation_result = store.query(relation_query)
        
        relation_types = []
        for record in relation_result:
            if 'relation_type' in record:
                relation_types.append(record['relation_type'])
        
        if relation_types:
            logger.info(f"所有关系类型: {relation_types}")
        else:
            logger.warning("未找到任何关系类型")
            
    except Exception as e:
        logger.error(f"查询失败: {e}")
    finally:
        # 关闭连接
        store.close()

def query_file_node(file_name: str, project_id: str = None):
    """查询文件节点
    
    Args:
        file_name: 文件名
        project_id: 项目ID
    """
    # 初始化Neo4j存储
    store = Neo4jGraphStore(project_id=project_id)
    
    try:
        # 连接到Neo4j数据库
        store.connect()
        
        # 查询文件节点
        query = """
            MATCH (n:File)
            WHERE n.name = $file_name
            RETURN n
            LIMIT 1
            """
        params = {"file_name": file_name}
        
        logger.info(f"执行查询: {query}")
        logger.info(f"查询参数: {params}")
        
        result = store.query(query, params)
        
        # 处理结果
        found = False
        for record in result:
            if 'n' in record:
                node = record['n']
                logger.info(f"找到文件节点: {file_name}")
                logger.info(f"节点属性: {dict(node)}")
                found = True
                break
        
        if not found:
            logger.warning(f"未找到文件节点: {file_name}")
            
            # 尝试模糊匹配
            fuzzy_query = """
                MATCH (n:File)
                WHERE n.name CONTAINS $file_name
                RETURN n.name as name, n.path as path
                LIMIT 10
                """
            
            logger.info(f"执行模糊匹配: {fuzzy_query}")
            
            fuzzy_result = store.query(fuzzy_query, params)
            
            files = []
            for record in fuzzy_result:
                if 'name' in record and 'path' in record:
                    files.append({
                        'name': record['name'],
                        'path': record['path']
                    })
            
            if files:
                logger.info(f"模糊匹配结果: {files}")
            else:
                logger.warning("模糊匹配也未找到文件")
        
        # 查询文件包含的函数
        functions_query = """
            MATCH (file:File)-[:CONTAINS]->(f:Function)
            WHERE file.name = $file_name
            RETURN f.name as function_name
            LIMIT 10
            """
        
        logger.info(f"查询文件包含的函数: {functions_query}")
        
        functions_result = store.query(functions_query, params)
        
        functions = []
        for record in functions_result:
            if 'function_name' in record:
                functions.append(record['function_name'])
        
        if functions:
            logger.info(f"文件包含的函数: {functions}")
        else:
            logger.warning(f"未找到文件 {file_name} 包含的函数")
            
    except Exception as e:
        logger.error(f"查询失败: {e}")
    finally:
        # 关闭连接
        store.close()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j查询工具")
    parser.add_argument("--function", "-f", help="查询函数节点")
    parser.add_argument("--file", "-F", help="查询文件节点")
    parser.add_argument("--project", "-p", help="项目ID")
    
    args = parser.parse_args()
    
    if args.function:
        query_function_node(args.function, args.project)
    elif args.file:
        query_file_node(args.file, args.project)
    else:
        logger.error("请指定要查询的函数名或文件名")
        parser.print_help()

if __name__ == "__main__":
    main() 