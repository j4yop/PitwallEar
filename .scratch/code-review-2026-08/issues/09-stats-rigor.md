# Stats rigor: direction reporting, dof floor, honest lead-time confidence

Status: ready-for-agent

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
