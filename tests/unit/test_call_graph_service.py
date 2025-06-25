"""调用图谱服务单元测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import json

from src.code_learner.llm.call_graph_service import CallGraphService
from src.code_learner.core.exceptions import ServiceError


class TestCallGraphService:
    """调用图谱服务测试类"""
    
    @pytest.fixture
    def mock_graph_store(self):
        """模拟图数据库存储"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_graph_store):
        """创建服务实例"""
        return CallGraphService(mock_graph_store)
    
    @pytest.fixture
    def sample_graph_data(self):
        """示例图谱数据"""
        return {
            'nodes': [
                {'id': 'main', 'name': 'main', 'file_path': 'main.c'},
                {'id': 'helper', 'name': 'helper', 'file_path': 'utils.c'}
            ],
            'edges': [
                {'source': 'main', 'target': 'helper', 'call_type': 'direct', 'line_no': 10}
            ],
            'root': 'main',
            'max_depth': 3
        }
    
    def test_build_graph_basic(self, service, mock_graph_store):
        """测试基本的图谱构建"""
        # 设置mock返回值
        mock_graph_store.query_call_graph.return_value = {
            'nodes': [{'id': 'main', 'name': 'main', 'file_path': 'main.c'}],
            'edges': [],
            'root': 'main',
            'max_depth': 1
        }
        
        # 调用方法
        result = service.build_graph('main', 1)
        
        # 验证结果
        assert result['root'] == 'main'
        assert result['max_depth'] == 1
        assert 'stats' in result
        assert result['stats']['node_count'] == 1
        assert result['stats']['edge_count'] == 0
        assert result['stats']['root_function'] == 'main'
        
        # 验证mock调用
        mock_graph_store.query_call_graph.assert_called_once_with('main', 1)
    
    def test_build_graph_with_filter(self, service, mock_graph_store):
        """测试带过滤的图谱构建"""
        # 设置mock返回值
        mock_graph_store.query_call_graph.return_value = {
            'nodes': [
                {'id': 'main', 'name': 'main', 'file_path': 'main.c'},
                {'id': 'helper', 'name': 'helper', 'file_path': 'utils.c'}
            ],
            'edges': [
                {'source': 'main', 'target': 'helper', 'call_type': 'direct'}
            ],
            'root': 'main',
            'max_depth': 2
        }
        
        # 调用方法
        result = service.build_graph('main', 2)
        
        # 验证结果
        assert result['stats']['node_count'] == 2
        assert result['stats']['edge_count'] == 1
        mock_graph_store.query_call_graph.assert_called_once_with('main', 2)
    
    def test_mermaid_output_format(self, service, sample_graph_data):
        """测试Mermaid输出格式"""
        mermaid_content = service.to_mermaid(sample_graph_data)
        
        # 验证Mermaid语法
        assert 'graph TD' in mermaid_content
        assert 'main["main<br/><small>main.c</small>"]' in mermaid_content
        assert 'helper["helper<br/><small>utils.c</small>"]' in mermaid_content
        assert 'main --> helper' in mermaid_content
        assert 'classDef rootNode' in mermaid_content
        assert 'class main rootNode' in mermaid_content
    
    def test_mermaid_call_types(self, service):
        """测试不同调用类型的Mermaid输出"""
        graph_data = {
            'nodes': [
                {'id': 'caller', 'name': 'caller', 'file_path': 'test.c'},
                {'id': 'target1', 'name': 'target1', 'file_path': 'test.c'},
                {'id': 'target2', 'name': 'target2', 'file_path': 'test.c'},
                {'id': 'target3', 'name': 'target3', 'file_path': 'test.c'},
                {'id': 'target4', 'name': 'target4', 'file_path': 'test.c'}
            ],
            'edges': [
                {'source': 'caller', 'target': 'target1', 'call_type': 'direct'},
                {'source': 'caller', 'target': 'target2', 'call_type': 'pointer'},
                {'source': 'caller', 'target': 'target3', 'call_type': 'member'},
                {'source': 'caller', 'target': 'target4', 'call_type': 'recursive'}
            ],
            'root': 'caller'
        }
        
        mermaid_content = service.to_mermaid(graph_data)
        
        # 验证不同调用类型的箭头样式
        assert 'caller --> target1' in mermaid_content  # direct
        assert 'caller ==>|pointer| target2' in mermaid_content  # pointer
        assert 'caller -->|member| target3' in mermaid_content  # member
        assert 'caller -.->|recursive| target4' in mermaid_content  # recursive
    
    def test_json_output_nodes_edges(self, service, sample_graph_data):
        """测试JSON输出的节点和边结构"""
        json_content = service.to_json(sample_graph_data)
        
        # 解析JSON
        data = json.loads(json_content)
        
        # 验证结构
        assert 'nodes' in data
        assert 'edges' in data
        assert 'metadata' in data
        assert data['metadata']['format'] == 'call_graph_json'
        assert data['metadata']['version'] == '1.0'
        
        # 验证节点
        assert len(data['nodes']) == 2
        assert data['nodes'][0]['name'] == 'main'
        
        # 验证边
        assert len(data['edges']) == 1
        assert data['edges'][0]['source'] == 'main'
        assert data['edges'][0]['target'] == 'helper'
    
    def test_export_to_file_mermaid(self, service, sample_graph_data, tmp_path):
        """测试导出Mermaid文件"""
        output_path = tmp_path / "test_graph.md"
        
        # 导出文件
        result = service.export_to_file(sample_graph_data, output_path, "mermaid")
        
        # 验证结果
        assert result is True
        assert output_path.exists()
        
        # 验证文件内容
        content = output_path.read_text(encoding='utf-8')
        assert 'graph TD' in content
        assert 'main --> helper' in content
    
    def test_export_to_file_json(self, service, sample_graph_data, tmp_path):
        """测试导出JSON文件"""
        output_path = tmp_path / "test_graph.json"
        
        # 导出文件
        result = service.export_to_file(sample_graph_data, output_path, "json")
        
        # 验证结果
        assert result is True
        assert output_path.exists()
        
        # 验证文件内容
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert 'nodes' in data
        assert 'edges' in data
    
    def test_export_unsupported_format(self, service, sample_graph_data, tmp_path):
        """测试不支持的导出格式"""
        output_path = tmp_path / "test_graph.xyz"
        
        # 应该抛出异常
        with pytest.raises(ServiceError):
            service.export_to_file(sample_graph_data, output_path, "unsupported")
    
    def test_generate_html_viewer(self, service, sample_graph_data, tmp_path):
        """测试生成HTML查看器"""
        output_path = tmp_path / "viewer.html"
        
        # 生成HTML
        result = service.generate_html_viewer(sample_graph_data, output_path)
        
        # 验证结果
        assert result is True
        assert output_path.exists()
        
        # 验证HTML内容
        content = output_path.read_text(encoding='utf-8')
        assert '<!DOCTYPE html>' in content
        assert 'Function Call Graph' in content
        assert 'mermaid' in content.lower()
        assert 'main' in content  # 根函数名
    
    def test_print_ascii_tree(self, service, sample_graph_data):
        """测试ASCII树形显示"""
        ascii_tree = service.print_ascii_tree(sample_graph_data)
        
        # 验证ASCII树内容
        assert '📞 Function Call Tree' in ascii_tree
        assert 'main' in ascii_tree
        assert 'helper' in ascii_tree
        assert '├──' in ascii_tree
    
    def test_print_ascii_tree_recursive(self, service):
        """测试递归调用的ASCII树显示"""
        graph_data = {
            'nodes': [
                {'id': 'recursive_func', 'name': 'recursive_func', 'file_path': 'test.c'}
            ],
            'edges': [
                {'source': 'recursive_func', 'target': 'recursive_func', 'call_type': 'recursive'}
            ],
            'root': 'recursive_func'
        }
        
        ascii_tree = service.print_ascii_tree(graph_data)
        
        # 验证递归标记
        assert 'recursive_func' in ascii_tree
        assert '(recursive)' in ascii_tree
    
    def test_sanitize_node_id(self, service):
        """测试节点ID清理"""
        # 测试特殊字符清理
        assert service._sanitize_node_id('func-name') == 'func_name'
        assert service._sanitize_node_id('func.name') == 'func_name'
        assert service._sanitize_node_id('func name') == 'func_name'
        
        # 测试数字开头的处理
        assert service._sanitize_node_id('123func') == 'fn_123func'
        
        # 测试空字符串
        assert service._sanitize_node_id('') == 'unknown_node'
    
    def test_build_graph_error_handling(self, service, mock_graph_store):
        """测试图谱构建错误处理"""
        # 设置mock抛出异常
        mock_graph_store.query_call_graph.side_effect = Exception("Database error")
        
        # 应该抛出ServiceError
        with pytest.raises(ServiceError) as exc_info:
            service.build_graph('main')
        
        assert "Failed to build call graph" in str(exc_info.value)
    
    def test_mermaid_conversion_error_handling(self, service):
        """测试Mermaid转换错误处理"""
        # 使用无效的图谱数据
        invalid_data = {'invalid': 'data'}
        
        # 应该抛出ServiceError
        with pytest.raises(ServiceError) as exc_info:
            service.to_mermaid(invalid_data)
        
        assert "Failed to convert graph to Mermaid" in str(exc_info.value)
    
    def test_json_conversion_error_handling(self, service):
        """测试JSON转换错误处理"""
        # 创建不可序列化的数据
        class UnserializableClass:
            pass
        
        invalid_data = {
            'nodes': [UnserializableClass()],
            'edges': []
        }
        
        # 应该抛出ServiceError
        with pytest.raises(ServiceError) as exc_info:
            service.to_json(invalid_data)
        
        assert "Failed to convert graph to JSON" in str(exc_info.value) 