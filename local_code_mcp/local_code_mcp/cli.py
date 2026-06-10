from __future__ import annotations

from ._canonical import load_canonical_module

_canonical_cli = load_canonical_module("cli")

build_parser = _canonical_cli.build_parser
dispatch = _canonical_cli.dispatch
main = _canonical_cli.main

__all__ = ["build_parser", "dispatch", "main"]


if __name__ == "__main__":
    main()
