# Enable FastF1 cache and parallelize radio clip processing

Status: ready-for-agent

No fastf1.Cache.enable_cache() anywhere, so each /analyse-text downloads the
same session twice (pace agent + timeline agent). Radio clips (~20-60/race)
are downloaded+transcribed+classified sequentially inside the handler.

Fix:
- enable FastF1 cache once at startup (dir under backend/.cache/, gitignored),
  share loaded sessions between pace/timeline agents
- thread-pool clip processing; persist transcripts keyed by recording_url

## Comments
