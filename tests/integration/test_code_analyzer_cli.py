"""
测试代码分析器CLI工具
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import pytest

from code_learner.cli.code_analyzer_cli import main


class TestCodeAnalyzerCLI:
    """测试代码分析器CLI工具"""
    
    @pytest.fixture
    def test_project(self):
        """创建测试项目"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()
            
            # 创建测试文件
            main_c = project_dir / "main.c"
            main_c.write_text("""
            #include <stdio.h>
            #include "utils.h"
            
            int main() {
                hello();
                return 0;
            }
            """)
            
            utils_h = project_dir / "utils.h"
            utils_h.write_text("""
            void hello();
            """)
            
            utils_c = project_dir / "utils.c"
            utils_c.write_text("""
            #include <stdio.h>
            #include "utils.h"
            
            void hello() {
                printf("Hello, World!\\n");
            }
            """)
            
            yield project_dir
    
    def test_analyze_command(self, test_project, monkeypatch, capsys):
        """测试analyze命令"""
        # 重定向参数
        monkeypatch.setattr(sys, "argv", ["code-learner", "analyze", str(test_project)])
        
        # 捕获异常，因为测试环境可能没有Neo4j
        try:
            main()
        except Exception:
            pass
        
        # 检查输出
        captured = capsys.readouterr()
        assert "开始分析项目" in captured.out
        assert str(test_project) in captured.out
    
    def test_status_command(self, monkeypatch, capsys):
        """测试status命令"""
        # 重定向参数
        monkeypatch.setattr(sys, "argv", ["code-learner", "status"])
        
        # 捕获异常，因为测试环境可能没有完整服务
        try:
            main()
        except Exception:
            pass
        
        # 检查输出
        captured = capsys.readouterr()
        assert "系统状态检查结果" in captured.out
    
    def test_help_command(self, monkeypatch, capsys):
        """测试帮助命令"""
        # 重定向参数
        monkeypatch.setattr(sys, "argv", ["code-learner", "--help"])
        
        # 捕获异常
        try:
            main()
        except SystemExit:
            pass
        
        # 检查输出
        captured = capsys.readouterr()
        assert "C语言智能代码分析调试工具" in captured.out
        assert "analyze" in captured.out
        assert "query" in captured.out
        assert "status" in captured.out
        assert "export" in captured.out
    
    def test_analyze_with_options(self, test_project, monkeypatch, capsys):
        """测试带选项的analyze命令"""
        # 创建输出目录
        output_dir = test_project / "output"
        output_dir.mkdir()
        
        # 重定向参数
        monkeypatch.setattr(sys, "argv", [
            "code-learner", 
            "analyze", 
            str(test_project),
            "--output-dir", str(output_dir),
            "--incremental",
            "--threads", "2"
        ])
        
        # 捕获异常
        try:
            main()
        except Exception:
            pass
        
        # 检查输出
        captured = capsys.readouterr()
        assert "开始分析项目" in captured.out
        assert "增量分析" in captured.out
    
    def test_query_command(self, test_project, monkeypatch, capsys):
        """测试query命令 (交互式问答)"""
        # 通过monkeypatch模拟用户输入 `exit` 立即退出
        monkeypatch.setattr(sys, "argv", [
            "code-learner", "query", "--project", str(test_project)
        ])
        
        # 模拟 input() 连续返回 'exit' -> Stop iteration
        monkeypatch.setattr("builtins.input", lambda prompt="": "exit")
        
        try:
            main()
        except Exception:
            # 可能因为缺少外部服务而抛异常，但我们只关心交互入口是否启动
            pass
        
        captured = capsys.readouterr()
        assert "代码问答会话" in captured.out
        assert "exit" not in captured.err
    
    def test_export_command(self, test_project, tmp_path, monkeypatch, capsys):
        """测试export命令 (导出分析结果)"""
        # 先执行一次 analyze 以生成数据 (忽略可能的错误)
        monkeypatch.setattr(sys, "argv", [
            "code-learner", "analyze", str(test_project)
        ])
        try:
            main()
        except Exception:
            pass
        
        export_path = tmp_path / "analysis_export.json"
        
        # 执行 export 命令
        monkeypatch.setattr(sys, "argv", [
            "code-learner", "export", "--project", str(test_project),
            "--format", "json", "--output", str(export_path)
        ])
        try:
            main()
        except Exception:
            pass
        
        captured = capsys.readouterr()
        assert "导出完成" in captured.out
        # 即使外部服务失败，仍应创建文件
        assert export_path.exists(), "导出文件应已创建"  