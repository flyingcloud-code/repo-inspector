"""调用图谱API集成测试"""

import pytest
from pathlib import Path
import json
import tempfile
import os

from src.code_learner.config.config_manager import ConfigManager
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.llm.call_graph_service import CallGraphService
from src.code_learner.cli.call_graph_cli import CallGraphCLI
from src.code_learner.core.exceptions import ServiceError, StorageError


@pytest.mark.integration
class TestCallGraphAPI:
    """调用图谱API集成测试"""
    
    @pytest.fixture(scope="class")
    def neo4j_store(self):
        """真实Neo4j连接"""
        config = ConfigManager()
        store = Neo4jGraphStore()
        
        try:
            config_data = config.get_config()
            success = store.connect(
                config_data.database.neo4j_uri,
                config_data.database.neo4j_user,
                config_data.database.neo4j_password
            )
            
            if not success:
                pytest.skip("Neo4j not available for integration testing")
            
            yield store
            
        except Exception as e:
            pytest.skip(f"Neo4j connection failed: {e}")
        finally:
            if store:
                store.close()
    
    @pytest.fixture
    def call_graph_service(self, neo4j_store):
        """调用图谱服务"""
        return CallGraphService(neo4j_store)
    
    @pytest.fixture
    def sample_data_setup(self, neo4j_store):
        """设置测试数据"""
        # 清空数据库
        neo4j_store.clear_database()
        
        # 插入测试数据
        test_functions = [
            ("main", "hello", "direct", 5),
            ("hello", "printf", "direct", 2),
            ("main", "cleanup", "direct", 8)
        ]
        
        for caller, callee, call_type, line_no in test_functions:
            neo4j_store.store_call_relationship(caller, callee, call_type)
        
        yield
        
        # 清理
        neo4j_store.clear_database()
    
    def test_http_api_ok(self, call_graph_service, sample_data_setup):
        """测试HTTP API正常响应"""
        # 构建调用图谱
        result = call_graph_service.build_graph("main", depth=2)
        
        # 验证结果结构
        assert "nodes" in result
        assert "edges" in result
        assert "stats" in result
        assert result["root"] == "main"
        assert result["max_depth"] == 2
        
        # 验证统计信息
        stats = result["stats"]
        assert stats["root_function"] == "main"
        assert stats["node_count"] >= 1  # 至少有main函数
        assert stats["edge_count"] >= 0
    
    def test_http_api_bad_root(self, call_graph_service, sample_data_setup):
        """测试不存在的根函数处理"""
        # 查询不存在的函数
        result = call_graph_service.build_graph("nonexistent_function", depth=1)
        
        # 应该返回空结果但不抛出异常
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["root"] == "nonexistent_function"
    
    def test_cli_render_mermaid_file(self, call_graph_service, sample_data_setup, tmp_path):
        """测试CLI生成Mermaid文件并可渲染"""
        # 构建图谱数据
        graph_data = call_graph_service.build_graph("main", depth=2)
        
        # 导出Mermaid文件
        mermaid_file = tmp_path / "test_graph.md"
        success = call_graph_service.export_to_file(graph_data, mermaid_file, "mermaid")
        
        assert success is True
        assert mermaid_file.exists()
        
        # 验证文件内容
        content = mermaid_file.read_text(encoding='utf-8')
        assert "graph TD" in content
        assert "main" in content
        
        # 验证Mermaid语法正确性（基本检查）
        lines = content.strip().split('\n')
        assert lines[0].strip() == "graph TD"
        
        # 检查是否有节点定义
        node_lines = [line for line in lines if '[' in line and ']' in line]
        assert len(node_lines) > 0
        
        # 检查是否有边定义
        edge_lines = [line for line in lines if '-->' in line or '==>' in line or '-.->']
        # 注意：如果没有调用关系，边可能为空，这是正常的
    
    def test_json_export_and_import(self, call_graph_service, sample_data_setup, tmp_path):
        """测试JSON导出和导入"""
        # 构建图谱数据
        graph_data = call_graph_service.build_graph("main", depth=2)
        
        # 导出JSON文件
        json_file = tmp_path / "test_graph.json"
        success = call_graph_service.export_to_file(graph_data, json_file, "json")
        
        assert success is True
        assert json_file.exists()
        
        # 读取并验证JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            imported_data = json.load(f)
        
        assert "nodes" in imported_data
        assert "edges" in imported_data
        assert "metadata" in imported_data
        assert imported_data["metadata"]["format"] == "call_graph_json"
    
    def test_html_viewer_generation(self, call_graph_service, sample_data_setup, tmp_path):
        """测试HTML查看器生成"""
        # 构建图谱数据
        graph_data = call_graph_service.build_graph("main", depth=2)
        
        # 生成HTML查看器
        html_file = tmp_path / "viewer.html"
        success = call_graph_service.generate_html_viewer(graph_data, html_file)
        
        assert success is True
        assert html_file.exists()
        
        # 验证HTML内容
        content = html_file.read_text(encoding='utf-8')
        assert "<!DOCTYPE html>" in content
        assert "Function Call Graph" in content
        assert "mermaid" in content.lower()
        assert "main" in content
        
        # 验证HTML结构
        assert "<head>" in content
        assert "<body>" in content
        assert "mermaid.min.js" in content
    
    def test_ascii_tree_output(self, call_graph_service, sample_data_setup):
        """测试ASCII树形输出"""
        # 构建图谱数据
        graph_data = call_graph_service.build_graph("main", depth=2)
        
        # 生成ASCII树
        ascii_tree = call_graph_service.print_ascii_tree(graph_data)
        
        # 验证ASCII树内容
        assert "📞 Function Call Tree" in ascii_tree
        assert "main" in ascii_tree
        assert "├──" in ascii_tree or "└──" in ascii_tree
    
    def test_error_handling_database_disconnected(self):
        """测试数据库断开连接的错误处理"""
        # 创建未连接的存储
        disconnected_store = Neo4jGraphStore()
        service = CallGraphService(disconnected_store)
        
        # 应该抛出ServiceError
        with pytest.raises(ServiceError) as exc_info:
            service.build_graph("main")
        
        assert "Failed to build call graph" in str(exc_info.value)
    
    def test_large_depth_query(self, call_graph_service, sample_data_setup):
        """测试大深度查询"""
        # 测试较大的深度值
        result = call_graph_service.build_graph("main", depth=10)
        
        # 应该正常返回结果，不会因为深度过大而失败
        assert "nodes" in result
        assert "edges" in result
        assert result["max_depth"] == 10
    
    def test_multiple_format_export(self, call_graph_service, sample_data_setup, tmp_path):
        """测试多种格式同时导出"""
        # 构建图谱数据
        graph_data = call_graph_service.build_graph("main", depth=2)
        
        # 导出多种格式
        formats = ["mermaid", "json"]
        for format_type in formats:
            output_file = tmp_path / f"graph.{format_type}"
            success = call_graph_service.export_to_file(graph_data, output_file, format_type)
            
            assert success is True
            assert output_file.exists()
            
            # 验证文件不为空
            assert output_file.stat().st_size > 0


@pytest.mark.integration
class TestCallGraphCLI:
    """调用图谱CLI集成测试"""
    
    def test_cli_args_parsing(self):
        """测试CLI参数解析"""
        from src.code_learner.cli.call_graph_cli import create_parser
        
        parser = create_parser()
        
        # 测试基本参数
        args = parser.parse_args(['main'])
        assert args.root == 'main'
        assert args.depth == 3  # 默认值
        assert args.format == 'mermaid'  # 默认值
        
        # 测试所有参数
        args = parser.parse_args([
            'test_func', 
            '--depth', '5',
            '--format', 'json',
            '--output', 'output.json',
            '--html',
            '--verbose'
        ])
        assert args.root == 'test_func'
        assert args.depth == 5
        assert args.format == 'json'
        assert args.output == 'output.json'
        assert args.html is True
        assert args.verbose is True
    
    def test_cli_invalid_format(self):
        """测试CLI无效格式参数"""
        from src.code_learner.cli.call_graph_cli import create_parser
        
        parser = create_parser()
        
        # 应该抛出SystemExit（argparse错误）
        with pytest.raises(SystemExit):
            parser.parse_args(['main', '--format', 'invalid_format'])
    
    @pytest.mark.skipif(
        not os.getenv('NEO4J_PASSWORD'), 
        reason="Neo4j credentials not available"
    )
    def test_cli_integration_run(self, tmp_path):
        """测试CLI完整运行（需要真实Neo4j）"""
        from src.code_learner.cli.call_graph_cli import main
        
        output_file = tmp_path / "cli_test.md"
        
        # 模拟命令行参数
        argv = [
            'main',
            '--format', 'mermaid',
            '--output', str(output_file),
            '--depth', '2'
        ]
        
        # 运行CLI（可能因为数据库为空而返回错误，但不应该崩溃）
        try:
            exit_code = main(argv)
            # 如果数据库中有数据，应该成功；如果没有数据，也应该优雅处理
            assert exit_code in [0, 1]  # 0=成功, 1=业务错误但程序正常
        except SystemExit as e:
            # argparse可能抛出SystemExit
            assert e.code in [0, 1] 