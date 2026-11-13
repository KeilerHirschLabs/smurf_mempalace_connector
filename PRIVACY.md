# Privacy – KHL MemPalace Recall

This local open-source plugin does not operate an independent cloud backend or telemetry service. It reads only the configured MemPalace SQLite index and returns a limited set of matching snippets, source paths and line references to the MCP host upon request. It does not collect user accounts, passwords, payment data or analytics for KeilerHirschLabs.

**Host disclosure:** Tool responses become available to the invoking ChatGPT/Codex environment. Depending on the product, configuration and execution mode, the host may transmit tool results to its cloud service. This is outside the plugin's control. Users choose which palace and wings the plugin may read. Do not expose sensitive wings to a host you do not trust.

**Retention:** The plugin itself creates no persistent record of queries or results. Your existing MemPalace index, source files, OS logs, the host's chat history and service retention are governed by their own settings and providers. This plugin does not delete or alter any of those records. To stop disclosure, remove/disable the plugin and its local configuration; deleting the plugin does not erase host chat history.

**Support:** Bugs and security issues can be reported through the project's GitHub repository. See `SECURITY.md`. The maintainers do not obtain automatic remote access to your machine.
