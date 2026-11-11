# Copilot instructions

The full project guide is in `AGENTS.md` at the repository root. Read it before suggesting or making changes, and follow it.

Essentials:
- Do not invent requirements; ask. Never use `float` for money (`Decimal` only).
- Business rules go in `servicos/` (pure Python); views stay thin.
- Check what already exists (section 2 of `AGENTS.md`) before running commands.
- User-facing text in Brazilian Portuguese; code, comments and commits in English.
- Work one file at a time and explain the reasoning; the owner is learning.