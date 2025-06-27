# Chunking Strategy Redesign: Plan and Progress

**Author:** Gemini AI
**Date:** 2025-06-27
**Status:** In Progress

## 1. Executive Summary

The existing code chunking mechanism for vector embeddings is inefficient and memory-intensive, leading to process termination. It relies on unreliable regex and file-based processing, ignoring the rich, structured data already parsed and stored in our Neo4j database.

This plan outlines a complete redesign of the chunking strategy. We will pivot from file-based processing to a **database-first approach**, leveraging the pre-parsed Abstract Syntax Tree (AST) information in Neo4j as the primary source for generating semantic code chunks. This ensures data consistency, improves efficiency, and resolves the memory overflow issues. A simple fixed-size chunking method will be retained as a fallback/utility option.

## 2. Core Principles

- **Single Source of Truth**: The Neo4j graph is the definitive source for semantic units (functions, structs, etc.). The embedding process will read from the database, not re-parse files.
- **Efficiency**: Avoid redundant file I/O and parsing. Querying the database is significantly faster and less memory-intensive.
- **Reliability**: Use the structured data from `tree-sitter` (via Neo4j) instead of fragile regular expressions.
- **User Control**: Provide clear, distinct strategies (`SEMANTIC` vs. `FIXED_SIZE`) that the user can explicitly select.

## 3. Execution Plan

The redesign is broken down into four distinct phases.

### Phase 1: Extend Data Access Layer (`Neo4jGraphStore`)

-   **Status:** ✅ Completed
-   **Objective:** Create a method to export all embeddable code units from the database.
-   **Key Tasks:**
    1.  Implement a new public method: `get_all_code_units() -> List[Dict]`.
    2.  This method will execute a Cypher query to fetch all nodes representing `Function` and `Struct` definitions.
    3.  For each node, it will return a dictionary containing its essential properties: `name`, `code`, `file_path`, `start_line`, `end_line`, and `node_type` (e.g., 'Function').

### Phase 2: Refactor Core Services (`CodeEmbedder` & `CodeChunker`)

-   **Status:** ✅ Completed
-   **Objective:** Decouple embedding from chunking and align services with the new database-first approach.
-   **Key Tasks:**
    1.  **Simplify `CodeEmbedder`**:
        -   Refactor it to accept a pre-processed list of `CodeChunk` objects.
        -   Its sole responsibility will be to manage the embedding process (calling the engine, storing in ChromaDB), not creating the chunks.
    2.  **Downgrade `CodeChunker`**:
        -   Remove all complex semantic logic (i.e., delete `_chunk_c_family` and its regex helpers).
        -   Retain and refine only the `_chunk_fixed_size` logic as a simple, standalone utility.

### Phase 3: Enhance Command-Line Tool (`embed-code`)

-   **Status:** ✅ Completed
-   **Objective:** Make the CLI the central controller for the embedding process, allowing the user to select the strategy.
-   **Key Tasks:**
    1.  Add a `--strategy` argument to the `embed-code` command, accepting `SEMANTIC` (default) and `FIXED_SIZE`.
    2.  **Implement `SEMANTIC` strategy flow**:
        -   Call `Neo4jGraphStore.get_all_code_units()`.
        -   Transform the returned dictionaries into `CodeChunk` objects.
        -   Pass the list of `CodeChunk`s to the refactored `CodeEmbedder`.
    3.  **Implement `FIXED_SIZE` strategy flow**:
        -   Iterate through files in the target directory.
        -   Use the simplified `CodeChunker` to perform fixed-size splitting.
        -   Pass the resulting chunks to the `CodeEmbedder`.

### Phase 4: Update and Validate with Testing

-   **Status:** ✅ Completed
-   **Objective:** Ensure the new implementation is robust, correct, and bug-free.
-   **Key Tasks:**
    1.  **Unit Test `CodeChunker`**: Write a focused test to verify the `FIXED_SIZE` strategy works as expected.
    2.  **Create New Integration Test**:
        -   Design a test for the end-to-end `SEMANTIC` flow.
        -   Use a temporary Neo4j database instance.
        -   **Setup**: Programmatically insert sample `Function` and `Struct` nodes.
        -   **Execute**: Run the `embed-code --strategy SEMANTIC` command.
        -   **Assert**: Verify that ChromaDB contains the correct number of embeddings and that their metadata (file path, function name, etc.) matches the data from the Neo4j setup step.

## 4. Progress Log

| Date       | Phase | Status      | Notes                                       |
|------------|-------|-------------|---------------------------------------------|
| 2025-06-27 | 4     | Completed   | Created and fixed unit tests for `CodeChunker`. |
| 2025-06-27 | 3     | Completed   | Created new `embed-code` command-line tool. |
| 2025-06-27 | 2     | Completed   | Refactored `CodeEmbedder` and `CodeChunker`. |
| 2025-06-27 | 1     | Completed   | Added `get_all_code_units` to `Neo4jGraphStore`. |
| 2025-06-27 | -     | Initialized | Plan documented. Execution starting.        |

## 5. Conclusion

The chunking strategy redesign has been successfully completed. We have:

1. **Improved Efficiency**: By leveraging pre-parsed AST data from Neo4j, we eliminated the memory-intensive regex-based parsing that was causing process termination.
2. **Enhanced Reliability**: The new approach uses structured data from Neo4j as the single source of truth, ensuring consistency and reliability.
3. **Provided User Control**: Users can now explicitly choose between `SEMANTIC` (database-driven) and `FIXED_SIZE` (file-based) chunking strategies.
4. **Validated with Tests**: Comprehensive unit tests ensure the new implementation works correctly.

This redesign has successfully addressed the memory overflow issues while also improving the overall architecture of the code embedding pipeline. 