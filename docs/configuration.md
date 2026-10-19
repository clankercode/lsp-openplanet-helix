# Configuration and manual installation

The authoritative complete snippet is [`config/languages.toml`](../config/languages.toml). Read it before installing. The installer copies this snippet, replacing only explicit executable/TOML-server choices, and installs the two query files from [`runtime/queries`](../runtime/queries).

## Locations

| Platform | User language configuration |
| --- | --- |
| Linux/macOS | `$XDG_CONFIG_HOME/helix/languages.toml`, or `~/.config/helix/languages.toml` |
| Windows | `%APPDATA%\helix\languages.toml` |
| Project override | `.helix/languages.toml` under the Helix workspace root |

Use `python3 scripts/install.py --config-dir /path/to/helix` for a custom user configuration directory. `--config-dir` controls the install destination, not Helix's discovery; arrange `XDG_CONFIG_HOME`/`APPDATA` or copy into the directory reported by Helix. The grammar builder accepts the same option. Do not place the runtime directory in `.helix/runtime`: Helix searches the **user** runtime (and its other runtime paths), not a per-project runtime there.

Helix merges builtin, user and project language definitions by name. Server lists and other arrays within a language are replaced. This repo uses new language names to avoid altering `toml` and `cpp`. It does not redefine `language-server.taplo`.

## Merge without overwriting

1. Back up your current `languages.toml`.
2. Merge `[language-server.openplanet-lsp]`, `[[language]] name = "angelscript"`, `[[language]] name = "openplanet-info"` and `[[grammar]] name = "angelscript"` from the snippet. If a named definition exists already, edit that definition; do not add a duplicate.
3. Keep your existing unrelated tables, comments and `[[language]] name = "toml"` configuration. Keep `{ name = "openplanet-lsp", only-features = ["diagnostics"] }` first in `openplanet-info.language-servers`, followed by `"taplo"`, `"tombi"`, or your actual TOML server(s). The feature restriction ensures TOML formatting/completion stays with a TOML server. User-defined server names need their own `[language-server.NAME]` definition.
4. Copy `runtime/queries/angelscript/highlights.scm` and `runtime/queries/openplanet-info/highlights.scm` to the same relative paths under your Helix user configuration directory. The latter inherits Helix's existing TOML highlights.
5. Run `python3 scripts/build-grammar.py` and restart Helix. If `use-grammars` exists, preserve it: the builder uses a private selection. If instead running `hx --grammar fetch/build` manually, add `angelscript` to any `only` list or remove it from an `except` list, and be aware those commands may build every selected grammar.

The installer checks all definition/query conflicts before writing. Conflicts, invalid TOML, partial prior definitions and direct symlink destinations are refused with manual-merge guidance. It does not edit through dotfile symlinks or merge customized language tables. It is additive rather than a package manager: no automatic uninstall/update of customized files. To uninstall, remove only the definitions and query/library files that this repository installed, preserving other config.

## Optional .as include files

The default claims only `.as`, avoiding ambiguity with ordinary C/C++ `.h` files. If your plugin uses `.asinc`, edit the AngelScript definition:

```toml
file-types = ["as", "asinc"]
```

For `.h`/`.inc` includes, use narrow plugin-specific globs in a project override instead of globally taking all headers:

```toml
[[language]]
name = "angelscript"
file-types = ["as", { glob = "MyPlugin/include/*.h" }, { glob = "MyPlugin/include/*.inc" }]
```

Adjust the path to your layout; glob matches are against full file paths. These snippets replace this language's `file-types` array. The included files need to be valid AngelScript and included/scanned according to server configuration. These optional globs have not been live-tested.

## Server settings and workspace roots

No initialization options are emitted by default, so server auto-detection and project/user configuration remain effective. Helix's server `config` is LSP `initializationOptions`. Add only deliberate overrides, using snake_case:

```toml
[language-server.openplanet-lsp.config]
openplanet_dir = "/path/to/OpenplanetNext"
# Other keys must match current upstream documentation.
```

Precedence: explicit initialization options > plugin `.openplanet-lsp.toml` > parent workspace config > `~/.config/openplanet-lsp/config.toml` > auto-detection. Consult upstream before setting type DB, game, plugin root or signature options. No options are fabricated in this repo.

For a single plugin, launch `hx` from its root and `info.toml` supplies the root marker. For a multi-plugin workspace, launch from the parent and preserve each plugin's manifest; use the server's `plugin_roots` only when its normal discovery needs an explicit override. Helix also supports `workspace-lsp-roots` in project `.helix/config.toml` for users who deliberately need separate server workspace roots; it is not forced here.

## Primary references

Checked 2026-10-19 against Helix 25.07.1:

- [Language configuration, globs, multiple LSPs and grammars](https://docs.helix-editor.com/languages.html)
- [Helix 25.07.1 builtin languages](https://github.com/helix-editor/helix/blob/25.07.1/languages.toml)
- [Actual configuration merge implementation](https://github.com/helix-editor/helix/blob/25.07.1/helix-loader/src/config.rs)
- [Runtime lookup and merge behavior](https://github.com/helix-editor/helix/blob/25.07.1/helix-loader/src/lib.rs)
- [Pinned AngelScript grammar](https://github.com/Relrin/tree-sitter-angelscript/tree/4595504ef9ae3fc7d597a14fd09d9aebc5eaf8e6)

Helix has no builtin AngelScript entry in that release. We use the maintained Relrin grammar; the older dehorsley grammar itself recommends Relrin. The parser uses Tree-sitter ABI 15 and was successfully built and loaded by stable Helix 25.07.1. Highlight captures come from that exact revision. Newer Helix compatibility should be checked before updating the documented tested version.
