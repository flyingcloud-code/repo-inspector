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
    def __init__(self):
        self.config = ConfigManager()
        self.graph_store = Neo4jGraphStore()
        logger.info("GraphContextRetriever initialized.")

    def get_source_type(self) -> SourceType:
        """Returns the source type of this retriever."""
        return SourceType.GRAPH_FUNCTION_DEFINITION # Generic graph source

    def is_available(self) -> bool:
        """Checks if the graph store is available."""
        return self.graph_store.is_available()

    def retrieve(self, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """
        Retrieves context from the graph database based on the query intent.
        """
        config = self.config.get_config()
        retriever_top_k = config.enhanced_query.sources["call_graph"]["top_k"]
        
        primary_entity = intent.get("primary_entity")
        core_intent = intent.get("core_intent")
        
        if not primary_entity or intent.get("core_intent") == "general":
            return []

        context_items: List[ContextItem] = []
        seen_items: Set[str] = set()

        try:
            # The order determines priority
            self._add_items(context_items, self._get_function_definition(primary_entity), seen_items)
            self._add_items(context_items, self._get_function_callers(primary_entity), seen_items)
            self._add_items(context_items, self._get_callees(primary_entity), seen_items)
            self._add_items(context_items, self._get_file_dependencies(primary_entity), seen_items)
        except Exception as e:
            logger.error(f"Graph retrieval for entity '{primary_entity}' failed: {e}", exc_info=True)

        return context_items[:retriever_top_k]

    def _add_items(self, all_items: List[ContextItem], new_items: List[ContextItem], seen: Set[str]):
        """Helper to add unique items to the list."""
        for item in new_items:
            if item.content not in seen:
                all_items.append(item)
                seen.add(item.content)

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