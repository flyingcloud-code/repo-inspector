# C语言智能代码分析调试工具 - Ubuntu环境部署指南

## 环境信息
- **系统版本:** Ubuntu 24.04.2 LTS (WSL2)
- **Python版本:** 3.12.3 (系统自带)
- **Docker版本:** 28.1.1 (已安装)
- **uv版本:** 已安装至 `/home/flyingcloud/.local/bin/uv`

## 快速部署步骤

### 第一步：创建Python虚拟环境

```bash
# 使用uv创建虚拟环境
uv venv --python 3.11

# 激活虚拟环境
source .venv/bin/activate

# 验证Python版本
python --version  # 应显示 Python 3.12.x
```

### 第二步：安装核心依赖

```bash
# 安装Tree-sitter (C语言解析器)
sudo apt update
sudo apt install libtree-sitter-dev
pip install tree-sitter tree-sitter-c

# 安装向量数据库
pip install chromadb>=1.0.13

# 安装LLM模型库
pip install sentence-transformers>=3.0.0

# 安装Neo4j Python驱动
pip install neo4j>=5.25.0

# 安装开发工具
pip install flake8 mypy pytest pytest-cov click pyyaml requests
```

### 第三步：启动Neo4j数据库 (Docker)

```bash
# 创建数据持久化卷
docker volume create neo4j_data
docker volume create neo4j_logs

# 启动Neo4j容器
docker run -d \
    --name neo4j-community \
    --restart always \
    -p 7474:7474 -p 7687:7687 \
    -v neo4j_data:/data \
    -v neo4j_logs:/logs \
    -e NEO4J_AUTH=neo4j/<your password> \
    -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
    neo4j:5.26-community

# 等待服务启动 (约30秒)
sleep 30

# 验证Neo4j服务状态
docker ps | grep neo4j
curl -s http://localhost:7474 | grep -o "Neo4j" || echo "Neo4j未启动"
```

### 第四步：验证环境安装

```bash
# 验证Tree-sitter
python -c "
import tree_sitter
from tree_sitter import Language, Parser
print('✅ Tree-sitter版本:', tree_sitter.__version__)
"

# 验证Chroma
python -c "
import chromadb
client = chromadb.Client()
print('✅ Chroma安装成功，版本:', chromadb.__version__)
"

# 验证Neo4j连接
python -c "
from neo4j import GraphDatabase
try:
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', '<your password>'))
    driver.verify_connectivity()
    print('✅ Neo4j连接成功')
    driver.close()
except Exception as e:
    print('❌ Neo4j连接失败:', e)
"

# 验证jina-embeddings模型 (首次运行会下载模型)
python -c "
from sentence_transformers import SentenceTransformer
print('✅ sentence-transformers可用')
print('📦 模型将下载至: ~/.cache/torch/sentence_transformers/')
"
```

### 第五步：创建项目配置文件

```bash
# 创建配置目录
mkdir -p src/code_learner/config

# 创建配置文件
cat > src/code_learner/config/settings.yaml << 'EOF'
# 应用配置
app:
  name: "Code Repo Learner"
  version: "0.1.0"
  debug: true
  log_level: "INFO"
  data_dir: "./data"

# Neo4j图数据库配置
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "<your pass word here>"
  database: "neo4j"

# Chroma向量数据库配置
chroma:
  persist_directory: "./data/chroma_db"
  collection_name: "code_embeddings"

# LLM配置
llm:
  embedding_model: "jinaai/jina-embeddings-v2-base-code"
  openrouter_api_key: ""  # 需要用户设置
  openrouter_api_url: "https://openrouter.ai/api/v1/chat/completions"
  openrouter_model: "google/gemini-2.0-flash-001"
  max_tokens: 8192

# 解析器配置
parser:
  supported_extensions: [".c", ".h"]
  ignore_patterns: ["build/", "dist/", ".git/"]
  max_file_size: 10485760  # 10MB
EOF
```

## 环境验证清单

运行以下命令确保所有组件正常工作：

```bash
# 🔍 系统环境检查
echo "=== 系统环境检查 ==="
uname -a
python --version
docker --version
which uv

# 🔍 Python包检查
echo "=== Python包检查 ==="
pip list | grep -E "(tree-sitter|chromadb|sentence-transformers|neo4j)"

# 🔍 Neo4j服务检查
echo "=== Neo4j服务检查 ==="
docker ps | grep neo4j
curl -s http://localhost:7474 | head -n 5

# 🔍 导入测试
echo "=== 导入测试 ==="
python -c "
import tree_sitter
import chromadb  
import neo4j
from sentence_transformers import SentenceTransformer
print('✅ 所有核心模块导入成功')
"
```

## 故障排除

### 1. Tree-sitter编译问题
```bash
# 如果遇到编译错误，安装构建工具
sudo apt install build-essential
```

### 2. Neo4j连接问题
```bash
# 检查容器状态
docker logs neo4j-community

# 重启容器
docker restart neo4j-community
```

### 3. Chroma数据库问题
```bash
# 创建数据目录
mkdir -p ./data/chroma_db
chmod 755 ./data/chroma_db
```

### 4. 网络问题 (模型下载)
```bash
# 检查网络连接
ping -c 3 huggingface.co

# 手动下载模型 (如果自动下载失败)
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('jinaai/jina-embeddings-v2-base-code')
print('模型下载完成')
"
```

## 下一步行动

环境部署完成后，您可以：

1. **开始Story 1.1开发**：按照更新后的工作计划进行
2. **运行单元测试**：`pytest tests/` 
3. **启动开发服务器**：`python src/code_learner/cli/main.py`
4. **访问Neo4j管理界面**：http://localhost:7474

## 环境管理

```bash
# 激活环境
source .venv/bin/activate

# 停用环境
deactivate

# 停止Neo4j
docker stop neo4j-community

# 启动Neo4j
docker start neo4j-community

# 查看Docker资源使用
docker stats neo4j-community
```

---

**注意：** 请将OpenRouter API Key设置为环境变量：
```bash
export OPENROUTER_API_KEY="your_api_key_here"
``` 