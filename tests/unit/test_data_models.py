"""数据模型单元测试

测试核心数据模型的功能和验证
"""
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.code_learner.core.data_models import (
    Function, FileInfo, ParsedCode, EmbeddingData, 
    QueryResult, AnalysisSession
)


class TestFunction:
    """Function数据模型测试"""
    
    def test_function_creation(self):
        """测试Function对象创建"""
        func = Function(
            name="test_function",
            code="int test_function() { return 0; }",
            start_line=1,
            end_line=3,
            file_path="/test/file.c",
            parameters=["int", "char*"],
            return_type="int",
            calls=["printf", "malloc"],
            called_by=["main"]
        )
        
        assert func.name == "test_function"
        assert func.start_line == 1
        assert func.end_line == 3
        assert func.file_path == "/test/file.c"
        assert len(func.parameters) == 2
        assert len(func.calls) == 2
        assert len(func.called_by) == 1
    
    def test_function_validation(self):
        """测试Function数据验证"""
        # 测试空函数名
        with pytest.raises(ValueError, match="function name cannot be empty"):
            Function(
                name="",
                code="test",
                start_line=1,
                end_line=2,
                file_path="/test.c"
            )
        
        # 测试负数行号
        with pytest.raises(ValueError, match="start_line must be non-negative"):
            Function(
                name="test",
                code="test",
                start_line=-1,
                end_line=2,
                file_path="/test.c"
            )
        
        # 测试end_line < start_line
        with pytest.raises(ValueError, match="end_line must be >= start_line"):
            Function(
                name="test",
                code="test",
                start_line=5,
                end_line=3,
                file_path="/test.c"
            )
    
    def test_function_defaults(self):
        """测试Function默认值"""
        func = Function(
            name="test",
            code="test",
            start_line=1,
            end_line=2,
            file_path="/test.c"
        )
        
        assert func.parameters == []
        assert func.return_type is None
        assert func.calls == []
        assert func.called_by == []


class TestFileInfo:
    """FileInfo数据模型测试"""
    
    def test_file_info_creation(self):
        """测试FileInfo对象创建"""
        now = datetime.now()
        file_info = FileInfo(
            path="/test/file.c",
            name="file.c",
            size=1024,
            last_modified=now,
            functions=[],
            includes=["stdio.h", "stdlib.h"]
        )
        
        assert file_info.path == "/test/file.c"
        assert file_info.name == "file.c"
        assert file_info.size == 1024
        assert file_info.last_modified == now
        assert len(file_info.includes) == 2
    
    def test_file_info_from_path(self):
        """测试从文件路径创建FileInfo"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write("int main() { return 0; }")
            temp_path = Path(f.name)
        
        try:
            file_info = FileInfo.from_path(temp_path)
            
            assert file_info.path == str(temp_path)
            assert file_info.name == temp_path.name
            assert file_info.size > 0
            assert isinstance(file_info.last_modified, datetime)
            
        finally:
            temp_path.unlink()


class TestParsedCode:
    """ParsedCode数据模型测试"""
    
    def test_parsed_code_creation(self):
        """测试ParsedCode对象创建"""
        file_info = FileInfo(
            path="/test.c",
            name="test.c", 
            size=100,
            last_modified=datetime.now()
        )
        
        functions = [
            Function("func1", "code1", 1, 5, "/test.c"),
            Function("func2", "code2", 7, 12, "/test.c")
        ]
        
        parsed = ParsedCode(
            file_info=file_info,
            functions=functions,
            ast_data={"type": "translation_unit"}
        )
        
        assert parsed.file_info == file_info
        assert len(parsed.functions) == 2
        assert parsed.ast_data["type"] == "translation_unit"
    
    def test_get_function_by_name(self):
        """测试按名称查找函数"""
        file_info = FileInfo("/test.c", "test.c", 100, datetime.now())
        functions = [
            Function("main", "main code", 1, 5, "/test.c"),
            Function("helper", "helper code", 7, 10, "/test.c")
        ]
        
        parsed = ParsedCode(file_info, functions)
        
        # 找到存在的函数
        main_func = parsed.get_function_by_name("main")
        assert main_func is not None
        assert main_func.name == "main"
        
        # 找不到的函数
        not_found = parsed.get_function_by_name("nonexistent")
        assert not_found is None
    
    def test_get_function_calls(self):
        """测试获取函数调用关系"""
        file_info = FileInfo("/test.c", "test.c", 100, datetime.now())
        functions = [
            Function("main", "main code", 1, 5, "/test.c", calls=["helper", "printf"]),
            Function("helper", "helper code", 7, 10, "/test.c", calls=["malloc"])
        ]
        
        parsed = ParsedCode(file_info, functions)
        call_graph = parsed.get_function_calls()
        
        assert call_graph["main"] == ["helper", "printf"]
        assert call_graph["helper"] == ["malloc"]


class TestEmbeddingData:
    """EmbeddingData数据模型测试"""
    
    def test_embedding_data_creation(self):
        """测试EmbeddingData对象创建"""
        embedding = EmbeddingData(
            id="func_main_1",
            text="int main() { return 0; }",
            embedding=[0.1, 0.2, 0.3, 0.4],
            metadata={"function": "main", "file": "test.c"}
        )
        
        assert embedding.id == "func_main_1"
        assert embedding.text == "int main() { return 0; }"
        assert len(embedding.embedding) == 4
        assert embedding.metadata["function"] == "main"
    
    def test_embedding_data_validation(self):
        """测试EmbeddingData数据验证"""
        # 测试空ID
        with pytest.raises(ValueError, match="embedding id cannot be empty"):
            EmbeddingData(
                id="",
                text="test",
                embedding=[0.1, 0.2]
            )
        
        # 测试空文本
        with pytest.raises(ValueError, match="embedding text cannot be empty"):
            EmbeddingData(
                id="test_id",
                text="",
                embedding=[0.1, 0.2]
            )
        
        # 测试空向量
        with pytest.raises(ValueError, match="embedding vector cannot be empty"):
            EmbeddingData(
                id="test_id",
                text="test",
                embedding=[]
            )


class TestQueryResult:
    """QueryResult数据模型测试"""
    
    def test_query_result_creation(self):
        """测试QueryResult对象创建"""
        result = QueryResult(
            question="What does main function do?",
            answer="The main function returns 0.",
            confidence=0.85,
            sources=[{"file": "test.c", "function": "main"}],
            context=["int main() { return 0; }"]
        )
        
        assert result.question == "What does main function do?"
        assert result.answer == "The main function returns 0."
        assert result.confidence == 0.85
        assert len(result.sources) == 1
        assert len(result.context) == 1
    
    def test_query_result_validation(self):
        """测试QueryResult数据验证"""
        # 测试无效confidence值
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            QueryResult(
                question="test",
                answer="test",
                confidence=1.5
            )
        
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            QueryResult(
                question="test",
                answer="test",
                confidence=-0.1
            )


class TestAnalysisSession:
    """AnalysisSession数据模型测试"""
    
    def test_analysis_session_creation(self):
        """测试AnalysisSession对象创建"""
        started_at = datetime.now()
        session = AnalysisSession(
            id="session_123",
            project_path="/test/project",
            status="running",
            started_at=started_at
        )
        
        assert session.id == "session_123"
        assert session.project_path == "/test/project"
        assert session.status == "running"
        assert session.started_at == started_at
        assert session.completed_at is None
        assert session.files_processed == 0
        assert session.functions_found == 0
        assert session.errors == []
    
    def test_mark_completed(self):
        """测试标记会话完成"""
        session = AnalysisSession(
            id="test",
            project_path="/test",
            status="running",
            started_at=datetime.now()
        )
        
        session.mark_completed()
        
        assert session.status == "completed"
        assert session.completed_at is not None
        assert isinstance(session.completed_at, datetime)
    
    def test_mark_failed(self):
        """测试标记会话失败"""
        session = AnalysisSession(
            id="test",
            project_path="/test",
            status="running",
            started_at=datetime.now()
        )
        
        error_msg = "Parse error occurred"
        session.mark_failed(error_msg)
        
        assert session.status == "failed"
        assert session.completed_at is not None
        assert error_msg in session.errors
    
    def test_add_progress(self):
        """测试添加进度"""
        session = AnalysisSession(
            id="test",
            project_path="/test",
            status="running",
            started_at=datetime.now()
        )
        
        session.add_progress(5, 20)
        assert session.files_processed == 5
        assert session.functions_found == 20
        
        session.add_progress(3, 15)
        assert session.files_processed == 8
        assert session.functions_found == 35


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 