import warnings
warnings.filterwarnings('ignore')  # 忽略警告信息

from sentence_transformers import SentenceTransformer
print('✅ 嵌入模型测试开始...')
model = SentenceTransformer('jinaai/jina-embeddings-v2-base-code')
test_result = model.encode('int main() { return 0; }')
print(f'✅ 嵌入模型工作正常！')
print(f'📊 嵌入维度: {len(test_result)}')
print(f'📈 嵌入向量类型: {type(test_result)}')
