"""Filesystem behavior tests; never touch the user's real skill directory."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("link_skills", Path(__file__).resolve().parents[1] / "scripts/link_skills.py")
link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link)


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.destination = self.root / "local/skills"
        for name in ("alpha", "beta", "draft"):
            folder = self.repo / "skills" / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(name)
        (self.repo / ".claude-plugin").mkdir()
        (self.repo / ".claude-plugin/plugin.json").write_text(json.dumps({"skills": ["./skills/alpha", "./skills/beta"]}))

    def tearDown(self):
        self.temp.cleanup()

    def old_skill(self):
        target = self.destination / "alpha"
        target.mkdir(parents=True)
        (target / "personal-note.md").write_text("keep this")
        return target

    def test_preview_creates_nothing_and_only_selects_registered_skills(self):
        plan = link.plan_links(self.repo, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual([p[1].name for p in plan], ["alpha", "beta"])

    def test_cli_preview_does_not_write(self):
        with patch.object(link, "ROOT", self.repo):
            self.assertEqual(0, link.main(["--dest", str(self.destination)]))
        self.assertFalse(self.destination.exists())

    def test_conflict_fails_before_creating_other_links(self):
        old = self.old_skill()
        with self.assertRaises(ValueError):
            link.plan_links(self.repo, self.destination)
        self.assertEqual("keep this", (old / "personal-note.md").read_text())
        self.assertFalse((self.destination / "beta").exists())

    def test_apply_links_and_second_run_is_unchanged(self):
        link.apply_links(link.plan_links(self.repo, self.destination))
        self.assertEqual((self.repo / "skills/alpha").resolve(), (self.destination / "alpha").resolve())
        self.assertTrue(all(action == "unchanged" for _, _, action in link.plan_links(self.repo, self.destination)))

    def test_explicit_replace_retains_original_bytes(self):
        old = self.old_skill()
        backup = link.apply_links(link.plan_links(self.repo, self.destination, replace=True))
        self.assertTrue(old.is_symlink())
        self.assertEqual("keep this", (backup / "alpha/personal-note.md").read_text())

    def test_replace_preview_keeps_conflicting_directory(self):
        old = self.old_skill()
        with patch.object(link, "ROOT", self.repo):
            self.assertEqual(0, link.main(["--dest", str(self.destination), "--replace"]))
        self.assertFalse(old.is_symlink())
        self.assertEqual([], list(self.destination.parent.glob("skills-backup-*")))

    def test_dangling_link_conflicts_and_is_backed_up_without_following(self):
        self.destination.mkdir(parents=True)
        target = self.destination / "alpha"
        target.symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            link.plan_links(self.repo, self.destination)
        backup = link.apply_links(link.plan_links(self.repo, self.destination, replace=True))
        self.assertTrue((backup / "alpha").is_symlink())
        self.assertFalse((self.root / "missing").exists())

    def test_unknown_or_duplicate_skill_names_rejected(self):
        for names in (["draft"], ["../alpha"], ["alpha", "alpha"]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                link.plan_links(self.repo, self.destination, names)

    def test_destination_inside_repo_or_symlink_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        for target in (self.repo / "local", alias):
            with self.subTest(target=target), self.assertRaises(ValueError):
                link.plan_links(self.repo, target)

    def test_race_after_preview_does_not_replace_new_file(self):
        plan = link.plan_links(self.repo, self.destination)
        old = self.old_skill()
        with self.assertRaises(ValueError):
            link.apply_links(plan)
        self.assertEqual("keep this", (old / "personal-note.md").read_text())

    def test_failed_apply_rolls_back_links_and_restores_backup(self):
        old = self.old_skill()
        original = Path.symlink_to
        def fail_second(path, *args, **kwargs):
            if path.name == "beta":
                raise OSError("simulated link failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "symlink_to", fail_second), self.assertRaises(OSError):
            link.apply_links(link.plan_links(self.repo, self.destination, replace=True))
        self.assertFalse(old.is_symlink())
        self.assertEqual("keep this", (old / "personal-note.md").read_text())
        self.assertFalse((self.destination / "beta").exists())


if __name__ == "__main__":
    unittest.main()
