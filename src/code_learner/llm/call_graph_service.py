"""调用图谱可视化服务

提供函数调用关系的图形化展示功能，支持多种输出格式。
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging

from ..core.interfaces import IGraphStore
from ..core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class CallGraphService:
    """调用图谱可视化服务
    
    负责从Neo4j查询调用关系并转换为可视化格式
    """
    
    def __init__(self, graph_store: IGraphStore):
        """初始化服务
        
        Args:
            graph_store: 图数据库存储接口
        """
        self.graph_store = graph_store
        
    def build_graph(self, root: str, depth: int = 3) -> Dict[str, Any]:
        """构建调用图谱数据
        
        Args:
            root: 根函数名
            depth: 查询深度
            
        Returns:
            Dict[str, Any]: 图谱数据结构
            
        Raises:
            ServiceError: 构建失败时抛出异常
        """
        try:
            logger.info(f"🔍 Building call graph from root '{root}' with depth {depth}")
            
            # 从Neo4j查询调用图数据
            graph_data = self.graph_store.query_call_graph(root, depth)
            
            logger.debug(f"Retrieved {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")
            
            # 添加统计信息
            graph_data.update({
                'stats': {
                    'node_count': len(graph_data['nodes']),
                    'edge_count': len(graph_data['edges']),
                    'max_depth': depth,
                    'root_function': root
                }
            })
            
            return graph_data
            
        except Exception as e:
            error_msg = f"Failed to build call graph for '{root}': {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def to_mermaid(self, graph_data: Dict[str, Any]) -> str:
        """转换为Mermaid格式
        
        Args:
            graph_data: 图谱数据
            
        Returns:
            str: Mermaid图形定义
        """
        try:
            logger.debug("🎨 Converting graph to Mermaid format")
            
            lines = ["graph TD"]
            
            # 添加节点定义
            for node in graph_data['nodes']:
                node_id = self._sanitize_node_id(node['id'])
                node_label = f"{node['name']}"
                if 'file_path' in node and node['file_path'] and node['file_path'] != 'unknown':
                    file_name = Path(node['file_path']).name
                    node_label += f"<br/><small>{file_name}</small>"
                
                lines.append(f'    {node_id}["{node_label}"]')
            
            # 添加边定义
            for edge in graph_data['edges']:
                source_id = self._sanitize_node_id(edge['source'])
                target_id = self._sanitize_node_id(edge['target'])
                call_type = edge.get('call_type', 'direct')
                
                # 根据调用类型选择不同的箭头样式
                if call_type == 'recursive':
                    lines.append(f'    {source_id} -.->|recursive| {target_id}')
                elif call_type == 'pointer':
                    lines.append(f'    {source_id} ==>|pointer| {target_id}')
                elif call_type == 'member':
                    lines.append(f'    {source_id} -->|member| {target_id}')
                else:
                    lines.append(f'    {source_id} --> {target_id}')
            
            # 添加样式定义
            root_id = self._sanitize_node_id(graph_data.get('root', ''))
            if root_id:
                lines.append(f'    classDef rootNode fill:#e1f5fe,stroke:#01579b,stroke-width:3px')
                lines.append(f'    class {root_id} rootNode')
            
            mermaid_content = '\n'.join(lines)
            logger.debug(f"Generated Mermaid diagram with {len(lines)} lines")
            
            return mermaid_content
            
        except Exception as e:
            error_msg = f"Failed to convert graph to Mermaid: {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def to_json(self, graph_data: Dict[str, Any]) -> str:
        """转换为JSON格式
        
        Args:
            graph_data: 图谱数据
            
        Returns:
            str: JSON字符串
        """
        try:
            logger.debug("📄 Converting graph to JSON format")
            
            # 确保数据可序列化
            serializable_data = {
                'nodes': graph_data.get('nodes', []),
                'edges': graph_data.get('edges', []),
                'stats': graph_data.get('stats', {}),
                'metadata': {
                    'format': 'call_graph_json',
                    'version': '1.0'
                }
            }
            
            json_content = json.dumps(serializable_data, indent=2, ensure_ascii=False)
            logger.debug(f"Generated JSON with {len(serializable_data['nodes'])} nodes")
            
            return json_content
            
        except Exception as e:
            error_msg = f"Failed to convert graph to JSON: {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def export_to_file(self, graph_data: Dict[str, Any], output_path: Path, format_type: str = "mermaid") -> bool:
        """导出图谱到文件
        
        Args:
            graph_data: 图谱数据
            output_path: 输出文件路径
            format_type: 格式类型 ('mermaid', 'json')
            
        Returns:
            bool: 导出是否成功
        """
        try:
            logger.info(f"📁 Exporting call graph to {output_path} in {format_type} format")
            
            if format_type.lower() == "mermaid":
                content = self.to_mermaid(graph_data)
                suffix = ".md"
            elif format_type.lower() == "json":
                content = self.to_json(graph_data)
                suffix = ".json"
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            # 确保文件有正确的扩展名
            if not output_path.suffix:
                output_path = output_path.with_suffix(suffix)
            
            # 创建目录（如果不存在）
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ Successfully exported call graph to {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to export graph to {output_path}: {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def generate_html_viewer(self, graph_data: Dict[str, Any], output_path: Path) -> bool:
        """生成HTML交互式查看器
        
        Args:
            graph_data: 图谱数据
            output_path: 输出HTML文件路径
            
        Returns:
            bool: 生成是否成功
        """
        try:
            logger.info(f"🌐 Generating HTML viewer for call graph at {output_path}")
            
            mermaid_content = self.to_mermaid(graph_data)
            
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Function Call Graph - {graph_data.get('root', 'Unknown')}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        #mermaid-diagram {{
            text-align: center;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Function Call Graph</h1>
            <p>Root Function: <strong>{graph_data.get('root', 'Unknown')}</strong></p>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{graph_data.get('stats', {}).get('node_count', 0)}</div>
                <div class="stat-label">Functions</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{graph_data.get('stats', {}).get('edge_count', 0)}</div>
                <div class="stat-label">Calls</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{graph_data.get('stats', {}).get('max_depth', 0)}</div>
                <div class="stat-label">Max Depth</div>
            </div>
        </div>
        
        <div id="mermaid-diagram">
            <pre class="mermaid">
{mermaid_content}
            </pre>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true
            }}
        }});
    </script>
</body>
</html>"""
            
            # 创建目录（如果不存在）
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入HTML文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            logger.info(f"✅ Successfully generated HTML viewer at {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to generate HTML viewer: {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def print_ascii_tree(self, graph_data: Dict[str, Any]) -> str:
        """生成ASCII树形显示
        
        Args:
            graph_data: 图谱数据
            
        Returns:
            str: ASCII树形图
        """
        try:
            logger.debug("🌳 Generating ASCII tree representation")
            
            # 构建调用关系映射
            call_map = {}
            for edge in graph_data.get('edges', []):
                caller = edge['source']
                callee = edge['target']
                if caller not in call_map:
                    call_map[caller] = []
                call_map[caller].append(callee)
            
            # 递归构建树形结构
            root = graph_data.get('root', '')
            if not root:
                return "No root function specified"
            
            def build_tree(node: str, prefix: str = "", visited: set = None) -> List[str]:
                if visited is None:
                    visited = set()
                
                if node in visited:
                    return [f"{prefix}├── {node} (recursive)"]
                
                visited.add(node)
                lines = [f"{prefix}├── {node}"]
                
                children = call_map.get(node, [])
                for i, child in enumerate(children):
                    is_last = (i == len(children) - 1)
                    child_prefix = prefix + ("    " if is_last else "│   ")
                    lines.extend(build_tree(child, child_prefix, visited.copy()))
                
                return lines
            
            tree_lines = [f"📞 Function Call Tree (Root: {root})"]
            tree_lines.extend(build_tree(root))
            
            ascii_tree = '\n'.join(tree_lines)
            logger.debug(f"Generated ASCII tree with {len(tree_lines)} lines")
            
            return ascii_tree
            
        except Exception as e:
            error_msg = f"Failed to generate ASCII tree: {e}"
            logger.error(f"❌ {error_msg}")
            raise ServiceError(error_msg)
    
    def _sanitize_node_id(self, node_id: str) -> str:
        """清理节点ID，确保符合Mermaid语法
        
        Args:
            node_id: 原始节点ID
            
        Returns:
            str: 清理后的节点ID
        """
        # 移除或替换特殊字符
        sanitized = node_id.replace('-', '_').replace('.', '_').replace(' ', '_')
        # 确保以字母开头
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'fn_' + sanitized
        return sanitized or 'unknown_node' 