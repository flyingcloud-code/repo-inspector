"""Integration test: parse C file and store CALLS relationships in Neo4j (真实数据库)"""

import os
from pathlib import Path

import pytest
from src.code_learner.parser.c_parser import CParser
from src.code_learner.storage.neo4j_store import Neo4jGraphStore

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")


@pytest.fixture(scope="module")
def graph_store():
    store = Neo4jGraphStore()
    assert store.connect(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    store.clear_database()
    yield store
    store.clear_database()
    store.close()


@pytest.fixture(scope="module")
def parser():
    return CParser()


def test_parse_and_store_calls(graph_store: Neo4jGraphStore, parser: CParser, tmp_path):
    c_code = """
void foo() {}
void bar() { foo(); }
int main() { bar(); return 0; }
"""
    file_path = tmp_path / "calls.c"
    file_path.write_text(c_code)
    
    # 解析文件
    parsed = parser.parse_file(str(file_path))
    
    # 存储解析结果（包含函数和调用关系）
    assert graph_store.store_parsed_code(parsed)
    
    # 验证 CALLS 关系
    with graph_store.driver.session() as session:
        result = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) as cnt")
        count = result.single()["cnt"]
        assert count >= 2  # bar->foo, main->bar


def test_complex_call_patterns(graph_store: Neo4jGraphStore, parser: CParser, tmp_path):
    c_code = """
struct obj { void (*method)(); };
void target() {}
void caller() {
    struct obj o;
    o.method = target;
    o.method();  // member call
    target();    // direct call
}
"""
    file_path = tmp_path / "complex.c"
    file_path.write_text(c_code)
    
    parsed = parser.parse_file(str(file_path))
    assert graph_store.store_parsed_code(parsed)
    
    # 验证存储的调用关系
    with graph_store.driver.session() as session:
        result = session.run(
            "MATCH (caller:Function {name: 'caller'})-[r:CALLS]->(callee:Function) "
            "RETURN callee.name as name, r.call_type as type"
        )
        calls = [(rec["name"], rec["type"]) for rec in result]
        assert len(calls) >= 1  # 至少有一个调用关系


def test_store_call_relationship_single(graph_store: Neo4jGraphStore):
    """测试单个调用关系存储"""
    assert graph_store.store_call_relationship("test_caller", "test_callee", "direct")
    
    # 验证关系存在
    with graph_store.driver.session() as session:
        result = session.run(
            "MATCH (a:Function {name: 'test_caller'})-[r:CALLS]->(b:Function {name: 'test_callee'}) "
            "RETURN r.call_type as type"
        )
        record = result.single()
        assert record is not None
        assert record["type"] == "direct" 