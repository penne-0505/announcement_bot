# TODO

- [ ] Rewrite `app.database` + repositories/services to use `aiosqlite`/SQLite while keeping schema + timestamp behaviors from `_docs/reference/bot/master-spec/reference.md`.
  - references: `_docs/plan/bot/channel-nickname-role-sync/plan.md`, `_docs/intent/bot/channel-nickname-role-sync/intent.md`, `_docs/plan/bot/temporary-voice-channels/plan.md`
- [ ] Update docs/guides (`_docs/guide/ops/database-setup/guide.md`, `_docs/guide/ops/railway-setup/guide.md`, `_docs/guide/bot/channel-nickname-role-sync/guide.md`, `_docs/guide/bot/temporary-voice-channels/guide.md`) plus all references to mention SQLite/aiosqlite.
- [ ] Refresh dependencies (`pyproject.toml`, `poetry.lock`, `.env.example`) and rerun `poetry run pytest tests/app/test_server_color_repository.py` to confirm CI coverage.
- [ ] Auto-create missing SQLite database file (and parent directory) on startup, and document the behavior in `_docs/guide/ops/database-setup/guide.md`.
- [ ] Migrate persistence from SQLite/aiosqlite to Supabase Postgres (async driver, schema init, query placeholders, error handling) and update deployment guides.
