---
tags: [watchtower, development, testing]
updated: 2026-10-23
---

# Development and Testing

## Run the regression suite

```bash
cd /home/plogodzo/WT
python -B -m unittest discover -s tests -v
```

The five tests in `tests/test_clear_history.py` cover:

1. Preserving active/inactive registrations, resetting status, and repeated cleanup.
2. Leaving the database unchanged after decline, blank input, or EOF.
3. Clearing history after interactive confirmation.
4. Honoring `--db` and leaving another database untouched.
5. Rolling back all deletions if status reset fails.

The six tests in `tests/test_device_status.py` cover:

1. Registry metadata edits surviving repeated writes from a stale monitor copy.
2. Status and counters persisting without affecting other devices.
3. Rejecting old-IP status until the device is reloaded.
4. Preserving deactivation and rejecting status writes to inactive devices.
5. Deleted registrations staying deleted across repeated saves.
6. Never inserting unregistered devices through the status writer.

All eleven tests use temporary databases and do not ping devices or send email.
They passed after the device-edit protection fix. This is not coverage of the
entire system. Python currently emits a deprecation warning for the existing
`datetime.utcnow()` model default; modernizing timestamps remains separate work.

## Useful checks

```bash
git status --short --branch
git diff --check
git diff --stat
git log -5 --oneline
```

Review exact paths before staging. This repository currently tracks the runtime
database and `config.yaml`, despite older README statements about configuration
being ignored. Changing `.gitignore` alone does not untrack existing files.
Review whether these files should remain versioned before future publication.

## Existing implementation commits

| Commit | Change |
|---|---|
| `8c88d1a` | Add clear-history CLI and its required storage helper |
| `4f718eb` | README walkthroughs, cleanup tests, cleared-history database snapshot, email comment edit |

The assistant's push attempts failed due to GitHub DNS resolution. A subsequent
local status check showed `main` matching its recorded `origin/main`; that local
check was not a new remote verification. Do not treat this note as live Git status.

This vault is a later documentation addition and is not part of those commits.

Related: [[Architecture]], [[History Cleanup]], [[2026-10-23 Project Progress]].
