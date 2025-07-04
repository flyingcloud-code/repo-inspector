"""
状态检查命令模块

检查系统各组件的健康状况和统计信息
"""

import logging
from typing import Dict, Any

from ..project.project_registry import ProjectRegistry
from ..config.config_manager import ConfigManager
from ..storage.neo4j_store import Neo4jGraphStore
from ..storage.chroma_store import ChromaVectorStore
from ..llm.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class StatusCommands:
    """状态检查命令处理器"""
    
    def __init__(self):
        """初始化状态检查命令处理器"""
        self.registry = ProjectRegistry()
        self.config_manager = ConfigManager()
    
    def check_status(self, verbose: bool = False) -> int:
        """
        检查系统状态
        
        Args:
            verbose: 是否显示详细信息
            
        Returns:
            int: 退出码（0表示成功）
        """
        try:
            print("🔍 系统状态检查")
            print("=" * 50)
            
            # 检查项目注册表
            project_status = self._check_project_registry()
            
            # 检查数据库连接
            database_status = self._check_database()
            
            # 检查向量存储
            vector_status = self._check_vector_store()
            
            # 检查嵌入模型
            embedding_status = self._check_embedding_model()
            
            # 检查LLM服务
            llm_status = self._check_llm_service()
            
            # 汇总状态
            all_statuses = [
                project_status,
                database_status,
                vector_status,
                embedding_status,
                llm_status
            ]
            
            healthy_count = sum(1 for status in all_statuses if status.get('healthy', False))
            total_count = len(all_statuses)
            
            print()
            print("📊 总体状态:")
            if healthy_count == total_count:
                print("✅ 所有组件正常运行")
                overall_status = "healthy"
            elif healthy_count > 0:
                print(f"⚠️  部分组件异常 ({healthy_count}/{total_count} 正常)")
                overall_status = "partial"
            else:
                print("❌ 所有组件异常")
                overall_status = "unhealthy"
            
            # 详细信息
            if verbose:
                print()
                print("📋 详细信息:")
                print("-" * 30)
                
                self._print_detailed_status("项目注册表", project_status)
                self._print_detailed_status("Neo4j数据库", database_status)
                self._print_detailed_status("向量存储", vector_status)
                self._print_detailed_status("嵌入模型", embedding_status)
                self._print_detailed_status("LLM服务", llm_status)
            
            # 建议
            print()
            print("💡 建议:")
            if overall_status == "healthy":
                print("   系统运行正常，可以开始使用！")
                print("   使用 'code-learner project create' 创建第一个项目")
            else:
                print("   请检查异常组件的配置和连接")
                print("   确保Neo4j和相关服务已启动")
            
            return 0 if overall_status != "unhealthy" else 1
            
        except Exception as e:
            logger.error(f"状态检查失败: {e}")
            print(f"❌ 状态检查出错: {e}")
            return 1
    
    def _check_project_registry(self) -> Dict[str, Any]:
        """检查项目注册表状态"""
        try:
            projects = self.registry.list_projects()
            
            status = {
                'healthy': True,
                'component': 'project_registry',
                'message': f'正常 ({len(projects)} 个项目)',
                'details': {
                    'project_count': len(projects),
                    'registry_file': str(self.registry.registry_file)
                }
            }
            
            print(f"✅ 项目注册表: {status['message']}")
            return status
            
        except Exception as e:
            status = {
                'healthy': False,
                'component': 'project_registry',
                'message': f'异常: {e}',
                'details': {'error': str(e)}
            }
            print(f"❌ 项目注册表: {status['message']}")
            return status
    
    def _check_database(self) -> Dict[str, Any]:
        """检查Neo4j数据库状态"""
        try:
            config = self.config_manager.get_config()
            
            # 创建测试连接
            graph_store = Neo4jGraphStore(
                uri=config.database.neo4j_uri,
                user=config.database.neo4j_user,
                password=config.database.neo4j_password
            )
            
            if graph_store.connect():
                # 获取数据库统计信息
                try:
                    # 查询节点和关系数量
                    node_count_result = graph_store.driver.execute_query(
                        "MATCH (n) RETURN count(n) as node_count"
                    )
                    node_count = node_count_result.records[0]['node_count']
                    
                    relation_count_result = graph_store.driver.execute_query(
                        "MATCH ()-[r]->() RETURN count(r) as relation_count"
                    )
                    relation_count = relation_count_result.records[0]['relation_count']
                    
                    graph_store.close()
                    
                    status = {
                        'healthy': True,
                        'component': 'neo4j_database',
                        'message': f'正常 ({node_count} 节点, {relation_count} 关系)',
                        'details': {
                            'uri': config.database.neo4j_uri,
                            'node_count': node_count,
                            'relation_count': relation_count
                        }
                    }
                    
                except Exception as e:
                    graph_store.close()
                    status = {
                        'healthy': True,
                        'component': 'neo4j_database',
                        'message': '连接正常，但无法获取统计信息',
                        'details': {
                            'uri': config.database.neo4j_uri,
                            'warning': str(e)
                        }
                    }
            else:
                status = {
                    'healthy': False,
                    'component': 'neo4j_database',
                    'message': '连接失败',
                    'details': {
                        'uri': config.database.neo4j_uri,
                        'error': '无法建立连接'
                    }
                }
            
            print(f"{'✅' if status['healthy'] else '❌'} Neo4j数据库: {status['message']}")
            return status
            
        except Exception as e:
            status = {
                'healthy': False,
                'component': 'neo4j_database',
                'message': f'异常: {e}',
                'details': {'error': str(e)}
            }
            print(f"❌ Neo4j数据库: {status['message']}")
            return status
    
    def _check_vector_store(self) -> Dict[str, Any]:
        """检查向量存储状态"""
        try:
            # 创建测试向量存储
            vector_store = ChromaVectorStore(project_id="test")
            
            # ChromaVectorStore在构造函数中自动初始化，检查client是否可用
            if vector_store.client is not None:
                # 获取集合信息
                try:
                    collections = vector_store.client.list_collections()
                    collection_count = len(collections)
                    
                    status = {
                        'healthy': True,
                        'component': 'vector_store',
                        'message': f'正常 ({collection_count} 个集合)',
                        'details': {
                            'collection_count': collection_count,
                            'collections': [col.name for col in collections],
                            'persist_directory': str(vector_store.persist_directory)
                        }
                    }
                    
                except Exception as e:
                    status = {
                        'healthy': True,
                        'component': 'vector_store',
                        'message': '连接正常，但无法获取集合信息',
                        'details': {'warning': str(e)}
                    }
            else:
                status = {
                    'healthy': False,
                    'component': 'vector_store',
                    'message': '初始化失败',
                    'details': {'error': '无法初始化ChromaDB客户端'}
                }
            
            print(f"{'✅' if status['healthy'] else '❌'} 向量存储: {status['message']}")
            return status
            
        except Exception as e:
            status = {
                'healthy': False,
                'component': 'vector_store',
                'message': f'异常: {e}',
                'details': {'error': str(e)}
            }
            print(f"❌ 向量存储: {status['message']}")
            return status
    
    def _check_embedding_model(self) -> Dict[str, Any]:
        """检查嵌入模型状态"""
        try:
            # 检查配置是否正确，但不实际初始化模型（避免下载）
            config = self.config_manager.get_config()
            model_name = getattr(config.llm, 'embedding_model_name', 'unknown')
            
            # 检查sentence_transformers是否可用
            try:
                import sentence_transformers
                transformers_available = True
            except ImportError:
                transformers_available = False
            
            if transformers_available:
                # 检查模型缓存目录是否存在
                import os
                from pathlib import Path
                cache_dir = Path.home() / '.cache' / 'torch' / 'sentence_transformers'
                model_cached = cache_dir.exists() and any(cache_dir.iterdir())
                
                status = {
                    'healthy': True,
                    'component': 'embedding_model',
                    'message': f'配置正常 (模型: {model_name})',
                    'details': {
                        'model_name': model_name,
                        'transformers_available': transformers_available,
                        'model_cached': model_cached,
                        'cache_dir': str(cache_dir)
                    }
                }
                
                if not model_cached:
                    status['message'] += ' - 首次使用需下载'
                    
            else:
                status = {
                    'healthy': False,
                    'component': 'embedding_model',
                    'message': 'sentence_transformers未安装',
                    'details': {'error': '缺少必需的依赖包'}
                }
            
            print(f"{'✅' if status['healthy'] else '❌'} 嵌入模型: {status['message']}")
            return status
            
        except Exception as e:
            status = {
                'healthy': False,
                'component': 'embedding_model',
                'message': f'异常: {e}',
                'details': {'error': str(e)}
            }
            print(f"❌ 嵌入模型: {status['message']}")
            return status
    
    def _check_llm_service(self) -> Dict[str, Any]:
        """检查LLM服务状态"""
        try:
            # 获取聊天机器人
            chatbot = ServiceFactory.get_chatbot()
            
            if chatbot:
                # 检查API密钥配置
                config = self.config_manager.get_config()
                api_key = getattr(config.llm, 'chat_api_key', None)
                
                if api_key and api_key.strip():
                    status = {
                        'healthy': True,
                        'component': 'llm_service',
                        'message': '配置正常',
                        'details': {
                            'model_name': getattr(config.llm, 'chat_model', 'unknown'),
                            'api_configured': True,
                            'base_url': getattr(config.llm, 'chat_base_url', 'unknown')
                        }
                    }
                else:
                    status = {
                        'healthy': False,
                        'component': 'llm_service',
                        'message': 'API密钥未配置',
                        'details': {'error': 'OPENROUTER_API_KEY未设置'}
                    }
            else:
                status = {
                    'healthy': False,
                    'component': 'llm_service',
                    'message': '服务未初始化',
                    'details': {'error': '无法创建聊天机器人实例'}
                }
            
            print(f"{'✅' if status['healthy'] else '❌'} LLM服务: {status['message']}")
            return status
            
        except Exception as e:
            status = {
                'healthy': False,
                'component': 'llm_service',
                'message': f'异常: {e}',
                'details': {'error': str(e)}
            }
            print(f"❌ LLM服务: {status['message']}")
            return status
    
    def _print_detailed_status(self, component_name: str, status: Dict[str, Any]):
        """打印组件详细状态"""
        print(f"\n🔧 {component_name}:")
        print(f"   状态: {'正常' if status['healthy'] else '异常'}")
        print(f"   信息: {status['message']}")
        
        details = status.get('details', {})
        if details:
            print("   详细信息:")
            for key, value in details.items():
                if isinstance(value, list):
                    print(f"     {key}: {len(value)} 项")
                    if len(value) <= 5:  # 只显示前5项
                        for item in value:
                            print(f"       - {item}")
                    else:
                        for item in value[:5]:
                            print(f"       - {item}")
                        print(f"       ... 还有 {len(value) - 5} 项")
                else:
                    print(f"     {key}: {value}") 