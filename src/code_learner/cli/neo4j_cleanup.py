#!/usr/bin/env python3
"""
Neo4j数据库清理工具

用于清理Neo4j数据库中的重复节点和无效关系。
"""

import logging
import sys
import os
import argparse
from pathlib import Path
import time

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_learner.storage.neo4j_store import Neo4jGraphStore
from code_learner.llm.service_factory import ServiceFactory

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_duplicate_files(store: Neo4jGraphStore) -> list:
    """查找重复的文件节点
    
    Args:
        store: Neo4j存储对象
        
    Returns:
        list: 重复文件路径列表
    """
    logger.info("查找重复的文件节点...")
    
    try:
        with store.driver.session() as session:
            query = """
            MATCH (f:File)
            WITH f.path as path, collect(f) as files
            WHERE size(files) > 1
            RETURN path, size(files) as count
            """
            
            result = session.run(query)
            duplicates = []
            
            for record in result:
                path = record["path"]
                count = record["count"]
                logger.info(f"发现重复文件路径: {path} (数量: {count})")
                duplicates.append(path)
                
            return duplicates
    except Exception as e:
        logger.error(f"查找重复文件节点失败: {e}")
        return []

def fix_duplicate_files(store: Neo4jGraphStore, duplicate_paths: list) -> bool:
    """修复重复的文件节点
    
    Args:
        store: Neo4j存储对象
        duplicate_paths: 重复文件路径列表
        
    Returns:
        bool: 是否成功
    """
    logger.info("修复重复的文件节点...")
    
    if not duplicate_paths:
        logger.info("没有发现重复的文件节点")
        return True
    
    try:
        with store.driver.session() as session:
            for path in duplicate_paths:
                # 1. 查找该路径的所有文件节点
                query1 = """
                MATCH (f:File {path: $path})
                RETURN id(f) as id, f.project_id as project_id
                """
                
                result = list(session.run(query1, {"path": path}))
                if len(result) <= 1:
                    continue
                
                # 保留第一个节点，删除其他节点
                keep_id = result[0]["id"]
                delete_ids = [r["id"] for r in result[1:]]
                
                logger.info(f"文件路径 {path}: 保留节点ID {keep_id}, 删除节点IDs {delete_ids}")
                
                # 2. 将要删除的节点的关系转移到保留的节点
                for delete_id in delete_ids:
                    # 转移包含的函数
                    query2 = """
                    MATCH (old:File)-[r:CONTAINS]->(func:Function)
                    WHERE id(old) = $delete_id
                    MATCH (keep:File)
                    WHERE id(keep) = $keep_id
                    MERGE (keep)-[:CONTAINS]->(func)
                    DELETE r
                    """
                    
                    session.run(query2, {"delete_id": delete_id, "keep_id": keep_id})
                    
                    # 转移包含关系
                    query3 = """
                    MATCH (f:File)-[r:INCLUDES]->(old:File)
                    WHERE id(old) = $delete_id
                    MATCH (keep:File)
                    WHERE id(keep) = $keep_id
                    MERGE (f)-[:INCLUDES]->(keep)
                    DELETE r
                    """
                    
                    session.run(query3, {"delete_id": delete_id, "keep_id": keep_id})
                    
                    # 转移被包含关系
                    query4 = """
                    MATCH (old:File)-[r:INCLUDES]->(f:File)
                    WHERE id(old) = $delete_id
                    MATCH (keep:File)
                    WHERE id(keep) = $keep_id
                    MERGE (keep)-[:INCLUDES]->(f)
                    DELETE r
                    """
                    
                    session.run(query4, {"delete_id": delete_id, "keep_id": keep_id})
                
                # 3. 删除多余的节点
                query5 = """
                MATCH (f:File)
                WHERE id(f) IN $delete_ids
                DETACH DELETE f
                """
                
                session.run(query5, {"delete_ids": delete_ids})
                
                logger.info(f"成功修复文件路径 {path} 的重复节点")
            
            return True
    except Exception as e:
        logger.error(f"修复重复文件节点失败: {e}")
        return False

def find_orphaned_functions(store: Neo4jGraphStore) -> list:
    """查找没有CONTAINS关系的函数节点
    
    Args:
        store: Neo4j存储对象
        
    Returns:
        list: 孤立函数节点ID列表
    """
    logger.info("查找孤立的函数节点...")
    
    try:
        with store.driver.session() as session:
            query = """
            MATCH (f:Function)
            WHERE NOT ((:File)-[:CONTAINS]->(f))
            RETURN id(f) as id, f.name as name, f.file_path as file_path
            """
            
            result = session.run(query)
            orphans = []
            
            for record in result:
                node_id = record["id"]
                name = record["name"]
                file_path = record["file_path"]
                logger.info(f"发现孤立函数节点: {name} (ID: {node_id}, 文件路径: {file_path})")
                orphans.append((node_id, name, file_path))
                
            return orphans
    except Exception as e:
        logger.error(f"查找孤立函数节点失败: {e}")
        return []

def fix_orphaned_functions(store: Neo4jGraphStore, orphans: list) -> bool:
    """修复孤立的函数节点
    
    Args:
        store: Neo4j存储对象
        orphans: 孤立函数节点列表 [(id, name, file_path), ...]
        
    Returns:
        bool: 是否成功
    """
    logger.info("修复孤立的函数节点...")
    
    if not orphans:
        logger.info("没有发现孤立的函数节点")
        return True
    
    try:
        with store.driver.session() as session:
            for node_id, name, file_path in orphans:
                if not file_path:
                    logger.warning(f"函数节点 {name} (ID: {node_id}) 没有文件路径，无法修复")
                    continue
                
                # 1. 查找或创建文件节点
                query1 = """
                MERGE (f:File {path: $path})
                ON CREATE SET f.language = 'c'
                RETURN f
                """
                
                session.run(query1, {"path": file_path})
                
                # 2. 创建CONTAINS关系
                query2 = """
                MATCH (file:File {path: $path})
                MATCH (func:Function)
                WHERE id(func) = $node_id
                MERGE (file)-[:CONTAINS]->(func)
                """
                
                session.run(query2, {"path": file_path, "node_id": node_id})
                
                logger.info(f"成功修复函数节点 {name} (ID: {node_id})")
            
            return True
    except Exception as e:
        logger.error(f"修复孤立函数节点失败: {e}")
        return False

def cleanup_database(store: Neo4jGraphStore) -> bool:
    """清理数据库
    
    Args:
        store: Neo4j存储对象
        
    Returns:
        bool: 是否成功
    """
    logger.info("开始清理数据库...")
    
    # 1. 查找并修复重复的文件节点
    duplicate_paths = find_duplicate_files(store)
    if not fix_duplicate_files(store, duplicate_paths):
        return False
    
    # 2. 查找并修复孤立的函数节点
    orphans = find_orphaned_functions(store)
    if not fix_orphaned_functions(store, orphans):
        return False
    
    logger.info("数据库清理完成")
    return True

def clear_database_completely(store: Neo4jGraphStore) -> bool:
    """完全清空数据库
    
    Args:
        store: Neo4j存储对象
        
    Returns:
        bool: 是否成功
    """
    logger.warning("准备完全清空数据库...")
    
    try:
        # 调用核心的清空方法
        store.clear_database()
        logger.info("数据库已成功清空")
        return True
    except Exception as e:
        logger.error(f"清空数据库失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Neo4j数据库清理工具")
    parser.add_argument("--project", "-p", help="项目ID")
    parser.add_argument("--cleanup", action="store_true", help="执行清理操作")
    parser.add_argument("--clear", action="store_true", help="完全清空数据库")
    
    args = parser.parse_args()
    
    # 初始化Neo4j存储
    service_factory = ServiceFactory()
    store = service_factory.get_graph_store(project_id=args.project)
    
    try:
        if not store.connected:
            logger.error("无法连接到Neo4j数据库，请检查配置")
            return
            
        if args.clear:
            confirm = input("你确定要完全清空数据库吗？所有数据都将丢失！(yes/no): ")
            if confirm.lower() == 'yes':
                clear_database_completely(store)
            else:
                logger.info("操作已取消")
        elif args.cleanup:
            cleanup_database(store)
        else:
            logger.info("请指定操作: --cleanup 或 --clear")
            parser.print_help()
            
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        # 关闭连接
        store.close()

if __name__ == "__main__":
    main() 