# Privacy — SMURF – MemPalace Connector

SMURF is an independent, community-built, read-only local MCP connector published by **KeilerHirsch Labs**. It has no independent cloud backend, telemetry service or account system. It reads the configured MemPalace SQLite index and returns limited search results, source paths and provenance metadata to the invoking MCP host. It does not change the index or create its own query-history database.

## Host disclosure

When a user invokes SMURF, retrieved text and source paths become visible to the ChatGPT/Codex host and may be transmitted to that provider under its own service settings. This transmission is outside SMURF's control. The user decides which local database and wings are authorized through the connector configuration. **Do not authorize SECRET or other sensitive wings unless disclosure to the invoking host is acceptable.**

## Retention and deletion

SMURF itself does not persist search responses. Original MemPalace sources, SQLite files, OS logs and host-side chat or service records have separate retention and deletion controls. Uninstalling SMURF does not erase those records. SMURF does not obtain automatic remote access to your machine.

## Contact

For bugs, privacy questions and security reports, use the GitHub repository and its `SECURITY.md` reporting guidance. Project: https://github.com/KeilerHirschLabs/smurf_mempalace_connector
