# API hardening: destructive GET, CORS wildcard, explainability mislabel

Status: ready-for-agent

- `app/main.py:236`: GET /aggregation/clear wipes the pooled store; combined
  with CORS `allow_origins=["*"]` any webpage can erase it. Make it POST/DELETE
  and restrict CORS to the Vite dev origin(s).
- `app/main.py:163-186`: /analyse-text stuffs its single text mood into the
  audio slot; explainability reports audio_mood=<text mood>, text_mood=null,
  and the computed agreement is discarded. Pass text/audio moods separately.
- Legacy fallback fills `correlation` with a rescaled pace delta though the
  schema calls it Pearson r (`correlation.py:57-68`) — return None instead.

## Comments
