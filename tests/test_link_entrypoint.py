"""Exercise the actual shell entrypoint against disposable destinations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class EntrypointTests(unittest.TestCase):
    def test_existing_file_directory_wrong_and_dangling_links_are_preserved(self):
        name = Path(json.loads((ROOT / '.claude-plugin/plugin.json').read_text())['skills'][0]).name
        for kind in ('directory', 'file', 'wrong-link', 'dangling-link'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / 'skills'
                dest.mkdir()
                target = dest / name
                original = Path(temp) / 'original'
                original.write_bytes(b'personal bytes\x00\xff')
                if kind == 'directory':
                    target.mkdir()
                    (target / 'note').write_bytes(original.read_bytes())
                elif kind == 'file':
                    target.write_bytes(original.read_bytes())
                else:
                    target.symlink_to(original if kind == 'wrong-link' else Path(temp) / 'missing')
                before = hashlib.sha256(original.read_bytes()).hexdigest()
                result = subprocess.run(['bash', str(ROOT / 'scripts/link-skills.sh'), '--apply',
                                         '--dest', str(dest), '--skills', name], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before, hashlib.sha256(original.read_bytes()).hexdigest())
                if kind in ('directory', 'file'):
                    self.assertFalse(target.is_symlink())
                    note = target / 'note' if kind == 'directory' else target
                    self.assertEqual(original.read_bytes(), note.read_bytes())
                else:
                    self.assertEqual(os.readlink(target), str(original if kind == 'wrong-link' else Path(temp) / 'missing'))
