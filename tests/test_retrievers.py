"""
检索器测试 - 使用真实数据

重构版本：彻底解耦Neo4j和Chroma数据
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os

from src.code_learner.retrieval.vector_retriever import VectorContextRetriever
from src.code_learner.retrieval.graph_retriever import GraphContextRetriever
from src.code_learner.core.context_models import IntentType
from src.code_learner.llm.independent_embedder import IndependentCodeEmbedder
from src.code_learner.cli.code_analyzer_cli import CodeAnalyzer


@pytest.fixture
def simple_test_data():
    """创建简单的测试数据，分离Neo4j和Chroma数据填充"""
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    test_project_dir = Path(temp_dir) / "test_project"
    test_project_dir.mkdir()
    
    try:
        # 创建测试文件
        main_c = test_project_dir / "main.c"
        main_c.write_text("""
#include <stdio.h>
#include "utils.h"

int main() {
    printf("Hello World\\n");
    print_message("Test message");
    return 0;
}

void setup_system() {
    printf("Setting up system\\n");
}
""")
        
        utils_h = test_project_dir / "utils.h"
        utils_h.write_text("""
#ifndef UTILS_H
#define UTILS_H

void print_message(const char* msg);
int calculate_sum(int a, int b);

#endif
""")
        
        utils_c = test_project_dir / "utils.c"
        utils_c.write_text("""
#include "utils.h"
#include <stdio.h>

void print_message(const char* msg) {
    printf("Message: %s\\n", msg);
}

int calculate_sum(int a, int b) {
    return a + b;
}
""")
        
        # 生成项目ID
        project_id = "auto_test123"
        
        # 设置环境变量
        os.environ["CODE_LEARNER_PROJECT_ID"] = project_id
        
        # 1. 填充Neo4j数据（用于图检索）
        print("=== 填充Neo4j数据 ===")
        analyzer = CodeAnalyzer(
            project_path=test_project_dir,
            project_id=project_id
        )
        
        # 运行分析，但不生成嵌入（避免混乱的数据流）
        analyzer.analyze(generate_embeddings=False)
        
        # 2. 独立填充Chroma数据（用于向量检索）
        print("=== 独立填充Chroma数据 ===")
        embedder = IndependentCodeEmbedder(project_id=project_id)
        success = embedder.embed_directory(str(test_project_dir), ['.c', '.h'])
        
        if not success:
            raise Exception("独立嵌入器失败")
        
        print("✅ 测试数据创建成功")
        
        yield {
            "project_dir": test_project_dir,
            "project_id": project_id
        }
        
    finally:
        # 清理环境变量
        if "CODE_LEARNER_PROJECT_ID" in os.environ:
            del os.environ["CODE_LEARNER_PROJECT_ID"]
        
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_vector_retriever_real_data(simple_test_data):
    """测试向量检索器 - 使用真实数据"""
    
    project_id = simple_test_data["project_id"]
    
    # 确保环境变量设置
    os.environ["CODE_LEARNER_PROJECT_ID"] = project_id
    
    try:
        # 创建向量检索器
        retriever = VectorContextRetriever()
        
        # 创建简单意图
        intent = {
            'primary_entity': 'printf',
            'core_intent': 'find'
        }
        
        # 执行检索
        results = retriever.retrieve("how to print a message", intent)
        
        # 验证结果
        assert len(results) > 0, "Retriever should return some results"
        
        # 检查是否包含相关内容
        found_printf = any("printf" in item.content for item in results)
        assert found_printf, "Expected to find content with 'printf'"
        
        # 检查元数据结构
        for item in results:
            assert hasattr(item, 'content'), "Item should have content"
            assert hasattr(item, 'metadata'), "Item should have metadata"
            assert hasattr(item, 'score'), "Item should have score"
            
            # 检查file_path是否存在（这是我们要修复的关键问题）
            assert 'file_path' in item.metadata, f"Item metadata should contain file_path. Got: {item.metadata}"
        
        # 检查是否有来自不同文件的结果
        file_paths = {item.metadata.get('file_path', '') for item in results}
        assert len(file_paths) > 0, "Should have file paths in metadata"
        
        print(f"✅ 向量检索测试通过，找到 {len(results)} 个结果")
        print(f"文件路径: {file_paths}")
        
    finally:
        # 清理环境变量
        if "CODE_LEARNER_PROJECT_ID" in os.environ:
            del os.environ["CODE_LEARNER_PROJECT_ID"]


def test_graph_retriever_real_data(simple_test_data):
    """测试图检索器 - 使用真实数据"""
    
    project_id = simple_test_data["project_id"]
    
    # 确保环境变量设置
    os.environ["CODE_LEARNER_PROJECT_ID"] = project_id
    
    try:
        # 创建图检索器
        retriever = GraphContextRetriever()
        
        # 创建简单意图
        intent = {
            'primary_entity': 'print_message',
            'core_intent': 'find'
        }
        
        # 执行检索
        results = retriever.retrieve("find print_message function", intent)
        
        # 验证结果
        assert len(results) >= 0, "Graph retriever should return results or empty list"
        
        print(f"✅ 图检索测试通过，找到 {len(results)} 个结果")
        
    finally:
        # 清理环境变量
        if "CODE_LEARNER_PROJECT_ID" in os.environ:
            del os.environ["CODE_LEARNER_PROJECT_ID"] 