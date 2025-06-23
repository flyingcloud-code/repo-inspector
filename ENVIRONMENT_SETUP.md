# 环境配置指南

## 📋 概述

本文档说明如何配置C语言智能代码分析调试工具的环境变量和凭据。

## 🔧 必需配置

### 1. OpenRouter API Key（必需）

**用途：** 与Google Gemini 2.0 Flash模型进行对话交互

**获取步骤：**
1. 访问 [OpenRouter](https://openrouter.ai/)
2. 注册账户并登录
3. 前往 [API Keys页面](https://openrouter.ai/keys)
4. 创建新的API Key
5. 复制API Key

**设置方法：**

```bash
# 方法1: 设置环境变量
export OPENROUTER_API_KEY="your_actual_api_key_here"

# 方法2: 创建.env文件
cp .env.example .env
# 编辑.env文件，填入真实的API Key
```

### 2. Neo4j数据库（可选，有默认值）

**用途：** 存储代码结构的图数据

**Docker方式（推荐）：**
```bash
# 创建数据卷
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
    neo4j:5.26-community

# 验证启动
docker ps | grep neo4j
curl http://localhost:7474
```

**环境变量：**
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j" 
export NEO4J_PASSWORD="<your password>"
```

## 📁 配置文件

### .env文件配置

1. **复制模板：**
```bash
cp .env.example .env
```

2. **编辑配置：**
```bash
# 编辑.env文件
nano .env
```

3. **必填项目：**
```env
# 必需 - OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx

# 可选 - Neo4j配置（如果使用非默认值）
NEO4J_PASSWORD=your_neo4j_password
```

### config.yml配置

系统会自动从以下位置加载配置：
1. `config/config.yml` - 主配置文件
2. 环境变量（优先级更高）

## 🧪 验证配置

### 1. 快速验证
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行验证脚本
python -c "
from src.code_learner import ConfigManager
config = ConfigManager().get_config()
print('✅ 配置加载成功')
if config.llm.chat_api_key:
    print('✅ OpenRouter API Key已设置')
else:
    print('⚠️  OpenRouter API Key未设置')
print(f'✅ Neo4j URI: {config.database.neo4j_uri}')
"
```

### 2. 完整测试
```bash
# 运行Story 1.1验收测试
python -m pytest tests/integration/test_story_1_1_acceptance.py::TestStory11Acceptance::test_story_1_1_complete -v -s
```

### 3. 检查依赖
```bash
# 检查所有依赖是否正常
python -m pytest tests/unit/test_ubuntu_environment.py -v
```

## 🔒 安全注意事项

1. **不要提交.env文件到Git：**
```bash
# .env文件已在.gitignore中
echo ".env" >> .gitignore
```

2. **保护API Key：**
- 不要在代码中硬编码API Key
- 不要在公共场所分享API Key
- 定期轮换API Key

3. **Neo4j安全：**
- 更改默认密码
- 限制网络访问
- 定期备份数据

## 🚀 快速开始

```bash
# 1. 设置环境
cp .env.example .env
# 编辑.env文件，填入OpenRouter API Key

# 2. 启动Neo4j (可选)
docker run -d --name neo4j-community -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/<your password> neo4j:5.26-community

# 3. 验证配置
source .venv/bin/activate
python -m pytest tests/integration/test_story_1_1_acceptance.py::TestStory11Acceptance::test_story_1_1_complete -v -s

# 4. 开始使用
python -c "import src.code_learner; src.code_learner.setup_environment()"
```

## 🆘 故障排除

### 问题1：OpenRouter API Key警告
```
警告: OpenRouter API Key未设置，请设置环境变量 OPENROUTER_API_KEY
```
**解决方案：**
1. 检查.env文件是否存在且包含正确的API Key
2. 确保环境变量已正确设置
3. 重启终端或重新加载环境变量

### 问题2：Neo4j连接失败
```
Neo4j connection error: Failed to establish connection
```
**解决方案：**
1. 检查Docker容器是否运行：`docker ps | grep neo4j`
2. 检查端口是否被占用：`netstat -tulpn | grep 7687`
3. 检查防火墙设置

### 问题3：依赖包导入错误
```
ModuleNotFoundError: No module named 'xxx'
```
**解决方案：**
1. 确保虚拟环境已激活：`source .venv/bin/activate`
2. 重新安装依赖：`uv pip install -r requirements.txt`
3. 检查Python版本：`python --version` (需要3.11+)

## 📞 获取帮助

如果遇到配置问题：
1. 查看日志文件：`logs/code_learner.log`
2. 运行诊断测试：`python -m pytest tests/unit/test_ubuntu_environment.py -v`
3. 检查配置文件：`config/config.yml`

---

配置完成后，您就可以开始使用C语言智能代码分析调试工具了！🎉 