# Stats rigor: direction reporting, dof floor, honest lead-time confidence

Status: resolved

Three related issues in the causal layer (needs care — touches scientific
claims):

1. `app/agents/stats.py:92-128`: Granger/TE loops only ever test mood→pace;
   "pace leads mood" strings are dead code. Either implement the reverse
   regression or reword outputs to state only one direction was tested.
2. Non-stationary raw levels with no differencing; aggregation accepts races
   where dof = n - 3L - 1 can be 1-4 (meaningless F-test). Floor dof at >= 10.
3. `correlation.py:201` floors confidence at 0.5 regardless of p-value; min-p
   over lags 1..3 is an uncorrected multiple comparison. Report lead time only
   when p < 0.05 and consider Bonferroni across lags.

## Comments

## Comments

2026-08-25: Resolved in fix/review-followups:
1. Granger + TE now test BOTH directions and pick by corrected p-value;
   "pace leads mood" is reachable and tested.
2. dof floor (_MIN_GRANGER_DOF=5): meaningless F-tests skipped everywhere.
3. Bonferroni correction across all tested lag-direction combinations;
   _risk_lead_time reports lead only when p < 0.05; /aggregation counts
   races toward mood_leads_fraction only when significant.
4. Non-stationarity disclosed explicitly in causal reasoning rather than
   silently differencing ordinal mood ranks (a real ADF/differencing pass
   would change the metric definition - deferred deliberately).
