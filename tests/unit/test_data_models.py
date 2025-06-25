"""数据模型单元测试

测试核心数据模型的功能和验证
"""
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.code_learner.core.data_models import (
    Function, FileInfo, ParsedCode, EmbeddingData, 
    QueryResult, AnalysisSession, ChatMessage, ChatResponse,
    # Story 2.1 新增数据模型
    FunctionCall, FallbackStats, FolderInfo, FolderStructure,
    Documentation, AnalysisResult
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


# Story 2.1 新增数据模型测试

class TestFunctionCall:
    """测试FunctionCall数据模型"""
    
    def test_function_call_creation(self):
        """测试FunctionCall创建"""
        call = FunctionCall(
            caller_name="main",
            callee_name="printf",
            call_type="direct",
            line_number=42,
            file_path="/path/to/main.c",
            context="printf(\"Hello World\\n\");"
        )
        
        assert call.caller_name == "main"
        assert call.callee_name == "printf"
        assert call.call_type == "direct"
        assert call.line_number == 42
        assert call.file_path == "/path/to/main.c"
        assert call.context == "printf(\"Hello World\\n\");"
    
    def test_function_call_validation(self):
        """测试FunctionCall数据验证"""
        # 测试空的调用者名称
        with pytest.raises(ValueError, match="caller_name cannot be empty"):
            FunctionCall("", "printf", "direct", 42, "/path/to/main.c", "context")
        
        # 测试空的被调用者名称
        with pytest.raises(ValueError, match="callee_name cannot be empty"):
            FunctionCall("main", "", "direct", 42, "/path/to/main.c", "context")
        
        # 测试无效的调用类型
        with pytest.raises(ValueError, match="call_type must be one of"):
            FunctionCall("main", "printf", "invalid", 42, "/path/to/main.c", "context")
        
        # 测试无效的行号
        with pytest.raises(ValueError, match="line_number must be positive"):
            FunctionCall("main", "printf", "direct", 0, "/path/to/main.c", "context")


class TestFallbackStats:
    """测试FallbackStats数据模型"""
    
    def test_fallback_stats_creation(self):
        """测试FallbackStats创建"""
        stats = FallbackStats()
        
        assert stats.total_functions == 0
        assert stats.treesitter_success == 0
        assert stats.regex_fallback == 0
        assert stats.fallback_reasons == {}
        assert stats.processing_times == []
        assert isinstance(stats.timestamp, datetime)
    
    def test_add_success(self):
        """测试记录成功解析"""
        stats = FallbackStats()
        stats.add_success(0.5)
        
        assert stats.total_functions == 1
        assert stats.treesitter_success == 1
        assert stats.regex_fallback == 0
        assert stats.processing_times == [0.5]
    
    def test_add_fallback(self):
        """测试记录fallback使用"""
        stats = FallbackStats()
        stats.add_fallback("syntax_error", 1.2)
        
        assert stats.total_functions == 1
        assert stats.treesitter_success == 0
        assert stats.regex_fallback == 1
        assert stats.fallback_reasons["syntax_error"] == 1
        assert stats.processing_times == [1.2]
    
    def test_fallback_rate(self):
        """测试fallback使用率计算"""
        stats = FallbackStats()
        
        # 空统计
        assert stats.fallback_rate == 0.0
        
        # 添加一些数据
        stats.add_success(0.5)
        stats.add_success(0.3)
        stats.add_fallback("error1", 1.0)
        stats.add_fallback("error2", 1.5)
        
        # 4个函数，2个fallback，使用率应该是0.5
        assert stats.fallback_rate == 0.5
    
    def test_average_processing_time(self):
        """测试平均处理时间计算"""
        stats = FallbackStats()
        
        # 空统计
        assert stats.average_processing_time == 0.0
        
        # 添加一些数据
        stats.add_success(0.5)
        stats.add_success(1.5)
        stats.add_fallback("error", 2.0)
        
        # 平均时间应该是 (0.5 + 1.5 + 2.0) / 3 = 1.33...
        expected_avg = (0.5 + 1.5 + 2.0) / 3
        assert abs(stats.average_processing_time - expected_avg) < 0.001


class TestFolderInfo:
    """测试FolderInfo数据模型"""
    
    def test_folder_info_creation(self):
        """测试FolderInfo创建"""
        folder = FolderInfo(
            path="/path/to/src",
            name="src",
            level=1,
            file_count=10,
            c_file_count=5,
            h_file_count=3,
            semantic_category="core"
        )
        
        assert folder.path == "/path/to/src"
        assert folder.name == "src"
        assert folder.level == 1
        assert folder.file_count == 10
        assert folder.c_file_count == 5
        assert folder.h_file_count == 3
        assert folder.semantic_category == "core"
    
    def test_folder_info_validation(self):
        """测试FolderInfo数据验证"""
        # 测试空路径
        with pytest.raises(ValueError, match="folder path cannot be empty"):
            FolderInfo("", "src", 1, 10, 5, 3, "core")
        
        # 测试负数级别
        with pytest.raises(ValueError, match="folder level must be non-negative"):
            FolderInfo("/path", "src", -1, 10, 5, 3, "core")
        
        # 测试负数文件数
        with pytest.raises(ValueError, match="file_count must be non-negative"):
            FolderInfo("/path", "src", 1, -10, 5, 3, "core")


class TestFolderStructure:
    """测试FolderStructure数据模型"""
    
    def test_folder_structure_creation(self):
        """测试FolderStructure创建"""
        structure = FolderStructure()
        
        assert structure.folders == []
        assert structure.files == []
        assert structure.naming_patterns == {}
    
    def test_add_folder(self):
        """测试添加文件夹"""
        structure = FolderStructure()
        folder = FolderInfo("/path", "src", 1, 10, 5, 3, "core")
        
        structure.add_folder(folder)
        
        assert len(structure.folders) == 1
        assert structure.folders[0] == folder
    
    def test_get_folders_by_category(self):
        """测试根据分类获取文件夹"""
        structure = FolderStructure()
        
        core_folder = FolderInfo("/src", "src", 1, 10, 5, 3, "core")
        test_folder = FolderInfo("/test", "test", 1, 5, 3, 1, "test")
        lib_folder = FolderInfo("/lib", "lib", 1, 8, 4, 2, "lib")
        
        structure.add_folder(core_folder)
        structure.add_folder(test_folder)
        structure.add_folder(lib_folder)
        
        core_folders = structure.get_folders_by_category("core")
        test_folders = structure.get_folders_by_category("test")
        
        assert len(core_folders) == 1
        assert core_folders[0] == core_folder
        assert len(test_folders) == 1
        assert test_folders[0] == test_folder


class TestDocumentation:
    """测试Documentation数据模型"""
    
    def test_documentation_creation(self):
        """测试Documentation创建"""
        doc = Documentation()
        
        assert doc.readme_files == {}
        assert doc.file_comments == {}
        assert doc.api_docs == []
    
    def test_add_readme(self):
        """测试添加README文件"""
        doc = Documentation()
        doc.add_readme("README.md", "# Project Title\nDescription")
        
        assert "README.md" in doc.readme_files
        assert doc.readme_files["README.md"] == "# Project Title\nDescription"
    
    def test_add_comments(self):
        """测试添加文件注释"""
        doc = Documentation()
        comments = ["/* Main function */", "// Initialize system"]
        doc.add_comments("main.c", comments)
        
        assert "main.c" in doc.file_comments
        assert doc.file_comments["main.c"] == comments
    
    def test_get_all_text(self):
        """测试获取所有文档文本"""
        doc = Documentation()
        doc.add_readme("README.md", "Project description")
        doc.add_comments("main.c", ["/* comment 1 */", "/* comment 2 */"])
        doc.api_docs.append("API documentation")
        
        all_text = doc.get_all_text()
        
        assert "Project description" in all_text
        assert "/* comment 1 */" in all_text
        assert "/* comment 2 */" in all_text
        assert "API documentation" in all_text


class TestAnalysisResult:
    """测试AnalysisResult数据模型"""
    
    def test_analysis_result_creation(self):
        """测试AnalysisResult创建"""
        folder_structure = FolderStructure()
        documentation = Documentation()
        functions = [
            Function("func1", "void func1() {}", 1, 3, "/test.c"),
            Function("func2", "void func2() {}", 5, 7, "/test.c")
        ]
        call_relationships = [
            FunctionCall("func1", "func2", "direct", 2, "/test.c", "func2();")
        ]
        function_embeddings = []
        doc_embeddings = []
        fallback_stats = FallbackStats()
        
        result = AnalysisResult(
            folder_structure=folder_structure,
            documentation=documentation,
            functions=functions,
            call_relationships=call_relationships,
            function_embeddings=function_embeddings,
            doc_embeddings=doc_embeddings,
            fallback_stats=fallback_stats
        )
        
        assert result.folder_structure == folder_structure
        assert result.documentation == documentation
        assert len(result.functions) == 2
        assert len(result.call_relationships) == 1
    
    def test_get_function_calls_by_caller(self):
        """测试根据调用者获取函数调用"""
        call_relationships = [
            FunctionCall("main", "func1", "direct", 10, "/test.c", "func1();"),
            FunctionCall("main", "func2", "direct", 11, "/test.c", "func2();"),
            FunctionCall("func1", "helper", "direct", 20, "/test.c", "helper();")
        ]
        
        result = AnalysisResult(
            folder_structure=FolderStructure(),
            documentation=Documentation(),
            functions=[],
            call_relationships=call_relationships,
            function_embeddings=[],
            doc_embeddings=[],
            fallback_stats=FallbackStats()
        )
        
        main_calls = result.get_function_calls_by_caller("main")
        assert len(main_calls) == 2
        assert all(call.caller_name == "main" for call in main_calls)
        
        func1_calls = result.get_function_calls_by_caller("func1")
        assert len(func1_calls) == 1
        assert func1_calls[0].callee_name == "helper"
    
    def test_get_function_calls_by_callee(self):
        """测试根据被调用者获取函数调用"""
        call_relationships = [
            FunctionCall("main", "helper", "direct", 10, "/test.c", "helper();"),
            FunctionCall("func1", "helper", "direct", 20, "/test.c", "helper();"),
            FunctionCall("func2", "other", "direct", 30, "/test.c", "other();")
        ]
        
        result = AnalysisResult(
            folder_structure=FolderStructure(),
            documentation=Documentation(),
            functions=[],
            call_relationships=call_relationships,
            function_embeddings=[],
            doc_embeddings=[],
            fallback_stats=FallbackStats()
        )
        
        helper_callers = result.get_function_calls_by_callee("helper")
        assert len(helper_callers) == 2
        assert all(call.callee_name == "helper" for call in helper_callers)
        
        other_callers = result.get_function_calls_by_callee("other")
        assert len(other_callers) == 1
        assert other_callers[0].caller_name == "func2"


# Story 2.1.2 新增测试 - 扩展数据模型功能测试

class TestFunctionExtensions:
    """测试Function扩展功能"""
    
    def test_function_call_management(self):
        """测试函数调用关系管理"""
        func = Function("main", "int main() { printf(); }", 1, 5, "/test.c")
        
        # 测试添加调用关系
        func.add_call("printf", "printf(\"Hello\\n\");")
        func.add_call("malloc", "ptr = malloc(100);")
        
        assert len(func.calls) == 2
        assert "printf" in func.calls
        assert "malloc" in func.calls
        assert len(func.call_contexts["printf"]) == 1
        assert "printf(\"Hello\\n\");" in func.call_contexts["printf"]
    
    def test_function_caller_management(self):
        """测试函数调用者关系管理"""
        func = Function("helper", "void helper() {}", 10, 15, "/test.c")
        
        # 测试添加调用者
        func.add_caller("main")
        func.add_caller("init")
        func.add_caller("main")  # 重复添加应该被忽略
        
        assert len(func.called_by) == 2
        assert "main" in func.called_by
        assert "init" in func.called_by
    
    def test_function_metrics(self):
        """测试函数指标计算"""
        func = Function("complex_func", "void complex_func() { /* 10 lines */ }", 1, 10, "/test.c")
        func.add_call("func1")
        func.add_call("func2")
        func.add_call("func3")
        
        # 测试基本指标
        assert func.get_call_count() == 3
        assert func.get_caller_count() == 0
        assert func.get_lines_of_code() == 10
        assert func.is_leaf_function() == False
        assert func.is_entry_function() == True
        
        # 测试复杂度计算
        complexity = func.calculate_complexity_score()
        assert complexity > 0
        assert isinstance(complexity, float)
    
    def test_function_attributes(self):
        """测试函数属性设置"""
        func = Function(
            "static_func", "static void func() {}", 1, 3, "/test.c",
            is_static=True, is_inline=False, 
            parameter_types=["int", "char*"],
            docstring="This is a test function"
        )
        
        assert func.is_static == True
        assert func.is_inline == False
        assert len(func.parameter_types) == 2
        assert func.docstring == "This is a test function"


class TestFileInfoExtensions:
    """测试FileInfo扩展功能"""
    
    def test_file_info_extended_creation(self):
        """测试扩展FileInfo创建"""
        file_info = FileInfo(
            path="/test/example.c", name="example.c", size=1024, 
            last_modified=datetime.now(), file_type="c",
            line_count=50, code_lines=35, comment_lines=10, blank_lines=5
        )
        
        assert file_info.file_type == "c"
        assert file_info.line_count == 50
        assert file_info.code_lines == 35
        assert file_info.comment_lines == 10
        assert file_info.blank_lines == 5
    
    def test_file_info_function_management(self):
        """测试文件函数管理"""
        file_info = FileInfo("/test.c", "test.c", 1024, datetime.now())
        
        func1 = Function("func1", "void func1() {}", 1, 3, "/test.c")
        func2 = Function("func2", "void func2() {}", 5, 7, "/test.c")
        
        file_info.add_function(func1)
        file_info.add_function(func2)
        file_info.add_function(func1)  # 重复添加应该被忽略
        
        assert file_info.get_function_count() == 2
        assert file_info.get_function_by_name("func1") == func1
        assert file_info.get_function_by_name("nonexistent") is None
    
    def test_file_metrics_calculation(self):
        """测试文件指标计算"""
        file_info = FileInfo("/test.c", "test.c", 2048, datetime.now())
        file_info.line_count = 100
        file_info.code_lines = 80
        file_info.macro_definitions = ["MACRO1", "MACRO2"]
        file_info.includes = ["stdio.h", "stdlib.h"]
        
        func1 = Function("func1", "void func1() {}", 1, 10, "/test.c")
        func2 = Function("func2", "void func2() {}", 15, 25, "/test.c")
        file_info.add_function(func1)
        file_info.add_function(func2)
        
        metrics = file_info.calculate_file_metrics()
        
        assert metrics['function_count'] == 2
        assert metrics['total_loc'] == 21  # (10-1+1) + (25-15+1) = 10 + 11 = 21
        assert metrics['include_count'] == 2
        assert metrics['macro_count'] == 2
        assert metrics['file_size_kb'] == 2.0
        assert metrics['code_density'] == 0.8  # 80/100


class TestParsedCodeExtensions:
    """测试ParsedCode扩展功能"""
    
    def test_parsed_code_call_relationship_management(self):
        """测试解析代码调用关系管理"""
        file_info = FileInfo("/test.c", "test.c", 1024, datetime.now())
        func1 = Function("main", "int main() {}", 1, 5, "/test.c")
        func2 = Function("helper", "void helper() {}", 10, 15, "/test.c")
        
        parsed_code = ParsedCode(file_info, [func1, func2])
        
        # 添加调用关系
        parsed_code.add_function_call_relationship("main", "helper", "direct", 3, "helper();")
        
        assert len(parsed_code.call_relationships) == 1
        
        # 验证Function对象也被更新
        assert "helper" in func1.calls
        assert "main" in func2.called_by
        
        # 测试查询功能
        main_calls = parsed_code.get_call_relationships_by_caller("main")
        assert len(main_calls) == 1
        assert main_calls[0].callee_name == "helper"
        
        helper_callers = parsed_code.get_call_relationships_by_callee("helper")
        assert len(helper_callers) == 1
        assert helper_callers[0].caller_name == "main"
    
    def test_parsed_code_function_analysis(self):
        """测试解析代码函数分析"""
        file_info = FileInfo("/test.c", "test.c", 1024, datetime.now())
        
        main_func = Function("main", "int main() {}", 1, 5, "/test.c")
        helper_func = Function("helper", "void helper() {}", 10, 15, "/test.c")
        leaf_func = Function("leaf", "void leaf() {}", 20, 25, "/test.c")
        
        parsed_code = ParsedCode(file_info, [main_func, helper_func, leaf_func])
        
        # 设置调用关系：main -> helper -> leaf
        parsed_code.add_function_call_relationship("main", "helper", "direct", 3)
        parsed_code.add_function_call_relationship("helper", "leaf", "direct", 12)
        
        # 测试入口函数查找
        entry_functions = parsed_code.find_entry_functions()
        assert len(entry_functions) == 1
        assert entry_functions[0].name == "main"
        
        # 测试叶子函数查找
        leaf_functions = parsed_code.find_leaf_functions()
        assert len(leaf_functions) == 1
        assert leaf_functions[0].name == "leaf"
        
        # 测试调用图生成
        call_graph = parsed_code.get_function_call_graph()
        assert "main" in call_graph
        assert "helper" in call_graph["main"]
        assert "leaf" in call_graph["helper"]
    
    def test_parsed_code_summary_and_validation(self):
        """测试解析代码摘要和验证"""
        file_info = FileInfo("/test.c", "test.c", 1024, datetime.now())
        functions = [Function("func1", "void func1() {}", 1, 5, "/test.c")]
        
        parsed_code = ParsedCode(
            file_info, functions, 
            parsing_time=0.5, parsing_method="tree_sitter", error_count=0
        )
        parsed_code.warnings.append("Unused variable warning")
        
        # 测试摘要生成
        summary = parsed_code.get_parsing_summary()
        assert summary['file_path'] == "/test.c"
        assert summary['function_count'] == 1
        assert summary['parsing_time'] == 0.5
        assert summary['parsing_method'] == "tree_sitter"
        assert summary['warning_count'] == 1
        
        # 测试验证功能
        parsed_code.add_function_call_relationship("nonexistent", "func1", "direct", 10)
        validation_errors = parsed_code.validate_call_relationships()
        assert len(validation_errors) > 0
        assert "nonexistent" in validation_errors[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 