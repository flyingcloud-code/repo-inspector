"""调用图谱CLI命令

提供命令行界面来生成和查看函数调用图谱
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import logging

from ..config.config_manager import ConfigManager
from ..storage.neo4j_store import Neo4jGraphStore
from ..llm.call_graph_service import CallGraphService
from ..core.exceptions import ServiceError, StorageError

logger = logging.getLogger(__name__)


class CallGraphCLI:
    """调用图谱命令行界面"""
    
    def __init__(self):
        """初始化CLI"""
        self.config = ConfigManager()
        self.graph_store = Neo4jGraphStore()
        self.call_graph_service = None
        
    def connect_to_database(self) -> bool:
        """连接到Neo4j数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            config = self.config.get_config()
            success = self.graph_store.connect(
                config.database.neo4j_uri,
                config.database.neo4j_user,
                config.database.neo4j_password
            )
            
            if success:
                self.call_graph_service = CallGraphService(self.graph_store)
                return True
            else:
                print("❌ Failed to connect to Neo4j database")
                return False
                
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def generate_call_graph(self, root: str, depth: int = 3, format_type: str = "mermaid", 
                          output: Optional[str] = None, html: bool = False) -> bool:
        """生成调用图谱
        
        Args:
            root: 根函数名
            depth: 查询深度
            format_type: 输出格式 ('mermaid', 'json', 'ascii')
            output: 输出文件路径
            html: 是否生成HTML查看器
            
        Returns:
            bool: 生成是否成功
        """
        try:
            print(f"🔍 Generating call graph for function '{root}' (depth: {depth})")
            
            # 构建图谱数据
            graph_data = self.call_graph_service.build_graph(root, depth)
            
            stats = graph_data.get('stats', {})
            print(f"📊 Found {stats.get('node_count', 0)} functions and {stats.get('edge_count', 0)} calls")
            
            if format_type.lower() == "ascii":
                # ASCII输出到控制台
                ascii_tree = self.call_graph_service.print_ascii_tree(graph_data)
                print("\n" + ascii_tree)
                
            elif output:
                # 输出到文件
                output_path = Path(output)
                self.call_graph_service.export_to_file(graph_data, output_path, format_type)
                print(f"✅ Call graph exported to {output_path}")
                
                # 可选生成HTML查看器
                if html:
                    html_path = output_path.with_suffix('.html')
                    self.call_graph_service.generate_html_viewer(graph_data, html_path)
                    print(f"🌐 HTML viewer generated at {html_path}")
                    
            else:
                # 输出到控制台
                if format_type.lower() == "mermaid":
                    mermaid_content = self.call_graph_service.to_mermaid(graph_data)
                    print("\n📊 Mermaid Diagram:")
                    print("```mermaid")
                    print(mermaid_content)
                    print("```")
                elif format_type.lower() == "json":
                    json_content = self.call_graph_service.to_json(graph_data)
                    print("\n📄 JSON Data:")
                    print(json_content)
                    
            return True
            
        except (ServiceError, StorageError) as e:
            print(f"❌ Service error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def run(self, args: argparse.Namespace) -> int:
        """运行CLI命令
        
        Args:
            args: 命令行参数
            
        Returns:
            int: 退出代码
        """
        try:
            # 连接数据库
            if not self.connect_to_database():
                return 1
            
            # 生成调用图谱
            success = self.generate_call_graph(
                root=args.root,
                depth=args.depth,
                format_type=args.format,
                output=args.output,
                html=args.html
            )
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
            return 130
        except Exception as e:
            logger.exception("Unexpected error in CallGraphCLI")
            print(f"❌ Unexpected error: {e}")
            return 1
        finally:
            if self.graph_store:
                self.graph_store.close()


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器
    """
    parser = argparse.ArgumentParser(
        prog='code-learner call-graph',
        description='Generate function call graphs from Neo4j database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show ASCII tree in console
  code-learner call-graph main --format ascii
  
  # Generate Mermaid diagram file
  code-learner call-graph main --format mermaid --output call_graph.md
  
  # Generate JSON with HTML viewer
  code-learner call-graph main --format json --output graph.json --html
  
  # Deep analysis with custom depth
  code-learner call-graph sbi_init --depth 5 --format mermaid --output deep_analysis.md
        """
    )
    
    parser.add_argument(
        'root',
        help='Root function name to start the call graph from'
    )
    
    parser.add_argument(
        '--depth', '-d',
        type=int,
        default=3,
        help='Maximum depth to traverse (default: 3)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['mermaid', 'json', 'ascii'],
        default='mermaid',
        help='Output format (default: mermaid)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path (if not specified, prints to console)'
    )
    
    parser.add_argument(
        '--html',
        action='store_true',
        help='Generate HTML viewer (only when --output is specified)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def main(argv: Optional[list] = None) -> int:
    """主函数
    
    Args:
        argv: 命令行参数列表
        
    Returns:
        int: 退出代码
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # 运行CLI
    cli = CallGraphCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main()) 