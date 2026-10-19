#!/usr/bin/env python3
"""Linux/macOS opt-in real Helix smoke test. Requires tmux, hx, server, and Taplo LSP.

Creates only a private temporary project/config and tmux server. Keeps evidence in
--output and always tears down its own tmux server. Never touches user config.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helix", default="hx")
    parser.add_argument("--server", default="openplanet-lsp")
    parser.add_argument("--taplo", default="taplo")
    parser.add_argument("--grammar", required=True, type=Path, help="Built angelscript.so or angelscript.dylib")
    parser.add_argument("--output", required=True, type=Path, help="New directory for evidence (must not exist)")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    project = output / "demo"
    shutil.copytree(ROOT / "examples/demo", project)
    (project / ".git").mkdir()  # Explicit Helix workspace boundary, no repository mutation.
    config = output / "config/helix"
    tools = {}
    for name, command in (("helix", args.helix), ("server", args.server), ("taplo", args.taplo)):
        executable = shutil.which(command)
        if executable is None:
            raise RuntimeError(f"Missing executable: {command}")
        # Preserve symlink basename: busybox-style/Node launchers can depend on argv[0].
        tools[name] = str(Path(executable).absolute())
    subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--config-dir", str(config),
                    "--server-path", tools["server"]], check=True)
    library = config / "runtime/grammars" / args.grammar.name
    library.parent.mkdir(parents=True)
    shutil.copy2(args.grammar, library)
    # Override just Taplo's executable in this private test config.
    with (config / "languages.toml").open("a") as stream:
        stream.write('\n[language-server.taplo]\ncommand = ' + json.dumps(tools["taplo"]) + '\nargs = ["lsp", "stdio"]\n')
    log = output / "helix.log"
    env = {**os.environ, "XDG_CONFIG_HOME": str(output / "config"),
           "XDG_CACHE_HOME": str(output / "cache")}
    socket = "openplanet-test-" + uuid.uuid4().hex[:12]

    def tmux(*arguments):
        return subprocess.run(["tmux", "-L", socket, *arguments], env=env,
                              check=True, text=True, capture_output=True).stdout

    def events():
        result = []
        for line in log.read_text().splitlines() if log.exists() else []:
            match = re.search(r'\[INFO\] (\S+) (->|<-) (\{.*\})$', line)
            if match:
                result.append((match[1], match[2], json.loads(match[3])))
        return result

    def wait_for(predicate, description):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.1)
        raise AssertionError("Timed out: " + description)

    def command(text):
        tmux("send-keys", "-t", "editor", "-l", text)
        tmux("send-keys", "-t", "editor", "Enter")

    def opened(server, name):
        return any(s == server and direction == "->" and event.get("method") == "textDocument/didOpen"
                   and event["params"]["textDocument"]["uri"].endswith("/" + name)
                   for s, direction, event in events())

    def diagnostics(name, fragment=None):
        matches = [event["params"]["diagnostics"] for server, direction, event in events()
                   if server == "openplanet-lsp" and direction == "<-"
                   and event.get("method") == "textDocument/publishDiagnostics"
                   and event["params"]["uri"].endswith("/" + name)]
        if not matches:
            return False
        return any(fragment in d["message"] for d in matches[-1]) if fragment else not matches[-1]

    evidence = {"checks": []}
    try:
        for name, executable in tools.items():
            evidence[name] = subprocess.check_output([executable, "--version"], text=True).splitlines()[0]
        cmd = shlex.join([tools["helix"], "-vv", "--log", str(log), "src/Main.as"])
        tmux("new-session", "-d", "-s", "editor", "-x", "140", "-y", "26", "-c", str(project), cmd)
        tmux("set-option", "status", "off")
        wait_for(lambda: diagnostics("Main.as", "undefined identifier `missing_counter`"), "AngelScript diagnostic")
        evidence["checks"].append("Real Helix received undefined-identifier diagnostic")
        tmux("send-keys", "-t", "editor", "-l", "]d")
        time.sleep(0.2)
        (output / "angelscript-screen.txt").write_text(tmux("capture-pane", "-p", "-t", "editor"))
        # Real editor -> server change notification; the diagnostic must clear.
        script = project / "src/Main.as"
        script.write_text(script.read_text().replace("missing_counter += 1;", "_laps += 1;"))
        command(":reload")
        wait_for(lambda: diagnostics("Main.as"), "diagnostic cleared after fixing source")
        evidence["checks"].append("Diagnostic cleared after source fix and Helix :reload")
        command(":open info.toml")
        wait_for(lambda: opened("openplanet-lsp", "info.toml") and opened("taplo", "info.toml"), "both manifest servers")
        evidence["checks"].append("Both Openplanet LSP and real Taplo LSP opened info.toml")
        manifest = project / "info.toml"
        original = manifest.read_text()
        manifest.write_text(original + '\n[broken\n')
        command(":reload")
        wait_for(lambda: any(s == "openplanet-lsp" and d == "<-" and e.get("method") == "textDocument/publishDiagnostics"
                            and e["params"]["uri"].endswith("/info.toml") and e["params"]["diagnostics"]
                            for s, d, e in events()), "manifest parse diagnostic")
        evidence["checks"].append("Openplanet LSP published invalid-manifest diagnostic")
        manifest.write_text(original)
        command(":reload")
        wait_for(lambda: diagnostics("info.toml"), "manifest diagnostic cleared")
        ordinary = project / "settings.toml"
        ordinary.write_text('title = "Ordinary TOML"\n')
        command(":open settings.toml")
        wait_for(lambda: opened("taplo", "settings.toml"), "ordinary TOML Taplo open")
        time.sleep(0.5)
        assert not opened("openplanet-lsp", "settings.toml"), "Openplanet must not claim ordinary TOML"
        evidence["checks"].append("Ordinary TOML opened by Taplo, not Openplanet LSP")
        (output / "protocol.json").write_text(json.dumps(events(), indent=2) + "\n")
        evidence["result"] = "PASS"
    finally:
        subprocess.run(["tmux", "-L", socket, "kill-server"], env=env, capture_output=True)
        (output / "result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
