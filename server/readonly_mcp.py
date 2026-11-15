"""SMURF – MemPalace Connector: local, bounded, read-only SQLite MCP bridge.

Supports the MemPalace sqlite_exact/rust_exact schema and Chroma's SQLite FTS5
storage. No subprocesses, indexing, writers, arbitrary file-path tool inputs,
HTTP listeners, API keys, or network requests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any

VERSION = "0.3.0"
PROTOCOL = "2025-06-18"
MAX_QUERY_CHARS = 160
MAX_QUERY_TOKENS = 12
MAX_OUTPUT_CHARS = 2600
DEFAULT_RESULTS = 5
MAX_RESULTS = 10
SQL_STEPS_LIMIT = 40000  # progress callbacks, ~4M SQLite VM operations


def config_path() -> Path:
    override = os.environ.get("KHL_RECALL_CONFIG")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "KeilerHirschLabs" / "MemPalaceRecall" / "config.json"
    return Path.home() / ".config" / "keilerhirschlabs" / "mempalace-recall" / "config.json"


def load_config() -> tuple[dict[str, Any], str | None]:
    p = config_path()
    if not p.is_file():
        return {}, "No configuration. Create the local config.json described in README.md."
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
        if not isinstance(obj, dict):
            return {}, "Config root must be a JSON object."
        db = obj.get("database")
        if not isinstance(db, str) or not db.strip():
            return {}, "Config.database must be an absolute path to an existing SQLite database."
        dbpath = Path(db).expanduser()
        if not dbpath.is_absolute() or dbpath.name.lower() not in {"sqlite_exact.sqlite3", "chroma.sqlite3"}:
            return {}, "Config.database must be an absolute path to sqlite_exact.sqlite3 or chroma.sqlite3."
        if not dbpath.is_file():
            return {}, "Configured SQLite database does not exist."
        wings = obj.get("allowed_wings")
        if not isinstance(wings, list) or not wings or len(wings) > 30 or not all(isinstance(w, str) and w.strip() and len(w) <= 100 for w in wings):
            return {}, "Config.allowed_wings must list 1–30 explicit wing names; '*' enables all wings."
        # '*' is the only wildcard. Explicit, intentional opt-in is required.
        if "*" in wings and len(wings) != 1:
            return {}, "Config.allowed_wings: '*' must be the only entry."
        return {"db": dbpath, "wings": frozenset(wings), "config": p}, None
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {}, f"Configuration cannot be read: {type(exc).__name__}."


def connect_ro(path: Path) -> sqlite3.Connection:
    # Path.as_uri percent-encodes Windows spaces; read-only URI mode forbids DB creation.
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    con.execute("PRAGMA query_only=ON")
    con.execute("PRAGMA busy_timeout=2000")
    return con


def detect_backend(con: sqlite3.Connection) -> str:
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('docs_fts','documents','collections','embedding_fulltext_search','embedding_metadata','embeddings')")}
    if {"docs_fts", "documents", "collections"} <= tables:
        return "sqlite_exact"
    if {"embedding_fulltext_search", "embedding_metadata", "embeddings"} <= tables:
        return "chroma"
    raise ValueError("Unsupported SQLite schema: not a supported MemPalace index")


def validate_query(query: Any, backend: str) -> str:
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= MAX_QUERY_CHARS:
        raise ValueError("query must have 1–160 characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in query):
        raise ValueError("control characters are not permitted")
    if any(ch in query for ch in ('"', "*", "^", ":")):
        raise ValueError("FTS query operators and quote characters are not accepted")
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not 1 <= len(tokens) <= MAX_QUERY_TOKENS:
        raise ValueError("query must contain 1–12 words/numeric tokens")
    # Chroma uses trigram FTS5. Short terms cannot be indexed. A short-token
    # query must fail clearly rather than silently returning misleading hits.
    if backend == "chroma" and any(len(t) < 3 for t in tokens):
        raise ValueError("Chroma's trigram index requires at least 3 characters per search token")
    return " AND ".join('"' + token + '"' for token in tokens)


def meta_value(row: tuple[str, Any, Any, Any, Any]) -> Any:
    _, text, integer, floating, boolean = row
    if text is not None:
        return text
    if integer is not None:
        return integer
    if floating is not None:
        return floating
    return bool(boolean) if boolean is not None else None


def permitted(wing: Any, allowed_wings: frozenset[str], requested: str | None) -> bool:
    return ("*" in allowed_wings or wing in allowed_wings) and (requested is None or requested == wing)


def bounded_document(content: str | None) -> tuple[str, bool]:
    s = content or ""
    return s[:MAX_OUTPUT_CHARS], len(s) > MAX_OUTPUT_CHARS


def sqlite_exact_search(con: sqlite3.Connection, expression: str, wings: frozenset[str], requested: str | None, limit: int) -> list[dict[str, Any]]:
    args: list[Any] = [expression]
    wh = ""
    if requested is not None:
        wh = " AND json_extract(d.metadata_json, '$.wing') = ?"
        args.append(requested)
    elif "*" not in wings:
        wh = " AND json_extract(d.metadata_json, '$.wing') IN (" + ",".join("?" for _ in wings) + ")"
        args.extend(sorted(wings))
    args.append(limit)
    sql = """SELECT d.id,d.document,d.metadata_json FROM docs_fts
    JOIN documents d ON d.collection_id=docs_fts.collection_id AND d.id=docs_fts.doc_id
    JOIN collections c ON c.id=d.collection_id
    WHERE docs_fts MATCH ? AND c.name='mempalace_drawers'""" + wh + " LIMIT ?"
    rows = con.execute(sql, args).fetchall()
    out = []
    for docid, content, mt in rows:
        try:
            meta = json.loads(mt or "{}")
        except (TypeError, ValueError):
            meta = {}
        if not permitted(meta.get("wing"), wings, requested):
            continue
        excerpt, truncated = bounded_document(content)
        out.append({"id": docid, "wing": meta.get("wing"), "room": meta.get("room"), "source_file": meta.get("source_file"), "line_start": meta.get("line_start"), "line_end": meta.get("line_end"), "verbatim": excerpt, "truncated": truncated})
    return out


def chroma_search(con: sqlite3.Connection, expression: str, wings: frozenset[str], requested: str | None, limit: int) -> list[dict[str, Any]]:
    # Chroma's embedding_fulltext_search rowid equals embedding_metadata.id
    # for the matching 'chroma:document' row (verified on MemPalace Chroma DB).
    # Restrict wings in SQL rather than leaking unpermitted excerpts to Python.
    args: list[Any] = [expression]
    wing_filter = ""
    if requested is not None:
        wing_filter = " AND w.string_value=?"
        args.append(requested)
    elif "*" not in wings:
        wing_filter = " AND w.string_value IN (" + ",".join("?" for _ in wings) + ")"
        args.extend(sorted(wings))
    args.append(limit)
    sql = """SELECT md.id,md.string_value FROM embedding_fulltext_search
      JOIN embedding_metadata md ON md.id=embedding_fulltext_search.rowid
         AND md.key='chroma:document'
      LEFT JOIN embedding_metadata w ON w.id=md.id AND w.key='wing'
      WHERE embedding_fulltext_search MATCH ?""" + wing_filter + " LIMIT ?"
    results = []
    for docid, content in con.execute(sql, args).fetchall():
        rows = con.execute("SELECT key,string_value,int_value,float_value,bool_value FROM embedding_metadata WHERE id=?", (docid,)).fetchall()
        meta = {r[0]: meta_value(r) for r in rows}
        if not permitted(meta.get("wing"), wings, requested):
            continue
        excerpt, truncated = bounded_document(content)
        identifier = con.execute("SELECT embedding_id FROM embeddings WHERE id=?", (docid,)).fetchone()
        results.append({"id": identifier[0] if identifier else str(docid), "wing": meta.get("wing"), "room": meta.get("room"), "source_file": meta.get("source_file"), "line_start": meta.get("line_start"), "line_end": meta.get("line_end"), "verbatim": excerpt, "truncated": truncated})
    return results


def status() -> dict[str, Any]:
    cfg, err = load_config()
    if err:
        return {"state": "unconfigured", "message": err, "read_only": True}
    con = None
    try:
        con = connect_ro(cfg["db"])
        backend = detect_backend(con)
        return {"state": "ready", "backend": backend, "read_only": True, "database": cfg["db"].name, "wing_filter": sorted(cfg["wings"]), "search_type": "SQLite FTS5 lexical, not semantic vector"}
    except (OSError, sqlite3.Error, ValueError) as ex:
        return {"state": "unavailable", "message": type(ex).__name__, "read_only": True}
    finally:
        if con is not None:
            con.close()


def search(arguments: Any) -> tuple[dict[str, Any], bool]:
    if not isinstance(arguments, dict) or set(arguments) - {"query", "wing", "limit"} or "query" not in arguments:
        return {"message": "Only query, optional wing and optional limit are accepted."}, True
    cfg, err = load_config()
    if err:
        return {"message": err}, True
    wing = arguments.get("wing")
    if wing is not None and (not isinstance(wing, str) or not wing.strip() or len(wing) > 100):
        return {"message": "wing must be a nonblank string of at most 100 characters."}, True
    if wing is not None and "*" not in cfg["wings"] and wing not in cfg["wings"]:
        return {"message": "Requested wing not authorized in local config."}, True
    limit = arguments.get("limit", DEFAULT_RESULTS)
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        return {"message": "limit must be an integer between 1 and 10."}, True
    con = None
    t = time.monotonic()
    try:
        con = connect_ro(cfg["db"])
        backend = detect_backend(con)
        expression = validate_query(arguments["query"], backend)
        counter = 0
        def progress() -> int:
            nonlocal counter
            counter += 1
            return int(counter > SQL_STEPS_LIMIT or (time.monotonic() - t) > 4.0)
        con.set_progress_handler(progress, 100)
        if backend == "chroma":
            hits = chroma_search(con, expression, cfg["wings"], wing, limit)
        else:
            hits = sqlite_exact_search(con, expression, cfg["wings"], wing, limit)
        return {"backend": backend, "mode": "SQLite FTS5 read-only (not vector)", "query": arguments["query"], "hits": hits, "count": len(hits), "elapsed_ms": round((time.monotonic()-t)*1000, 2), "truncation_limit_chars": MAX_OUTPUT_CHARS}, False
    except (sqlite3.Error, ValueError, OSError, TypeError) as ex:
        return {"message": "Search failed: " + type(ex).__name__ + " – " + (str(ex)[:200] if isinstance(ex, ValueError) else "no data returned")}, True
    finally:
        if con is not None:
            con.close()


TOOL_LIST = [
    {"name": "smurf_recall_status", "title": "SMURF – MemPalace Connector Status", "description": "Check the explicitly configured local MemPalace SQLite index. No reads of unconfigured paths.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
    {"name": "smurf_recall_search", "title": "SMURF – MemPalace Connector Search", "description": "Read-only, source-grounded lexical search in the locally configured MemPalace SQLite index. Limits and wing allowlist enforced locally. Text may be sent to the host AI when this tool is called.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 160}, "wing": {"type": "string", "maxLength": 100}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "required": ["query"], "additionalProperties": False}, "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


def emit(value: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def execute(msg: Any) -> None:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "id" not in msg:
        return
    rid = msg["id"]
    method = msg.get("method")
    if method == "initialize":
        params = msg.get("params") or {}
        req = params.get("protocolVersion", PROTOCOL) if isinstance(params, dict) else PROTOCOL
        version = req if req in ("2025-06-18", "2025-03-26", "2024-11-05") else PROTOCOL
        out = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "smurf-mempalace-connector", "version": VERSION}}
    elif method == "ping":
        out = {}
    elif method == "tools/list":
        out = {"tools": TOOL_LIST}
    elif method == "tools/call":
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        name, args = params.get("name"), params.get("arguments") or {}
        if name == "smurf_recall_status":
            data, is_error = (status(), False) if not args else ({"message": "No status arguments accepted."}, True)
        elif name == "smurf_recall_search":
            data, is_error = search(args)
        else:
            emit({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Unknown tool"}})
            return
        out = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "isError": is_error}
    else:
        emit({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "Method not found"}})
        return
    emit({"jsonrpc": "2.0", "id": rid, "result": out})


def main() -> None:
    for line in sys.stdin.buffer:
        try:
            execute(json.loads(line.decode("utf-8")))
        except (ValueError, UnicodeError, TypeError, AttributeError) as ex:
            print("Invalid MCP request: " + type(ex).__name__, file=sys.stderr, flush=True)
        except Exception as ex:  # never put traceback or private data on MCP stdout
            print("MCP internal error: " + type(ex).__name__, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
