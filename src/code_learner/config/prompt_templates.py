# A centralized repository for all LLM prompt templates.
# This makes it easy to view, manage, and experiment with different prompts
# without changing the core application logic.

TEMPLATES = {
    "intent_analysis_default": """
Analyze the user's query about a C codebase and break it down into structured intents.

**User Query:**
"{query}"

**Instructions:**
1.  Identify the primary function, file, or concept the user is asking about.
2.  Determine the user's core intent (e.g., "explain code", "find risks", "show usage", "find dependencies").
3.  Generate a list of sub-queries that can be used to retrieve relevant context from different sources (vector search, graph database).
4.  Return the result as a JSON object with the following structure:
    {{
        "primary_entity": "The main function/file name, or 'general' if none.",
        "core_intent": "A short phrase describing the user's goal.",
        "sub_queries": [
            {{"source": "vector", "query": "A query optimized for semantic search."}},
            {{"source": "graph_calls", "query": "A query for the graph DB about function calls."}},
            {{"source": "graph_dependencies", "query": "A query for the graph DB about file dependencies."}}
        ]
    }}

**JSON Output:**
""",

    "rerank_default": """
You are an expert C programmer and a code analysis assistant.
Your task is to re-rank a list of context snippets based on their relevance to the user's original query.

**User Query:**
"{query}"

**Context Snippets to Re-rank:**
Each snippet is identified by an index (e.g., [0], [1], ...).
---
{context_items}
---

**Instructions:**
1.  Carefully read the user's query and each context snippet.
2.  Evaluate how well each snippet helps to answer the query. Consider both direct relevance and supporting information.
3.  Provide a new, re-ordered list of the indices of the most relevant snippets, from most to least relevant.
4.  Return ONLY a JSON list of integers representing the new order. For example: [3, 1, 0, 4, 2].

**Your JSON Response (only the list of indices):**
""",

    "qa_default": """
You are a world-class C programming expert and a helpful AI assistant.
Your task is to provide a clear, comprehensive, and accurate answer to the user's question based *only* on the provided context.

**User's Question:**
{query}

**Provided Context:**
---
{context}
---

**Instructions:**
1.  Synthesize the information from all context snippets. Do not use any external knowledge.
2.  Structure your answer clearly. Use markdown for formatting (e.g., code blocks, lists).
3.  If the context contains code, explain what it does, its purpose, and any potential implications.
4.  If the context is insufficient to answer the question fully, state that clearly. Do not make up information.
5.  Answer in the same language as the user's question.

**Your Answer:**
"""
}

# You can add more specialized templates here,
# e.g., "rerank_for_debugging", "intent_analysis_for_refactoring", etc. 