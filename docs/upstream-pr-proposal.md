# Proposal: community ChatGPT Plus Work / Codex local MCP read-only bridge

**Project:** KHL MemPalace Recall (independent KeilerHirschLabs integration)

## Evidence

A predecessor v0.1.3 prototype was invoked from ChatGPT Plus Work in *two execution modes* on Windows 11 (November 13, 2026). The test index contained a synthetic source marker `LAB-ORION-7319`. Both modes returned the same verbatim source and line range. Observed outer call latency was 116–132 ms for search and 23–45 ms for status; these are **one-system smoke tests, not general performance benchmarks**. Ordinary ChatGPT chats were not demonstrated to support the local tools.

## Technical scope

The community v0.2.0 bridge wraps only SQLite FTS5, with no MemPalace writes, re-mining, migrations, vector retrieval or arbitrary MCP exec. Supports Chroma and sqlite_exact/rust_exact index structures. Deliberately avoids claiming to replace native MemPalace MCP or core memory management.

## Suggested upstream contribution

A brief documentation link under integrations or FAQ, with truthful setup requirements, security disclosure, community-maintained status, and limitations. Do not merge the entire external implementation into upstream without maintainers' approval. Wait for public repo, reproducible tests, and a maintainer response before broad integration claims.
