# SMURF – MemPalace Connector v0.3.0 (MCP tool naming)

- Renamed public MCP tool identifiers to `smurf_recall_status` and `smurf_recall_search` to match the SMURF brand across the Skill, server, tests, and review metadata.
- **Breaking change for callers:** update prompts, saved tool references and integrations using v0.2.x tool identifiers. Search logic, read-only boundary, index configuration and filtering are unchanged.
- Kept the plugin private; public GitHub source does not imply a public OpenAI Marketplace listing.

# SMURF – MemPalace Connector (0.2.2, branding alignment)

- Unified display name, Skill metadata, MCP server alias, README and public publisher text as SMURF – MemPalace Connector by KeilerHirsch Labs.
- Aligned licence metadata and Terms to the repository's EUPL-1.2 (canonical full text on GitHub).
- Retained `khl_recall_status` and `khl_recall_search` APIs and unchanged read-only implementation.
- OpenAI plugin remains PRIVATE. GitHub source updates do not publish the Marketplace listing or establish general host compatibility.

## Previous 0.2.0 technical scope

- Read-only SQLite FTS5 search against MemPalace `sqlite_exact`/`rust_exact` and Chroma indices.
- Explicit local wing allowlist, bounded source excerpts and source-reference metadata.
- No database writes or telemetry; availability depends on supported local MCP hosts.
