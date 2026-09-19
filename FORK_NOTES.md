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

## 上游发布工作流

继承的 `Release` 工作流使用上游包名、变更日志地址和待发布 changeset，仅在 `mattpocock/skills` 运行。本 Fork 的安全补丁合并后执行 `link-safety.yml`，不会自动生成上游版本 PR 或发布标签。若未来要维护独立版本，应先配置自己的包信息、变更记录和发布规则，再启用对应流程。
