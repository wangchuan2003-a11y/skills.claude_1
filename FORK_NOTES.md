# Local fork notes

This repository is a reference snapshot of [mattpocock/skills](https://github.com/mattpocock/skills), based on commit `6eeb81b5fcfeeb5bd531dd47ab2f9f2bbea27461`. Upstream authorship and the existing license are unchanged. This fork does not claim to be the latest upstream release.

The local safety change makes `scripts/link-skills.sh` a Python 3.10+ backed, preview-first installer. Only skills registered in `.claude-plugin/plugin.json` are selected by default; this avoids automatically enabling personal, deprecated, or unfinished skills.

```sh
bash scripts/link-skills.sh
bash scripts/link-skills.sh --skills tdd teach --apply
```

Existing files, directories, and different or dangling links cause the preflight to stop without changes. To intentionally replace conflicts, first preview with `--replace`, then add `--apply`. Originals are renamed into a unique sibling `skills-backup-...` directory, whose path is printed; they are not deleted. Links already pointing at this checkout are left unchanged. `--dest PATH` selects another destination. If a later link fails, links created by that run are rolled back and backups are restored where possible without overwriting concurrent files.

```sh
python3 -m unittest discover -s tests -v
```

Review upstream diffs before syncing. Do not blindly synchronize and immediately enable every upstream skill; test these local protections again after a merge. Updating this checkout changes the content used by its existing symlinks.
