# Security model and reporting

- **Trust boundary:** MCP client may request queries, but cannot select a path, bypass the configured wing allowlist, run commands or modify the database. The configured database is opened with `mode=ro` and `PRAGMA query_only`.
- **Bounded execution:** 160-character query, 12 tokens, up to 10 hits, max 2600 excerpt characters/hit, SQLite progress timeout and no child processes.
- **Privacy:** Returned snippets and provenance paths may be disclosed to the AI host. Exclude secret/private wings from `allowed_wings`.
- **No credential storage** and no network listener. This is *not* a sandbox for untrusted arbitrary SQLite databases; only configure indices you control.
- **Prompt injection:** Database content is untrusted and must not become higher-priority instructions.
- **Known limitations:** Chroma trigram FTS needs ≥3 chars per search token; lexical matches may miss semantically related information. Concurrent writers / WAL snapshots and index corruption may cause query failure. Source paths and line references are index metadata, not proof that original files still exist.

For suspected vulnerabilities, use GitHub's private vulnerability reporting if enabled, or contact maintainers privately before opening a public issue containing exploit details. Never upload private palaces, tokens, or chat logs to bug reports.
