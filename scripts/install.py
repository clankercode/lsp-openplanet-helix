#!/usr/bin/env python3
"""Install additive Helix configuration; never overwrite conflicting user data."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def default_config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ["APPDATA"]) / "helix"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "helix"


def snippet(server: str = "openplanet-lsp", toml_servers: list[str] | None = None) -> str:
    text = (ROOT / "config/languages.toml").read_text()
    text = text.replace('command = "openplanet-lsp"', "command = " + json.dumps(server, ensure_ascii=False), 1)
    servers = ["taplo"] if toml_servers is None else toml_servers
    return text.replace('["openplanet-lsp", "taplo"]', json.dumps(["openplanet-lsp", *servers], ensure_ascii=False))


def plan(config_dir: Path, text: str) -> list[tuple[Path, bytes]]:
    """Preflight every destination before writing anything. Keep original TOML bytes."""
    wanted = tomllib.loads(text)
    target = config_dir / "languages.toml"
    if target.is_symlink():
        raise ValueError(f"Refusing symlink: {target}; merge manually into its actual target")
    original = target.read_bytes() if target.exists() else b""
    existing = tomllib.loads(original.decode("utf-8"))
    present = []
    for kind in ("language", "grammar"):
        for item in wanted[kind]:
            matches = [v for v in existing.get(kind, []) if v.get("name") == item["name"]]
            if matches and matches != [item]:
                raise ValueError(f"Conflicting {kind}: {item['name']}; merge manually")
            present.append(bool(matches))
    for name, item in wanted["language-server"].items():
        current = existing.get("language-server", {}).get(name)
        if current is not None and current != item:
            raise ValueError(f"Conflicting language-server: {name}; merge manually")
        present.append(current is not None)
    if any(present) and not all(present):
        raise ValueError("Partial installation found; merge manually instead of duplicating tables")
    writes = []
    if not all(present):
        separator = b"\n" if original.endswith(b"\n") else b"\n\n"
        data = original + (separator if original else b"") + text.encode()
        tomllib.loads(data.decode("utf-8"))
        writes.append((target, data))
    for source in sorted((ROOT / "runtime/queries").rglob("*.scm")):
        destination = config_dir / "runtime/queries" / source.relative_to(ROOT / "runtime/queries")
        data = source.read_bytes()
        if destination.is_symlink():
            raise ValueError(f"Refusing symlink: {destination}")
        if destination.exists():
            if destination.read_bytes() != data:
                raise ValueError(f"Conflicting query: {destination}; merge manually")
        else:
            writes.append((destination, data))
    return writes


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=default_config_dir())
    parser.add_argument("--server-path", default="openplanet-lsp", help="Executable name or absolute path (one command, not shell arguments)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--toml-server", action="append", help="Manifest TOML server name; repeat for multiple (default: taplo)")
    group.add_argument("--no-toml-server", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        servers = [] if args.no_toml_server else args.toml_server
        if args.server_path == "" or (servers and "openplanet-lsp" in servers):
            raise ValueError("Server command must be nonempty and TOML servers must not repeat openplanet-lsp")
        text = snippet(args.server_path, servers)
        writes = plan(args.config_dir, text)
        for path, data in writes:
            print(f"{'Would write' if args.dry_run else 'Writing'} {path}")
            if not args.dry_run:
                atomic_write(path, data)
        if not writes:
            print("Already installed; no changes")
        if args.dry_run:
            print("\n" + text)
        else:
            print("Build the AngelScript grammar with scripts/build-grammar.py; then restart Helix.")
        return 0
    except (ValueError, OSError) as error:
        print(f"Installation refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
