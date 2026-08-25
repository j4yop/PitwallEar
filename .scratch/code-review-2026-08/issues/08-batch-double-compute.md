# batch_runner computes every race twice

Status: resolved

`app/batch_runner.py:30-45`: run_race builds rows then discards them,
returning only counts; main() re-fetches and re-runs inference for the same
races. Double network + model cost, and passes can diverge.

Fix: return (summary, rows) from run_race and persist those rows directly.

## Comments

2026-08-25: Fixed.
