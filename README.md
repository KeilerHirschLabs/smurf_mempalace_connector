# SMURF – MemPalace Connector

**Secure MemPalace Utility for Retrieval & Filtering**

by **KeilerHirsch Labs**

> Connect MemPalace to OpenAI workflows. Retrieve source-grounded memories with read-only access and traceable references.

SMURF is a source-grounded, read-only connector between a **locally configured MemPalace SQLite index** and supported OpenAI/ChatGPT/Codex MCP execution modes. It is not MemPalace itself, an official OpenAI product, or a separate AI memory platform.

## OpenAI Marketplace plugin

A private **SMURF – MemPalace Connector** plugin exists for OpenAI ecosystem testing. **It is not publicly listed or generally installable from the OpenAI Plugin Marketplace.** A public Marketplace launch requires further testing. This GitHub source repository is already public; that does not make the OpenAI plugin public.

Selected ChatGPT Plus Work environments have been tested using synthetic data; the current package has local MCP/SQLite fixture tests. Ordinary ChatGPT chats and broader host compatibility are **not confirmed** to expose the local MCP connector.

## Capabilities and limitations

- `khl_recall_status`: verify the locally configured index, detected backend and allowed wing filters.
- `khl_recall_search`: bounded read-only **SQLite FTS5 lexical search**, with source-file and line-range provenance where available.
- Supports MemPalace `sqlite_exact` / `rust_exact` and Chroma SQLite indices. No migration or embeddings generation.
- Uses standard Python 3.10+, SQLite `mode=ro`, `PRAGMA query_only`, a query-time budget, and a configured wing allowlist; no background daemon, network listener, API key, or writer tool.

This is **not** semantic retrieval, host-side background memory, automatic prompt injection, original-file verification, or guaranteed cross-session continuity. Results may be stale; verify original sources for consequential decisions.

## Setup

1. Install a compatible MemPalace local index and have Python 3.10+ with SQLite FTS5 available.
2. Clone the current `main` branch of [smurf_mempalace_connector](https://github.com/KeilerHirschLabs/smurf_mempalace_connector) into a stable local directory. Do **not** install the historical `v0.2.0` release archive as SMURF: its plugin manifest still uses the earlier `khl-mempalace-recall` package slug. Until a new SMURF release is published, use the current `main` branch.
3. Copy `config.example.json` to the plugin config location and enter your own **absolute** SQLite index path. On Windows the default is `%APPDATA%/KeilerHirschLabs/MemPalaceRecall/config.json`; on Linux/macOS use `~/.config/keilerhirschlabs/mempalace-recall/config.json`. `KHL_RECALL_CONFIG` can point to another absolute JSON config.
4. Restrict `allowed_wings` to exactly the data intended for use with the invoking AI host. The `*` wildcard explicitly permits all wings and may expose sensitive content.
5. Install/register the plugin using a host that supports local stdio MCP execution. The MCP server command is `python -u ${PLUGIN_ROOT}/server/readonly_mcp.py`; the marketplace package slug is `smurf-mempalace-connector` (the GitHub repository uses underscores only in its repository name). Use `khl_recall_status` before trying searches.

A failed or unavailable host tool is not a successful search. For local smoke tests, run `python -m unittest discover -s tests -v`.

## Data protection

The connector never modifies the configured SQLite index. **Returned snippets and source paths may be sent by the MCP host to the AI provider.** This boundary must be understood before enabling sensitive wings. See [Privacy](PRIVACY.md), [Security](SECURITY.md), and [Terms](TERMS.md).

## Publisher and licence

**KeilerHirsch Labs** — independent community integration, unaffiliated with OpenAI or the upstream MemPalace maintainers. Licensed **EUPL-1.2**; the full canonical licence text is in [`LICENSE`](LICENSE). Attribution and provenance must be preserved in distributed derivatives.
