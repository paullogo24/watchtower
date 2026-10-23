---
tags:
  - watchtower
  - index
updated: 2026-10-23
---

# WatchTower

A reference vault for the WatchTower network monitoring project.

> [!info] Open this vault
> In Obsidian's vault switcher, choose **Open folder as vault**, select
> `/home/plogodzo/WT/vault`, then open this note.

## Start here

- [[Project Overview]] — purpose, current capabilities, and stack.
- [[Architecture]] — how monitoring, storage, and alerts connect.
- [[Database]] — tables, device persistence, and design decisions.
- [[Roadmap]] — completed work and prioritized next steps.

## Everyday tasks

- [[Device Management]] — add, inspect, update, and deactivate devices.
- [[History Cleanup]] — clear scan data while preserving registrations.
- [[Configuration]] — effective settings and current limitations.
- [[Development and Testing]] — source map, tests, and Git workflow.

## Project memory

- [[Known Issues]] — findings from reviewing the implementation.
- [[2026-10-23 Project Progress]] — work completed during the initial review.
- [[2026-10-23 Device Edit Protection]] — fix for monitoring overwriting registry edits.
- [[Work Note Template]] — copy this note to record future changes.

## Current checkpoint

The CLI supports `clear-history`. Monitoring now saves only status fields and
cannot overwrite registry metadata or recreate deleted devices. Eleven regression
tests pass. Live registry refresh, address validation, continuous operation, and
the dashboard are still pending. Devices and history **still share one SQLite file**.

These notes are a snapshot of the reviewed source, not a live status dashboard.
Update the relevant notes and [[Roadmap]] when code changes.

Repository: https://github.com/paullogo24/watchtower

Local project: `/home/plogodzo/WT`. Run shell commands from that directory,
not from this vault's directory. All source paths in these notes are relative to
the project root. Example IP addresses are placeholders.
