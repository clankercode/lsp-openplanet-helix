# Third-party and example provenance

`runtime/queries/angelscript/highlights.scm` is copied unchanged from [Relrin/tree-sitter-angelscript](https://github.com/Relrin/tree-sitter-angelscript/blob/4595504ef9ae3fc7d597a14fd09d9aebc5eaf8e6/queries/highlights.scm), revision `4595504ef9ae3fc7d597a14fd09d9aebc5eaf8e6`. Copyright 2026 Valeryi Savich; BSD-3-Clause. The complete license is in `LICENSE-tree-sitter-angelscript` and applies to that vendored query and the grammar fetched on demand. Parser sources and binaries are not bundled in this repository.

`runtime/queries/openplanet-info/highlights.scm` is an original one-line Helix inheritance directive; it uses the TOML queries/grammar already distributed with the user's Helix installation. This repo does not redistribute those files.

`examples/demo/info.toml` and `examples/demo/src/Main.as` are original minimal examples written for this integration, based on the documented Openplanet `Main`/`RenderMenu` callbacks and `UI::MenuItem` API. They were not copied from someone else's plugin. The undefined `missing_counter` is intentionally introduced to demonstrate real diagnostics; the screenshot is not a claim that the example runs in-game unchanged. Change it to `_laps += 1;` to remove that diagnostic. `int _laps` deliberately uses the server's unused-variable suppression convention. No third-party plugin assets are included.

The project does not vendor Helix, Openplanet, openplanet-lsp, Taplo or their binaries. Those are independently installed and retain their respective licenses. Full licenses for this project's original work are `UNLICENSE` and `LICENSE-CC0`.
