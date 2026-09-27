# X-Idol CLI helpers

`xidol.bash` searches X-Idol's public WordPress API by video code and prints the matched title, codes, and suggested filename. `-m` prints the alternate-code filename when the same record lists paired codes; `--json` returns structured output.

```bash
xidol/xidol.bash FWAY-033
xidol/xidol.bash -m REBD-200.mp4
xidol/xidol.bash --json FWAY-033
```

`xidol-copy.bash` can create a second local filename for an already-downloaded file. It preserves the source, refuses to overwrite an existing destination, and supports `--dry-run`.

```bash
xidol/xidol-copy.bash --dry-run REBD-200.mp4
xidol/xidol-copy.bash REBD-200.mp4
```

Requirements: Bash, `curl`, and `python3`. These tools perform metadata lookups only; they do not download video files.
