import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "helix"

    def run_install(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/install.py"),
                               "--config-dir", str(self.config), *args], capture_output=True, text=True)

    def write(self, text):
        self.config.mkdir(parents=True, exist_ok=True)
        (self.config / "languages.toml").write_bytes(text.encode())

    def test_fresh_install_and_repeat_are_identical(self):
        self.assertEqual(self.run_install().returncode, 0)
        before = {p: p.read_bytes() for p in self.config.rglob("*") if p.is_file()}
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.config.rglob("*") if p.is_file()})
        self.assertEqual(len(before), 3)

    def test_preserves_comments_newlines_and_existing_toml_servers(self):
        for ending in ("", "\n", "\r\n"):
            with self.subTest(ending=repr(ending)):
                original = '# Keep me\n[[language]]\nname="toml"\nlanguage-servers=["tombi"]' + ending
                self.write(original)
                self.assertEqual(self.run_install().returncode, 0)
                content = (self.config / "languages.toml").read_bytes()
                self.assertTrue(content.startswith(original.encode()))
                data = tomllib.loads(content.decode())
                self.assertEqual(data["language"][0]["language-servers"], ["tombi"])

    def test_dry_run_creates_nothing(self):
        result = self.run_install("--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Would write", result.stdout)
        self.assertFalse(self.config.exists())

    def test_conflicting_definitions_leave_all_files_unchanged(self):
        cases = ['[[language]]\nname="angelscript"\nfile-types=["custom"]',
                 '[[language]]\nname="openplanet-info"',
                 '[[grammar]]\nname="angelscript"\nsource={path="mine"}',
                 '[language-server.openplanet-lsp]\ncommand="mine"']
        for text in cases:
            with self.subTest(text=text):
                self.write(text)
                result = self.run_install()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.config / "languages.toml").read_text(), text)
                self.assertFalse((self.config / "runtime").exists())

    def test_partial_identical_install_refused(self):
        self.write('[language-server.openplanet-lsp]\ncommand="openplanet-lsp"\nargs=["--lsp"]')
        self.assertNotEqual(self.run_install().returncode, 0)

    def test_malformed_toml_refused(self):
        self.write('name = [')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual((self.config / "languages.toml").read_text(), 'name = [')

    def test_query_conflict_preflight_does_not_write_languages(self):
        target = self.config / "runtime/queries/angelscript/highlights.scm"
        target.parent.mkdir(parents=True)
        target.write_text("my query")
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse((self.config / "languages.toml").exists())
        self.assertEqual(target.read_text(), "my query")

    @unittest.skipIf(os.name == "nt", "Creating symlinks can require elevated Windows permissions")
    def test_symlinked_languages_refused(self):
        self.config.mkdir()
        real = Path(self.temp.name) / "dotfile"
        real.write_text("# original")
        (self.config / "languages.toml").symlink_to(real)
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(real.read_text(), "# original")

    def test_executable_path_and_toml_variants_roundtrip(self):
        commands = ['/a path/openplanet-lsp', 'C:\\Program Files\\Openplanet\\openplanet-lsp.exe', 'say"hello', 'λ']
        for command in commands:
            for servers in (None, [], ["tombi"], ["taplo", "tombi"]):
                with self.subTest(command=command, servers=servers):
                    config = tomllib.loads(installer.snippet(command, servers))
                    self.assertEqual(config["language-server"]["openplanet-lsp"]["command"], command)
                    self.assertEqual(config["language"][1]["language-servers"], [{"name": "openplanet-lsp", "only-features": ["diagnostics"]}, *(servers if servers is not None else ["taplo"])])

    def test_custom_manifest_servers_via_cli(self):
        self.assertEqual(self.run_install("--toml-server", "tombi", "--toml-server", "taplo").returncode, 0)
        data = tomllib.loads((self.config / "languages.toml").read_text())
        self.assertEqual(data["language"][1]["language-servers"], [{"name": "openplanet-lsp", "only-features": ["diagnostics"]}, "tombi", "taplo"])

    def test_empty_server_refused(self):
        self.assertNotEqual(self.run_install("--server-path", "").returncode, 0)
        self.assertFalse(self.config.exists())

    def test_config_contract(self):
        config = tomllib.loads(installer.snippet())
        server = config["language-server"]["openplanet-lsp"]
        self.assertEqual(server, {"command": "openplanet-lsp", "args": ["--lsp"]})
        script, manifest = config["language"]
        self.assertEqual(script["file-types"], ["as"])
        self.assertEqual(manifest["file-types"], [{"glob": "info.toml"}])
        self.assertEqual(manifest["grammar"], "toml")
        self.assertEqual(manifest["language-id"], "toml")
        self.assertEqual(manifest["language-servers"][0], {"name": "openplanet-lsp", "only-features": ["diagnostics"]})
        for language in (script, manifest):
            self.assertEqual(language["roots"], ["info.toml", ".openplanet-lsp.toml"])
        self.assertEqual(len(config["grammar"][0]["source"]["rev"]), 40)

    def test_complete_licenses_and_query_attribution(self):
        self.assertIn("THE SOFTWARE IS PROVIDED", (ROOT / "UNLICENSE").read_text())
        self.assertIn("Creative Commons Legal Code", (ROOT / "LICENSE-CC0").read_text())
        self.assertIn("Valeryi Savich", (ROOT / "LICENSE-tree-sitter-angelscript").read_text())
        self.assertGreater((ROOT / "LICENSE-CC0").stat().st_size, 6000)


if __name__ == "__main__":
    unittest.main()
