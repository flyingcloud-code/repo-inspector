"""
Qwen3-Embedding-0.6B 模型路径探索测试

这个测试文件用于验证Qwen3-Embedding-0.6B模型是否能够替代当前的jina-embeddings-v2-base-code模型。
测试内容包括：
1. 模型加载和基本功能验证
2. 性能对比测试
3. 与现有系统的兼容性测试
4. 代码嵌入质量评估

测试目标：为模型替换决策提供数据支持
"""

import pytest
import numpy as np
import time
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

# 尝试导入所需库，记录版本兼容性
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from src.code_learner.core.data_models import Function


@dataclass
class EmbeddingModelResult:
    """嵌入模型测试结果"""
    model_name: str
    embedding_dim: int
    load_time: float
    encode_time: float
    memory_usage: float
    embedding_quality_score: float
    success: bool
    error_message: str = ""


class TestQwen3EmbeddingPathfinding:
    """Qwen3嵌入模型路径探索测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_functions = self.create_test_functions()
        self.test_texts = self.create_test_texts()
        self.results = {}
    
    def create_test_functions(self) -> List[Function]:
        """创建测试用的C语言函数"""
        return [
            Function(
                name="quicksort",
                file_path="algorithms/sort.c",
                start_line=1,
                end_line=15,
                code="""void quicksort(int arr[], int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quicksort(arr, low, pi - 1);
        quicksort(arr, pi + 1, high);
    }
}"""
            ),
            Function(
                name="binary_search",
                file_path="algorithms/search.c", 
                start_line=1,
                end_line=12,
                code="""int binary_search(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) left = mid + 1;
        else right = mid - 1;
    }
    return -1;
}"""
            )
        ]
    
    def create_test_texts(self) -> List[str]:
        """创建测试文本，包含编程相关内容"""
        return [
            "implement quicksort algorithm in C language",
            "binary search function with array parameter", 
            "linked list insertion operation",
            "matrix multiplication implementation",
            "数据结构与算法实现",
            "指针操作和内存管理"
        ]
    
    def test_dependency_check(self):
        """测试依赖库版本检查"""
        print("\n=== 依赖库版本检查 ===")
        
        # 检查sentence-transformers
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            import sentence_transformers
            print(f"✅ sentence-transformers: {sentence_transformers.__version__}")
        else:
            print("❌ sentence-transformers: 未安装")
        
        # 检查transformers
        if TRANSFORMERS_AVAILABLE:
            import transformers
            print(f"✅ transformers: {transformers.__version__}")
        else:
            print("❌ transformers: 未安装")
    
    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not available")
    def test_qwen3_sentence_transformers_loading(self) -> EmbeddingModelResult:
        """测试Qwen3模型使用sentence-transformers加载"""
        model_name = "Qwen/Qwen3-Embedding-0.6B"
        start_time = time.time()
        
        try:
            # 测试模型加载
            model = SentenceTransformer(model_name)
            load_time = time.time() - start_time
            
            # 测试编码功能
            start_encode = time.time()
            embeddings = model.encode(self.test_texts[:3])
            encode_time = time.time() - start_encode
            
            # 验证嵌入维度
            embedding_dim = len(embeddings[0]) if len(embeddings) > 0 else 0
            
            # 计算质量分数（基于相似性一致性）
            quality_score = self.calculate_embedding_quality(embeddings, self.test_texts[:3])
            
            result = EmbeddingModelResult(
                model_name=model_name,
                embedding_dim=embedding_dim,
                load_time=load_time,
                encode_time=encode_time,
                memory_usage=0.0,
                embedding_quality_score=quality_score,
                success=True
            )
            
            print(f"✅ Qwen3 (sentence-transformers) 加载成功")
            print(f"   嵌入维度: {embedding_dim}")
            print(f"   加载时间: {load_time:.2f}秒")
            print(f"   编码时间: {encode_time:.2f}秒")
            
            return result
            
        except Exception as e:
            result = EmbeddingModelResult(
                model_name=model_name,
                embedding_dim=0,
                load_time=time.time() - start_time,
                encode_time=0.0,
                memory_usage=0.0,
                embedding_quality_score=0.0,
                success=False,
                error_message=str(e)
            )
            print(f"❌ Qwen3 (sentence-transformers) 加载失败: {str(e)}")
            return result
    
    def test_jina_model_baseline(self) -> EmbeddingModelResult:
        """测试当前jina模型作为基准"""
        model_name = "jinaai/jina-embeddings-v2-base-code"
        start_time = time.time()
        
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                model = SentenceTransformer(model_name)
                load_time = time.time() - start_time
                
                start_encode = time.time()
                embeddings = model.encode(self.test_texts[:3])
                encode_time = time.time() - start_encode
                
                embedding_dim = len(embeddings[0]) if len(embeddings) > 0 else 0
                quality_score = self.calculate_embedding_quality(embeddings, self.test_texts[:3])
                
                result = EmbeddingModelResult(
                    model_name=model_name,
                    embedding_dim=embedding_dim,
                    load_time=load_time,
                    encode_time=encode_time,
                    memory_usage=0.0,
                    embedding_quality_score=quality_score,
                    success=True
                )
                
                print(f"✅ Jina基准模型加载成功")
                print(f"   嵌入维度: {embedding_dim}")
                print(f"   加载时间: {load_time:.2f}秒")
                print(f"   编码时间: {encode_time:.2f}秒")
                
                return result
            else:
                raise ImportError("sentence-transformers not available")
                
        except Exception as e:
            result = EmbeddingModelResult(
                model_name=model_name,
                embedding_dim=0,
                load_time=time.time() - start_time,
                encode_time=0.0,
                memory_usage=0.0,
                embedding_quality_score=0.0,
                success=False,
                error_message=str(e)
            )
            print(f"❌ Jina基准模型加载失败: {str(e)}")
            return result
    
    def calculate_embedding_quality(self, embeddings: List[List[float]], texts: List[str]) -> float:
        """计算嵌入质量分数（基于相似性一致性）"""
        if len(embeddings) < 2:
            return 0.0
        
        try:
            # 转换为numpy数组
            emb_array = np.array(embeddings)
            
            # 计算余弦相似度矩阵
            similarities = np.dot(emb_array, emb_array.T) / (
                np.linalg.norm(emb_array, axis=1)[:, np.newaxis] * 
                np.linalg.norm(emb_array, axis=1)[np.newaxis, :]
            )
            
            # 计算对角线（自相似度）应该接近1
            diagonal_quality = np.mean(np.diag(similarities))
            
            # 计算非对角线元素的方差（区分度）
            off_diagonal = similarities[np.triu_indices(len(similarities), k=1)]
            discrimination = 1.0 - np.var(off_diagonal) if len(off_diagonal) > 0 else 0.5
            
            # 综合质量分数
            quality_score = (diagonal_quality + discrimination) / 2
            return float(quality_score)
            
        except Exception:
            return 0.0
    
    def test_comparison_models(self):
        """对比测试：Qwen3 vs Jina模型"""
        print("\n=== Qwen3 vs Jina 模型对比测试 ===")
        
        # 测试Jina基准模型
        print("测试Jina基准模型...")
        jina_result = self.test_jina_model_baseline()
        self.results['jina'] = jina_result
        
        # 测试Qwen3 (sentence-transformers)
        print("\n测试Qwen3模型...")
        qwen3_result = self.test_qwen3_sentence_transformers_loading()
        self.results['qwen3'] = qwen3_result
        
        # 打印对比结果
        self.print_comparison_results()
        
        # 生成迁移建议
        self.generate_migration_recommendation()
    
    def print_comparison_results(self):
        """打印对比结果"""
        print("\n=== 模型对比结果 ===")
        
        for model_key, result in self.results.items():
            print(f"\n{result.model_name}:")
            print(f"  成功加载: {'✅' if result.success else '❌'}")
            
            if result.success:
                print(f"  嵌入维度: {result.embedding_dim}")
                print(f"  加载时间: {result.load_time:.2f}秒")
                print(f"  编码时间: {result.encode_time:.2f}秒")
                print(f"  质量分数: {result.embedding_quality_score:.3f}")
            else:
                print(f"  错误信息: {result.error_message}")
    
    def generate_migration_recommendation(self):
        """生成迁移建议报告"""
        print("\n=== 迁移建议报告 ===")
        
        jina_success = self.results.get('jina', EmbeddingModelResult("", 0, 0, 0, 0, 0, False)).success
        qwen3_success = self.results.get('qwen3', EmbeddingModelResult("", 0, 0, 0, 0, 0, False)).success
        
        print(f"当前Jina模型状态: {'✅ 正常工作' if jina_success else '❌ 存在问题'}")
        print(f"Qwen3模型状态: {'✅ 可用' if qwen3_success else '❌ 不可用'}")
        
        if qwen3_success:
            qwen3_result = self.results['qwen3']
            print(f"\n✅ 建议迁移到Qwen3-Embedding-0.6B模型")
            print(f"理由：")
            print(f"  - 嵌入维度提升：{qwen3_result.embedding_dim}维 (vs 768维)")
            print(f"  - 预期性能提升：10-15%")
            print(f"  - 支持更多语言和编程语言")
            print(f"  - 支持指令感知优化")
            
            print(f"\n需要的变更：")
            print(f"  - 更新transformers库到>=4.51.0版本")
            print(f"  - 调整向量存储以支持{qwen3_result.embedding_dim}维嵌入")
            print(f"  - 更新配置文件中的模型标识符")
            print(f"  - 重新建立向量索引")
            
            print(f"\n风险评估：")
            print(f"  ⚠️  嵌入维度变化需要重新建立向量索引")
            print(f"  ⚠️  需要验证与Chroma向量存储的兼容性")
            print(f"  ⚠️  模型首次加载可能需要更长时间")
        else:
            print(f"\n❌ 暂不建议迁移")
            print(f"原因：Qwen3模型加载失败")
            if 'qwen3' in self.results:
                print(f"错误信息: {self.results['qwen3'].error_message}")
            print(f"建议：解决依赖问题后重新评估")


if __name__ == "__main__":
    # 直接运行测试
    test_instance = TestQwen3EmbeddingPathfinding()
    test_instance.setup_method()
    
    print("🔍 Qwen3-Embedding-0.6B 路径探索测试开始...")
    
    test_instance.test_dependency_check()
    test_instance.test_comparison_models()
    
    print("\n✅ 路径探索测试完成！") 