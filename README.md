# KHL MemPalace Recall

**An independent, source-grounded, read-only MemPalace ↔ ChatGPT Desktop Work bridge** by [KeilerHirschLabs](https://github.com/KeilerHirschLabs). Community project; not affiliated with OpenAI or the MemPalace maintainers.

> Status: **community preview v0.2.0**. A private earlier prototype passed real ChatGPT Plus Work (local and cloud-mode) tests on one Windows installation, with a synthetic `sqlite_exact` dataset. This generic v0.2.0 package is tested with local MCP/SQLite fixtures; broader ChatGPT deployments remain to be verified. **Ordinary ChatGPT chats have not been proven to expose this local plugin.**

## What it actually does

- `khl_recall_status`: verify one locally configured SQLite index and allowed wing filters.
- `khl_recall_search`: fast read-only **lexical FTS5** search with quoted-safe terms, bounded results, source-file and line-range provenance.
- Supports **MemPalace `sqlite_exact`/`rust_exact`** (`sqlite_exact.sqlite3`) and **Chroma** (`chroma.sqlite3`) indices, with no migration and no embedding generation.
- Uses stdlib Python 3.10+, SQLite `mode=ro`, `PRAGMA query_only`, query-time budget, explicit local wing allowlist. No daemon, network listener, hidden uploads, API key, or write tool.

**Not** semantic vector retrieval, background memory, model training, automatic contextual injection, MemPalace's full MCP API, or guaranteed continuity across all chats. Original files and indices remain authoritative; results can be stale.

## Requirements

- Windows desktop (Windows 11 test environment), Python 3.10+ in PATH with SQLite FTS5 enabled.
- Local MemPalace palace created with a supported index backend.
- ChatGPT/Codex host capable of running a **local stdio MCP plugin**. Our working installation used ChatGPT Plus **Work**, in both tested execution modes. Availability depends on account and host; ordinary chats may not expose local MCP.

## Install on your own machine

1. Download this repository/release to a stable local folder. Do **not** use another person's local paths.
2. Create your own config file:
   - Windows: `%APPDATA%\KeilerHirschLabs\MemPalaceRecall\config.json`
   - Linux/macOS: `~/.config/keilerhirschlabs/mempalace-recall/config.json`
   - Or point `KHL_RECALL_CONFIG` to another **absolute** JSON config path.
3. Use `config.example.json` as a starting point, replacing `database` with an **absolute path** to your own `sqlite_exact.sqlite3` or `chroma.sqlite3`. Set `allowed_wings` to one or more wing names; **`["*"]` explicitly permits all wings and may expose sensitive content**, so use only when you understand the risk.
4. Install the plugin using your host's supported **local marketplace** flow; for Codex CLI, register the local marketplace and install `khl-mempalace-recall@<marketplace-name>`. The portable `plugin.json`, `mcp.json`, and compatibility manifests are included. The plugin runs `python -u ${PLUGIN_ROOT}/server/readonly_mcp.py`.
5. In a **local Work** task, select the plugin and ask: “Check KHL MemPalace Recall status and search for my earlier decision about X.” Only claim success when a real `tools/call` returned results.

**Troubleshooting:** If `tools/list` works locally but the AI cannot call the tools, check host plugin activation, local vs cloud execution mode, plugin cache and local tool discovery. Do not reinstall MemPalace or increase your plan until the execution mode is verified. Run local tests with `python -m unittest discover -s tests -v`.

## Security and data flow

Your SQLite database is never modified by this plugin. **When an AI invokes the search tool, the retrieved source snippets are returned to the host and may be transmitted to the AI provider.** This is an explicit client-side disclosure boundary; do not permit Wings containing sensitive or confidential material unless you intend to share that content with the host. Read `PRIVACY.md` and `SECURITY.md` before use.

The plugin does not upload anything directly, run arbitrary commands, or accept paths from AI tools. Source text is untrusted data: the skill instructs the model to ignore instructions embedded in results. No automated indexing or migration is performed.

## Upstream PR scope

We welcome an upstream MemPalace documentation/integration PR after public source release and maintainers' review; upstream should not be asked to adopt unsupported claims about ChatGPT access. See `docs/upstream-pr-proposal.md`.

## License

MIT, © 2026 KeilerHirschLabs. MemPalace is a separate project with its own licenses and maintainers.
