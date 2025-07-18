"""自定义异常类定义

定义系统中各种业务异常，提供清晰的错误信息
"""


class CodeLearnerError(Exception):
    """基础异常类"""
    pass


class ParseError(CodeLearnerError):
    """代码解析异常"""
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        self.message = message
        super().__init__(f"Parse error in {file_path}: {message}")


class DatabaseConnectionError(CodeLearnerError):
    """数据库连接异常"""
    def __init__(self, database_type: str, message: str):
        self.database_type = database_type
        self.message = message
        super().__init__(f"{database_type} connection error: {message}")


class StorageError(CodeLearnerError):
    """存储操作异常"""
    def __init__(self, operation_or_message: str, message: str = None):
        if message is None:
            # 只提供了一个参数，作为message使用
            self.operation = "general"
            self.message = operation_or_message
            super().__init__(f"Storage error: {self.message}")
        else:
            # 提供了两个参数
            self.operation = operation_or_message
            self.message = message
            super().__init__(f"Storage error during '{self.operation}': {self.message}")


class ConfigurationError(CodeLearnerError):
    """配置异常"""
    def __init__(self, config_key_or_message: str, message: str = None):
        if message is None:
            # 只提供了一个参数，作为message使用
            self.config_key = "general"
            self.message = config_key_or_message
            super().__init__(f"Configuration error: {self.message}")
        else:
            # 提供了两个参数
            self.config_key = config_key_or_message
            self.message = message
            super().__init__(f"Configuration error for '{self.config_key}': {self.message}")


class ModelLoadError(CodeLearnerError):
    """模型加载异常"""
    def __init__(self, model_name: str, message: str):
        self.model_name = model_name
        self.message = message
        super().__init__(f"Failed to load model '{model_name}': {message}")


class EmbeddingError(CodeLearnerError):
    """向量嵌入异常"""
    def __init__(self, text: str, message: str):
        self.text = text[:100] + "..." if len(text) > 100 else text
        self.message = message
        super().__init__(f"Embedding error for text '{self.text}': {message}")


class QueryError(CodeLearnerError):
    """查询异常"""
    def __init__(self, query: str, message: str):
        self.query = query
        self.message = message
        super().__init__(f"Query error '{query}': {message}")


class APIError(CodeLearnerError):
    """API调用异常"""
    def __init__(self, api_name: str, status_code: int, message: str):
        self.api_name = api_name
        self.status_code = status_code
        self.message = message
        super().__init__(f"{api_name} API error (status {status_code}): {message}")


class ValidationError(CodeLearnerError):
    """数据验证异常"""
    def __init__(self, field_name: str, value: str, message: str):
        self.field_name = field_name
        self.value = value
        self.message = message
        super().__init__(f"Validation error for field '{field_name}' with value '{value}': {message}")


class APIConnectionError(CodeLearnerError):
    """API连接异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"API connection error: {message}")


class ModelError(CodeLearnerError):
    """模型运行异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Model error: {message}")


class ServiceError(CodeLearnerError):
    """服务异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Service error: {message}") 