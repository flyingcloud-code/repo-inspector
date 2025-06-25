"""Story 2.1.4 验收测试：调用图谱可视化服务

验证调用图谱可视化服务的完整功能，包括:
1. 从Neo4j查询调用关系数据
2. 生成Mermaid、JSON、ASCII格式输出
3. 导出文件和HTML查看器
4. CLI命令行界面
"""

import pytest
from pathlib import Path
import json
import tempfile

from src.code_learner.config.config_manager import ConfigManager
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.parser.c_parser import CParser
from src.code_learner.llm.call_graph_service import CallGraphService
from src.code_learner.cli.call_graph_cli import CallGraphCLI


@pytest.mark.integration
class TestStory214Acceptance:
    """Story 2.1.4 验收测试类"""
    
    @pytest.fixture(scope="class")
    def neo4j_store(self):
        """Neo4j存储连接"""
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
                pytest.skip("Neo4j not available for acceptance testing")
            
            yield store
            
        except Exception as e:
            pytest.skip(f"Neo4j connection failed: {e}")
        finally:
            if store:
                store.close()
    
    @pytest.fixture
    def test_data_setup(self, neo4j_store):
        """设置完整的测试数据"""
        # 清空数据库
        neo4j_store.clear_database()
        
        # 解析测试文件并存储
        parser = CParser()
        test_file = Path("tests/fixtures/complex.c")
        
        if test_file.exists():
            parsed_code = parser.parse_file(test_file)
            neo4j_store.store_parsed_code(parsed_code)
        else:
            # 如果测试文件不存在，手动创建测试数据
            test_relationships = [
                ("main", "print_sequence", "direct"),
                ("print_sequence", "fibonacci", "direct"),
                ("fibonacci", "fibonacci", "recursive"),
                ("main", "cleanup", "direct"),
                ("cleanup", "free", "direct")
            ]
            
            for caller, callee, call_type in test_relationships:
                neo4j_store.store_call_relationship(caller, callee, call_type)
        
        yield
        
        # 清理
        neo4j_store.clear_database()
    
    def test_ac_1_complete_call_graph_generation(self, neo4j_store, test_data_setup):
        """验收标准1：完整的调用图谱生成流程
        
        从Neo4j查询数据 → 构建图谱 → 验证数据结构
        """
        # 创建调用图谱服务
        service = CallGraphService(neo4j_store)
        
        # 构建调用图谱
        graph_data = service.build_graph("main", depth=3)
        
        # 验证数据结构
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert "stats" in graph_data
        assert graph_data["root"] == "main"
        assert graph_data["max_depth"] == 3
        
        # 验证统计信息
        stats = graph_data["stats"]
        assert "node_count" in stats
        assert "edge_count" in stats
        assert "root_function" in stats
        assert stats["root_function"] == "main"
        
        # 验证至少有根节点
        assert stats["node_count"] >= 1
        
        print(f"✅ 生成调用图谱成功：{stats['node_count']}个节点，{stats['edge_count']}条边")
    
    def test_ac_2_multiple_format_export(self, neo4j_store, test_data_setup, tmp_path):
        """验收标准2：多种格式导出功能
        
        支持Mermaid、JSON格式导出，文件内容正确
        """
        service = CallGraphService(neo4j_store)
        graph_data = service.build_graph("main", depth=2)
        
        # 测试Mermaid导出
        mermaid_file = tmp_path / "call_graph.md"
        success = service.export_to_file(graph_data, mermaid_file, "mermaid")
        assert success is True
        assert mermaid_file.exists()
        
        mermaid_content = mermaid_file.read_text(encoding='utf-8')
        assert "graph TD" in mermaid_content
        assert "main" in mermaid_content
        
        # 测试JSON导出
        json_file = tmp_path / "call_graph.json"
        success = service.export_to_file(graph_data, json_file, "json")
        assert success is True
        assert json_file.exists()
        
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        assert "nodes" in json_data
        assert "edges" in json_data
        assert "metadata" in json_data
        
        print(f"✅ 多格式导出成功：Mermaid({mermaid_file.stat().st_size}字节), JSON({json_file.stat().st_size}字节)")
    
    def test_ac_3_html_viewer_generation(self, neo4j_store, test_data_setup, tmp_path):
        """验收标准3：HTML交互式查看器生成
        
        生成包含Mermaid.js的HTML文件，可在浏览器中查看
        """
        service = CallGraphService(neo4j_store)
        graph_data = service.build_graph("main", depth=2)
        
        # 生成HTML查看器
        html_file = tmp_path / "call_graph_viewer.html"
        success = service.generate_html_viewer(graph_data, html_file)
        
        assert success is True
        assert html_file.exists()
        
        # 验证HTML内容
        html_content = html_file.read_text(encoding='utf-8')
        
        # 基本HTML结构
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "<head>" in html_content
        assert "<body>" in html_content
        
        # Mermaid.js集成
        assert "mermaid.min.js" in html_content
        assert "mermaid.initialize" in html_content
        assert 'class="mermaid"' in html_content
        
        # 图谱内容
        assert "main" in html_content
        assert "Function Call Graph" in html_content
        
        # 统计信息
        stats = graph_data.get('stats', {})
        if stats.get('node_count', 0) > 0:
            assert str(stats['node_count']) in html_content
        
        print(f"✅ HTML查看器生成成功：{html_file.stat().st_size}字节")
    
    def test_ac_4_ascii_tree_display(self, neo4j_store, test_data_setup):
        """验收标准4：ASCII树形显示
        
        生成适合终端显示的ASCII树形图
        """
        service = CallGraphService(neo4j_store)
        graph_data = service.build_graph("main", depth=2)
        
        # 生成ASCII树
        ascii_tree = service.print_ascii_tree(graph_data)
        
        # 验证ASCII树内容
        assert "📞 Function Call Tree" in ascii_tree
        assert "main" in ascii_tree
        assert "├──" in ascii_tree or "└──" in ascii_tree or "Root: main" in ascii_tree
        
        # 验证树形结构符号
        lines = ascii_tree.split('\n')
        assert len(lines) >= 2  # 至少有标题和根节点
        
        print(f"✅ ASCII树形显示生成成功：")
        print(ascii_tree)
    
    def test_ac_5_different_call_types_visualization(self, neo4j_store, test_data_setup):
        """验收标准5：不同调用类型的可视化
        
        验证direct、pointer、member、recursive调用类型的正确显示
        """
        service = CallGraphService(neo4j_store)
        graph_data = service.build_graph("main", depth=3)
        
        # 生成Mermaid图谱
        mermaid_content = service.to_mermaid(graph_data)
        
        # 检查是否包含不同的调用类型标记
        # 注意：实际的调用类型取决于测试数据
        call_type_patterns = [
            "-->",      # direct call
            "==>",      # pointer call  
            "-.->",     # recursive call
            "|",        # call type labels
        ]
        
        found_patterns = [pattern for pattern in call_type_patterns if pattern in mermaid_content]
        assert len(found_patterns) > 0, f"应该找到至少一种调用类型模式，实际内容：{mermaid_content[:200]}..."
        
        print(f"✅ 调用类型可视化成功：发现{len(found_patterns)}种模式")
    
    def test_ac_6_error_handling_and_edge_cases(self, neo4j_store, test_data_setup):
        """验收标准6：错误处理和边界情况
        
        验证不存在的函数、空数据库等边界情况的处理
        """
        service = CallGraphService(neo4j_store)
        
        # 测试不存在的函数
        result = service.build_graph("nonexistent_function", depth=2)
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["root"] == "nonexistent_function"
        
        # 测试空图谱的格式转换
        mermaid_content = service.to_mermaid(result)
        assert "graph TD" in mermaid_content
        
        json_content = service.to_json(result)
        json_data = json.loads(json_content)
        assert json_data["nodes"] == []
        assert json_data["edges"] == []
        
        ascii_tree = service.print_ascii_tree(result)
        assert "nonexistent_function" in ascii_tree
        
        print("✅ 错误处理和边界情况验证成功")
    
    def test_ac_7_performance_with_reasonable_data(self, neo4j_store, test_data_setup):
        """验收标准7：合理数据量的性能测试
        
        验证处理中等规模数据时的性能表现
        """
        import time
        
        service = CallGraphService(neo4j_store)
        
        # 测试不同深度的查询性能
        depths = [1, 2, 3, 5]
        for depth in depths:
            start_time = time.time()
            result = service.build_graph("main", depth=depth)
            query_time = time.time() - start_time
            
            # 基本性能要求：查询时间应该在合理范围内
            assert query_time < 10.0, f"深度{depth}查询时间过长：{query_time:.2f}秒"
            
            print(f"✅ 深度{depth}查询性能：{query_time:.3f}秒，{result['stats']['node_count']}节点")
    
    def test_ac_8_integration_with_existing_data(self, neo4j_store, test_data_setup):
        """验收标准8：与现有数据的集成
        
        验证与Story 2.1.3存储的调用关系数据的兼容性
        """
        service = CallGraphService(neo4j_store)
        
        # 构建图谱
        graph_data = service.build_graph("main", depth=2)
        
        # 验证数据结构兼容性
        for node in graph_data.get('nodes', []):
            assert 'id' in node
            assert 'name' in node
            # file_path可能为None，这是允许的
        
        for edge in graph_data.get('edges', []):
            assert 'source' in edge
            assert 'target' in edge
            # call_type和line_no可能不存在，这是允许的
        
        # 验证能够生成所有格式
        mermaid_ok = True
        json_ok = True
        ascii_ok = True
        
        try:
            service.to_mermaid(graph_data)
        except Exception:
            mermaid_ok = False
        
        try:
            service.to_json(graph_data)
        except Exception:
            json_ok = False
        
        try:
            service.print_ascii_tree(graph_data)
        except Exception:
            ascii_ok = False
        
        assert mermaid_ok, "Mermaid格式转换失败"
        assert json_ok, "JSON格式转换失败"
        assert ascii_ok, "ASCII树格式转换失败"
        
        print("✅ 与现有数据集成验证成功")


if __name__ == "__main__":
    # 运行验收测试
    pytest.main([__file__, "-v", "-s"]) 