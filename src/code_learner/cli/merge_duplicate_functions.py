#!/usr/bin/env python3
"""
合并重复的函数节点

识别并合并Neo4j数据库中的重复函数节点。
"""

import logging
import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_learner.storage.neo4j_store import Neo4jGraphStore
from neo4j import Result

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_duplicate_functions(store: Neo4jGraphStore) -> Dict[str, List[Dict[str, Any]]]:
    """查找重复的函数节点
    
    Args:
        store: Neo4j存储对象
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: 函数名到重复节点列表的映射
    """
    duplicates = {}
    
    try:
        with store.driver.session() as session:
            # 查询具有相同名称的函数节点
            query = """
            MATCH (f:Function)
            WITH f.name as name, collect(f) as functions
            WHERE size(functions) > 1
            RETURN name, size(functions) as count
            """
            
            result = session.run(query)
            
            for record in result:
                name = record["name"]
                count = record["count"]
                logger.info(f"发现重复函数: {name} (数量: {count})")
                
                # 获取每个重复函数的详细信息
                detail_query = """
                MATCH (f:Function {name: $name})
                OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
                RETURN id(f) as id, f.name as name, f.file_path as file_path, file.path as real_file_path,
                       f.start_line as start_line, f.end_line as end_line, f.code as code
                """
                
                detail_result = session.run(detail_query, {"name": name})
                functions = []
                
                for detail in detail_result:
                    functions.append({
                        "id": detail["id"],
                        "name": detail["name"],
                        "file_path": detail["file_path"],
                        "real_file_path": detail["real_file_path"],
                        "start_line": detail["start_line"],
                        "end_line": detail["end_line"],
                        "code": detail["code"]
                    })
                
                duplicates[name] = functions
    
    except Exception as e:
        logger.error(f"查找重复函数失败: {e}")
    
    return duplicates

def merge_duplicate_functions(store: Neo4jGraphStore, duplicates: Dict[str, List[Dict[str, Any]]]):
    """合并重复的函数节点
    
    Args:
        store: Neo4j存储对象
        duplicates: 函数名到重复节点列表的映射
    """
    try:
        with store.driver.session() as session:
            for name, functions in duplicates.items():
                if len(functions) <= 1:
                    continue
                
                logger.info(f"合并函数 {name} 的 {len(functions)} 个节点")
                
                # 选择保留的节点（优先选择有代码的节点）
                keep = None
                for func in functions:
                    if func["code"]:
                        keep = func
                        break
                
                # 如果没有找到有代码的节点，选择第一个
                if not keep:
                    keep = functions[0]
                
                logger.info(f"保留节点ID: {keep['id']}")
                
                # 合并其他节点到保留的节点
                for func in functions:
                    if func["id"] == keep["id"]:
                        continue
                    
                    logger.info(f"合并节点ID: {func['id']} 到 {keep['id']}")
                    
                    # 1. 转移调用关系（作为调用者）
                    transfer_caller_query = """
                    MATCH (other:Function)-[r:CALLS]->(func:Function)
                    WHERE id(func) = $from_id
                    MATCH (keep:Function)
                    WHERE id(keep) = $keep_id
                    MERGE (other)-[:CALLS]->(keep)
                    DELETE r
                    """
                    
                    session.run(transfer_caller_query, {"from_id": func["id"], "keep_id": keep["id"]})
                    
                    # 2. 转移调用关系（作为被调用者）
                    transfer_callee_query = """
                    MATCH (func:Function)-[r:CALLS]->(other:Function)
                    WHERE id(func) = $from_id
                    MATCH (keep:Function)
                    WHERE id(keep) = $keep_id
                    MERGE (keep)-[:CALLS]->(other)
                    DELETE r
                    """
                    
                    session.run(transfer_callee_query, {"from_id": func["id"], "keep_id": keep["id"]})
                    
                    # 3. 如果保留节点没有代码但当前节点有，则更新代码
                    if not keep["code"] and func["code"]:
                        update_code_query = """
                        MATCH (f:Function)
                        WHERE id(f) = $keep_id
                        SET f.code = $code
                        """
                        
                        session.run(update_code_query, {"keep_id": keep["id"], "code": func["code"]})
                        logger.info(f"更新保留节点的代码")
                    
                    # 4. 删除重复的节点
                    delete_query = """
                    MATCH (f:Function)
                    WHERE id(f) = $id
                    DETACH DELETE f
                    """
                    
                    session.run(delete_query, {"id": func["id"]})
                    logger.info(f"删除节点ID: {func['id']}")
    
    except Exception as e:
        logger.error(f"合并重复函数失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="合并重复的函数节点")
    parser.add_argument("--project-id", help="项目ID")
    parser.add_argument("--function-name", help="指定要处理的函数名，不指定则处理所有重复函数")
    
    args = parser.parse_args()
    
    store = Neo4jGraphStore(project_id=args.project_id)
    
    try:
        store.connect()
        
        # 查找重复的函数节点
        all_duplicates = find_duplicate_functions(store)
        
        # 如果指定了函数名，只处理该函数
        if args.function_name:
            if args.function_name in all_duplicates:
                duplicates = {args.function_name: all_duplicates[args.function_name]}
            else:
                logger.warning(f"未找到重复的函数: {args.function_name}")
                return
        else:
            duplicates = all_duplicates
        
        # 合并重复的函数节点
        merge_duplicate_functions(store, duplicates)
        
        logger.info("合并完成")
    
    except Exception as e:
        logger.error(f"执行失败: {e}")
    finally:
        store.close()

if __name__ == "__main__":
    main() 