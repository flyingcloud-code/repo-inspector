import logging
from typing import List, Dict, Any, Set

from ..core.context_models import ContextItem, SourceType
from ..core.retriever_interfaces import IContextRetriever
from ..storage.neo4j_store import Neo4jGraphStore
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class GraphContextRetriever(IContextRetriever):
    """
    Retrieves structured context from the Neo4j graph database.
    This single retriever handles various types of graph queries.
    """
    def __init__(self, project_id: str):
        """初始化GraphContextRetriever"""
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        config = self.config.get_config().database
        self.graph_store = Neo4jGraphStore(
            project_id=project_id,
            uri=config.neo4j_uri,
            user=config.neo4j_user,
            password=config.neo4j_password
        )
        logger.info("GraphContextRetriever initialized.")

    def get_source_type(self) -> SourceType:
        """Returns the source type of this retriever."""
        return SourceType.GRAPH_FUNCTION_DEFINITION # Generic graph source

    def is_available(self) -> bool:
        """Checks if the graph store is available."""
        return self.graph_store.is_available()

    def retrieve(self, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """
        Retrieves context from the graph database based on intent.
        This simplified version runs queries sequentially for robustness.
        """
        all_items: List[ContextItem] = []
        function_names = intent.get("functions", [])
        
        if not function_names:
            self.logger.info("No function names in intent, GraphContextRetriever has nothing to do.")
            return []

        self.logger.info(f"Graph retriever processing functions: {function_names}")

        for func_name in function_names:
            # 1. Get function definition (most important)
            definition = self._get_function_definition(func_name)
            if definition:
                self.logger.info(f"Found definition for '{func_name}'")
                all_items.extend(definition)

            # 2. Get callees
            callees = self._get_callees(func_name)
            if callees:
                self.logger.info(f"Found {len(callees)} callees for '{func_name}'")
                all_items.extend(callees)
            
            # 3. Get callers
            callers = self._get_function_callers(func_name)
            if callers:
                self.logger.info(f"Found {len(callers)} callers for '{func_name}'")
                all_items.extend(callers)

        # Deduplicate and return
        seen_content = set()
        deduplicated_items = []
        for item in all_items:
            # Simple content-based deduplication
            if item.content not in seen_content:
                deduplicated_items.append(item)
                seen_content.add(item.content)
        
        self.logger.info(f"Graph retrieval found {len(deduplicated_items)} items for functions: {function_names}")
        
        return deduplicated_items

    def _get_function_definition(self, func_name: str) -> List[ContextItem]:
        query = """
        MATCH (f:Function {name: $func_name})
        RETURN f.name AS name, f.code AS code, f.docstring AS docstring,
               f.file_path AS file_path, f.start_line AS start_line
        LIMIT 1
        """
        params = {"func_name": func_name}
        results = self.graph_store.query(query, params)
        return [
            ContextItem(
                content=f"Function: {r['name']}\nPath: {r['file_path']}\nDocstring: {r['docstring']}\n\n```c\n{r['code']}\n```",
                source="graph_function_definition",
                score=1.0,  # Highest score for direct definition
                metadata=r
            ) for r in results
        ]

    def _get_function_callers(self, func_name: str) -> List[ContextItem]:
        query = """
        MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $func_name})
        RETURN caller.name AS caller_name, caller.file_path AS file_path
        LIMIT 10
        """
        params = {"func_name": func_name}
        results = self.graph_store.query(query, params)
        return [
            ContextItem(
                content=f"Function `{r['caller_name']}` (in {r['file_path']}) calls `{func_name}`.",
                source="graph_function_callers",
                score=0.9,
                metadata=r
            ) for r in results
        ]

    def _get_callees(self, func_name: str) -> List[ContextItem]:
        query = """
        MATCH (caller:Function {name: $func_name})-[:CALLS]->(callee:Function)
        RETURN callee.name AS callee_name, callee.file_path AS file_path
        LIMIT 10
        """
        params = {"func_name": func_name}
        results = self.graph_store.query(query, params)
        return [
            ContextItem(
                content=f"Function `{func_name}` calls `{r['callee_name']}` (in {r['file_path']}).",
                source="graph_function_callees",
                score=0.85,
                metadata=r
            ) for r in results
        ]

    def _get_file_dependencies(self, func_name: str) -> List[ContextItem]:
        query = """
        MATCH (f:Function {name: $func_name})<-[:CONTAINS]-(file:File)
        MATCH (file)-[:DEPENDS_ON]->(dep_file:File)
        RETURN file.path AS source_file, dep_file.path AS dependency_file
        LIMIT 10
        """
        params = {"func_name": func_name}
        results = self.graph_store.query(query, params)
        return [
            ContextItem(
                content=f"The file `{r['source_file']}` (containing `{func_name}`) depends on `{r['dependency_file']}`.",
                source="graph_file_dependencies",
                score=0.8,
                metadata=r
            ) for r in results
        ]

    def _query_and_convert(self, query: str, params: Dict[str, Any], source_description: str) -> List[ContextItem]:
        """
        Args:
            query: Cypher查询语句
            params: 查询参数
            source_description: 描述来源的字符串 (e.g., "callers")
        
        Returns:
            List[ContextItem]
        """
        results = self.graph_store.run_query(query, params)
        return [
            ContextItem(
                content=item["content"],
                source=f"graph_{source_description}",
                score=1.0,  # 图数据库结果被认为是高相关的
                metadata=item
            )
            for item in results if item.get("content")
        ] 