from __future__ import annotations

from typing import Any

from ._canonical import load_canonical_module

_canonical_server = load_canonical_module("server")

create_mcp_server = _canonical_server.create_mcp_server
main = _canonical_server.main

__all__ = ["create_mcp_server", "main"]


if __name__ == "__main__":
    main()
