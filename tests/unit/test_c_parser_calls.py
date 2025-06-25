"""CParser 函数调用提取单元测试

要求：
1. 不使用 mock 或 patch
2. 真实运行 Tree-sitter 解析
"""

from pathlib import Path

import pytest

from src.code_learner.parser.c_parser import CParser


@pytest.fixture(scope="module")
def parser():
    return CParser()


def _write_tmp(tmp_path: Path, name: str, content: str) -> Path:
    file_path = tmp_path / name
    file_path.write_text(content)
    return file_path


def test_extract_direct_call(parser, tmp_path):
    c_code = """
void callee() {}
void caller() {
    callee();
}
"""
    fp = _write_tmp(tmp_path, "direct.c", c_code)
    calls = parser.extract_function_calls(c_code, str(fp))
    assert any(c.call_type == "direct" and c.callee_name == "callee" for c in calls)


def test_extract_member_call(parser, tmp_path):
    c_code = """
struct st { int (*fp)(); };
int target() { return 0; }
void caller(struct st *s) {
    s->fp();
}
"""
    fp = _write_tmp(tmp_path, "member.c", c_code)
    calls = parser.extract_function_calls(c_code, str(fp))
    assert any(c.call_type == "member" for c in calls)


def test_extract_pointer_call(parser, tmp_path):
    c_code = """
int target() { return 0; }
void caller() {
    int (*fp)() = target;
    (*fp)();
}
"""
    fp = _write_tmp(tmp_path, "pointer.c", c_code)
    calls = parser.extract_function_calls(c_code, str(fp))
    assert any(c.call_type in ("pointer", "direct") for c in calls)


def test_extract_recursive_call(parser, tmp_path):
    c_code = """
int fact(int n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}
"""
    fp = _write_tmp(tmp_path, "recursive.c", c_code)
    calls = parser.extract_function_calls(c_code, str(fp))
    assert any(c.call_type == "recursive" and c.callee_name == "fact" for c in calls) 