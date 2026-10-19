import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.name == "nt", "POSIX fake executable; real Windows grammar build untested")
class GrammarBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "user/helix"
        self.config.mkdir(parents=True)
        (self.config / "languages.toml").write_text('use-grammars = { only = ["rust"] }\n')
        self.fake = self.root / "fake-hx"
        self.fake.write_text("#!" + sys.executable + "\n" + '''import os
from pathlib import Path
import sys
p = Path(os.environ["XDG_CONFIG_HOME"]) / "helix"
s = (p / "languages.toml").read_text()
assert 'only = ["angelscript"]' in s
assert "4595504ef9ae3fc7d597a14fd09d9aebc5eaf8e6" in s
if sys.argv[-1] == "build":
    (p / "runtime/grammars/angelscript.so").write_bytes(b"fake library for isolated wrapper test")
''')
        self.fake.chmod(0o755)

    def run_build(self):
        return subprocess.run([sys.executable, str(ROOT / "scripts/build-grammar.py"),
                               "--config-dir", str(self.config), "--helix", str(self.fake)],
                              capture_output=True, text=True)

    def test_isolated_build_preserves_grammar_selection_and_is_idempotent(self):
        before = (self.config / "languages.toml").read_bytes()
        self.assertEqual(self.run_build().returncode, 0)
        self.assertEqual((self.config / "languages.toml").read_bytes(), before)
        self.assertEqual(self.run_build().returncode, 0)
        self.assertEqual((self.config / "runtime/grammars/angelscript.so").read_bytes(), b"fake library for isolated wrapper test")

    def test_existing_custom_library_is_preserved(self):
        path = self.config / "runtime/grammars/angelscript.so"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"custom")
        self.assertNotEqual(self.run_build().returncode, 0)
        self.assertEqual(path.read_bytes(), b"custom")

    def test_failed_helix_does_not_install_library(self):
        self.fake.write_text("#!" + sys.executable + "\nraise SystemExit(3)\n")
        self.assertNotEqual(self.run_build().returncode, 0)
        self.assertFalse((self.config / "runtime/grammars/angelscript.so").exists())


if __name__ == "__main__":
    unittest.main()
