#!/usr/bin/env python3
"""Build only the pinned AngelScript grammar, without changing user's grammar selection."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location("installer", Path(__file__).with_name("install.py"))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=installer.default_config_dir())
    parser.add_argument("--helix", default="hx", help="Helix executable name or path")
    args = parser.parse_args()
    # A private config gives hx exactly one grammar and leaves existing config untouched.
    with tempfile.TemporaryDirectory(prefix="openplanet-grammar-") as temporary:
        root = Path(temporary)
        config = root / "helix"
        (config / "runtime/grammars").mkdir(parents=True)
        grammar = (installer.ROOT / "config/languages.toml").read_text().split("[[grammar]]", 1)[1]
        (config / "languages.toml").write_text('use-grammars = { only = ["angelscript"] }\n[[grammar]]' + grammar)
        env = {**os.environ, "XDG_CONFIG_HOME": str(root), "APPDATA": str(root)}
        for action in ("fetch", "build"):
            subprocess.run([args.helix, "--grammar", action], env=env, cwd=root, check=True)
        products = [p for p in (config / "runtime/grammars").glob("angelscript.*") if p.is_file()]
        if len(products) != 1:
            raise RuntimeError(f"Expected one grammar library, found: {products}")
        target = args.config_dir / "runtime/grammars" / products[0].name
        if target.exists() or target.is_symlink():
            if target.is_file() and not target.is_symlink() and target.read_bytes() == products[0].read_bytes():
                print(f"Already built: {target}")
                return
            raise RuntimeError(f"Refusing to overwrite existing grammar {target}; move it aside explicitly to rebuild")
        installer.atomic_write(target, products[0].read_bytes())
        print(f"Installed {target}")


if __name__ == "__main__":
    main()
