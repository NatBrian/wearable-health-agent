# Pointing the phone at the PC's mock watch

Run 2 of the verification needs the phone to read from the mock watch instead
of the real one. The mock speaks the same HTTP protocol as the watch-box app,
so the phone cannot tell the difference.

## On the PC

Terminal 1, left running:

```bash
uv run python tools/mock_watch.py serve
```

Terminal 2, one day at a time (see `docs/RUNBOOK-SIMULATION.md` Phase 4 for
what each flag does):

```bash
uv run python tools/mock_watch.py init --cursor 2026-09-03 --window 35
uv run python tools/mock_watch.py backfill
uv run python tools/mock_watch.py day --scenario healthy
uv run python tools/mock_watch.py day --scenario illness
```

## On the phone

1. Join the wifi the PC serves (or the phone's hotspot with the PC joined to
   it). Find the PC's address on that network (`ipconfig` on Windows: the
   wireless adapter address, typically starting with 192.168).
2. Open the app, go to Settings, Data source. Set the host to that address and
   the port to the mock's port. Save, then Restart now.
3. After each simulated day, use Settings, Diagnostics, "Run ingest now" and
   then "Score nights now" to pull the new night and step any open episode.

Localhost on the phone is the phone itself: `127.0.0.1` reaches the phone, not
the PC. Always use the LAN address.
