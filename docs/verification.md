# Verification — 2026-10-19

## Actual tested environment

Linux x86_64, Python 3.14.8, Node 22.23.3, npm 12.0.1, GCC 16.2.1. Portable **Helix 25.07.1 (a05c151b)** from the official release archive. Server **openplanet-lsp 0.8.0**, installed from npm in `/tmp/helix-npm` rather than using a checkout build. Standalone **Taplo 0.10.0** from its official GitHub release. No global install, full system update, server rebuild or user Helix configuration edit was performed.

AngelScript grammar: Relrin revision `4595504ef9ae3fc7d597a14fd09d9aebc5eaf8e6`, fetched and built by the shipped builder using real Helix. ABI 15 parser and its highlight query load successfully in this release. `hx --health angelscript` reports parser/highlights/server available; `hx --health openplanet-info` reports TOML parser/highlights and configured servers available. Textobjects and indent queries are absent and deliberately not claimed.

The server auto-detected the existing real Openplanet type DB: Openplanet 1.29.14, game DB dated 2026-02-03. No fixture type database was substituted or shipped.

## Automated evidence

- [18 focused unit tests](evidence/unit-tests.txt): config preservation including comments/newlines, rerun idempotence, preview with no writes, conflicting/partial/invalid TOML, query conflict preflight, symlink refusal, Windows executable quoting, custom TOML LSP lists, narrow filetypes/root markers and complete licenses. Grammar-builder wrapper tests cover private grammar selection, failure, preserving custom libraries, auxiliary MSVC output, stripping inherited Cargo runtime overrides and repeat installs. Five wrapper tests plus the symlink test have explicit Windows skips; these are synthetic wrapper tests, not real compiler tests.
- [Real editor smoke result](evidence/live-smoke.json): six checks passed using actual Helix processes and real language servers, never a simulated editor.
- [LSP protocol transcript](evidence/lsp-protocol.json): actual parsed Helix transport messages. Temporary directory prefix replaced with `<verification-run>` for portability; payloads otherwise retained.
- [Real terminal text](evidence/angelscript-screen.txt).

The smoke checks prove:

1. Helix opens AngelScript with `languageId=angelscript` and receives an error from Openplanet LSP for `missing_counter`.
2. Editing the private copy to use `_laps += 1;` and invoking Helix `:reload` clears the diagnostic.
3. The same `info.toml` is opened with `languageId=toml` by **both** Openplanet LSP and standalone Taplo LSP.
4. Manifest formatting goes to Taplo, with no formatting request sent to Openplanet LSP.
5. An invalid `[broken` TOML table produces a real manifest parse diagnostic; restoring valid TOML clears it.
6. `settings.toml` opens through Taplo and never produces a `didOpen` to Openplanet LSP during the bounded check.

The smoke's read-only wait window is 20 seconds per positive condition and 0.5 seconds after the ordinary-TOML positive condition for the negative routing check. This is evidence for the tested scenario, not proof for all timing or workspace combinations.

## Reproduce

Install Helix, the server and LSP-capable Taplo; add them to PATH. First build the grammar and then run:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/install.py --config-dir /tmp/my-helix-check/config/helix
python3 scripts/build-grammar.py --config-dir /tmp/my-helix-check/config/helix
python3 scripts/live-smoke.py \
  --helix hx --server openplanet-lsp --taplo taplo \
  --grammar /tmp/my-helix-check/config/helix/runtime/grammars/angelscript.so \
  --output /tmp/my-helix-check/results
```

The output directory must not already exist. Adjust the library extension for your platform. The smoke is POSIX-oriented and requires `tmux`; it creates and tears down its own tmux server. The actual recorded run used explicit executable paths under `/tmp/helix-research`, `/tmp/helix-npm`, and `/tmp/helix-tools`. The complete original run is retained at `/tmp/helix-smoke-format` on the validation machine, which is ephemeral and not a required installation path.

## Real screenshot

[`assets/helix-diagnostics.png`](assets/helix-diagnostics.png) is a direct **1440 × 650** PNG capture of an Alacritty window attached to actual Helix running in a private tmux server on Xvfb `:198`. The window was resized, not redrawn or composited. ImageMagick `import -window <window-id>` captured the pixels. It shows the original [`examples/demo/src/Main.as`](../examples/demo/src/Main.as), Helix's cursor, status line and `undefined identifier `missing_counter`` diagnostic. No HTML, hand-drawn editor, overlay diagnostic or synthetic terminal rendering was used. The full Xvfb display was 1440 × 960; capture is the actual terminal window only.

Capture process: install the configuration into a private XDG directory; open the example in `hx -vvv --log ...`; navigate to the error with `]d`; attach Alacritty on the private display; resize it to 1440 × 650; capture that window. The screenshot session's log remains at `/tmp/helix-verification/helix.log`. The tmux server, terminal and Xvfb process were cleaned up after validation.

The PNG decodes successfully with Pillow. Full-frame vision review plus enlarged diagnostic/status crops passed: syntax-colored code, diagnostic and status are legible. Independent T3 Codex review passed the same committed image: all elements contained, full diagnostic visible (rightmost pixel x=1436), and status identifies one error at 5:19. No clipping repair or invented content was needed.

## Known limits and failed probes

- **Linux only** was tested live. macOS/Windows CI covers Python configuration behavior only; actual editor launch, grammar compilation, npm binary delivery and GUI behavior on those OSes are unverified. CI itself must be inspected after publication before claiming its hosted runs pass.
- Minimum Helix version is the tested stable 25.07.1. Newer Helix releases, nightly builds and older versions have not been tested.
- Completion, hover, signature help, navigation, references, rename and formatting are configured through LSP but were not interactively exercised. Semantic token rendering, code lenses, inlay hints, call hierarchy and full VS Code feature parity are not claimed.
- No Openplanet game process was started; the example was not built, staged or run in-game.
- Single plugin root was tested. Multi-plugin workspaces, marker-free single files, custom `plugin_roots`, optional `.asinc`/header globs and manual project overrides remain documented, untested configurations.
- Independent prepublication review found and fixed two grammar-builder issues. [Red tests](evidence/grammar-builder-red.txt) demonstrate inherited `CARGO_MANIFEST_DIR` and auxiliary `.lib`/`.exp` outputs; all regression tests pass after removing the override and selecting only loadable library suffixes. Windows execution itself remains unverified.
- Manifest routing has a recorded [red regression test](evidence/manifest-routing-red.txt): the initial unrestricted server list failed the new diagnostics-only expectation. The final configuration restricts Openplanet to diagnostics and the real formatting-routing check passes.
- The initial deliberate string-to-integer assignment did **not** emit a diagnostic with server 0.8.0. It was replaced by a reliably reported undefined identifier. The fixture and screenshot therefore claim only the actual supported check.
- npm `@taplo/cli` 0.9.0 was tried and explicitly exited because its build excludes LSP support. The passing run uses official standalone Taplo 0.10.0. Do not recommend that npm package for this role.
- One preliminary smoke attempt fixed the undefined name by declaring a new unused variable, so the test correctly failed its empty-diagnostics check. The final fix reuses `_laps`, and the final smoke passes.
- Local npm 12 blocked the server's postinstall validation script under its allow-scripts policy; the installed platform binary nevertheless ran successfully. No global npm policy was changed.
- The installer is designed for normal single-user configuration edits. It does not lock against concurrent writers, roll back a later disk-write failure, or resolve symlinked parent directories. Back up dotfiles before manual merges.
