# Question bank — styles and what a 5/5 looks like

Templates per topic, not scripts: vary the numbers, underliers, and framing
every session so nothing repeats verbatim. Topic names match
`scripts/build_topics.py` exactly.

## mental math & quick estimation
- "17 × 24?" chains; "what's 3.5% of 840?"; decimal/fraction conversions
  under time pressure; Fermi estimates ("ADV of SPY in dollars?").
- 5/5: fast, correct, states the shortcut used (17×24 = 17×25 − 17).

## probability & expected value
- Dice/coin games with a price to play ("roll a die, get paid the face —
  fair price? Now you can re-roll once — how much more is it worth?").
- Conditional probability, Bayes with concrete numbers, birthday-style
  counterintuitives, expected value with optionality.
- 5/5: clean EV setup, correct conditioning, prices the option of re-rolling
  as max(EV_continue, value_now).

## options pricing & greeks
- Put-call parity from given prices; "long call, spot rises 1, vol drops 2
  points — pnl sign?"; delta/gamma/vega/theta intuition; why ATM gamma peaks
  near expiry; replicate a payoff diagram from vanillas.
- 5/5: parity applied without formula fumbling; signs right with reasoning
  ("delta gain vs vega loss, net depends on moneyness/vega").

## volatility & vol surface
- Implied vs realized; skew — why equity puts trade rich; term structure in
  a stressed market; "vol is 16 — what daily move does that imply?" (16/√252
  ≈ 1%); variance swap vs ATM vol.
- 5/5: knows the √252 rule instantly, explains skew via demand + jump risk.

## market making & adverse selection
- "Make me a market on <uncertain quantity>" (population of a city, cards
  left in a deck, next month's payrolls print). Then: "I lift your offer —
  now what?" (widen/skew: the flow is informed).
- Inventory management, when to widen vs skew, winner's curse.
- 5/5: quotes a two-sided market with sensible width for their uncertainty,
  adjusts correctly after being traded through, names adverse selection.

## brainteasers & game theory
- Classic structures (25 horses/5 tracks, 100 doors, poison wine barrels),
  auction/bidding games, simple Nash reasoning, poker-style pot-odds calls.
- 5/5: structures the search space aloud rather than pattern-matching a
  memorized answer.

## market microstructure & execution
- Limit vs market order tradeoffs; what widens spreads; VWAP/TWAP/IS algos —
  when each; market impact scaling with size; "client order is 30% of ADV —
  execution plan?"
- 5/5: ties impact, urgency, and information leakage together.

## portfolio construction & optimization
- Kelly sizing with concrete edge/odds; why fractional Kelly; correlation's
  effect on combined Sharpe ("two Sharpe-1 strategies, ρ=0.2 — portfolio
  Sharpe?"); position limits vs conviction.
- 5/5: does the √((1+ρ)/2)-style math or estimates it, argues for shrinkage.

## risk management & drawdowns
- "You're down 8% in a week — walk me through your desk." VaR limits and
  their failure modes; hedging a specific exposure cheaply; when to cut vs
  add; tail risk of short-vol strategies.
- 5/5: has a pre-committed drawdown protocol, distinguishes losing money
  from being wrong.

## alpha research & signals
- "Pitch a signal you'd research this month — data, hypothesis, test,
  capacity, decay, why it survives costs and isn't crowded."
  Overfitting tells; in-sample vs out-of-sample discipline; how many
  backtests before you trust nothing.
- 5/5: hypothesis-first (not data-mined), names the economic reason the
  edge exists and who's on the other side.

## statistics & time series
- Stationarity and why it matters for backtests; autocorrelation's effect on
  annualized Sharpe; regression pitfalls (leakage, multicollinearity);
  p-hacking; "R² is 0.01 — is the model useless?"
- 5/5: connects each concept to a trading decision, not textbook recitation.

## machine learning
- Overfitting controls in low signal-to-noise markets; why tree ensembles
  beat deep nets on tabular alpha; leakage horror stories; feature
  importance instability; walk-forward validation design.
- 5/5: skeptical-practitioner tone; knows finance ML ≠ Kaggle.

## coding (python/c++)
- Verbal code design (no IDE in a phone screen): "dedupe a 10GB file of
  quotes", "data structure for a top-of-book ladder", complexity of common
  operations, generators vs lists for tick streams.
- 5/5: talks tradeoffs (memory/latency/simplicity) before naming the tool.

## macro & rates knowledge
- "Where's the 10y? What moved it this month?"; curve steepener mechanics;
  what a surprise CPI print does across assets; carry trades and their
  crash risk.
- 5/5: current numbers roughly right and a coherent causal story.

## equities & single-name knowledge
- Pitch a long and a short with catalysts; earnings-day vol behavior; how
  index rebalances move names; sector rotation logic.
- 5/5: pitch has entry, sizing, catalyst, exit, and what kills the thesis.

## fx & commodities
- Covered interest parity intuition; what drives a currency pair this year;
  contango/backwardation and roll yield; storage arb limits.
- 5/5: mechanism-level answers, not headline recitation.

## market awareness & current events
- "What's the most interesting trade in markets right now?"; "what surprised
  you this week?"; defend a view against pushback twice.
- 5/5: specific, current, sized view; updates gracefully under new info
  without folding instantly.

## track record & pnl attribution
- "Walk me through your best and worst trades — sizing, thesis, exit.";
  "how much of your pnl was market beta?"; "your Sharpe — over what period,
  what capacity?"
- 5/5: honest attribution, numbers consistent under cross-examination,
  owns the losers.

## client & franchise skills
- Role-play: "client wants out of 2M shares of an illiquid name, market's
  falling — the call is yours."; handling a client you disagree with;
  balancing franchise vs prop risk.
- 5/5: protects the client relationship and the book, communicates the
  tradeoff explicitly.

## behavioral & fit
- "Why this firm / this seat?"; conflict with a PM over risk; a time you
  were wrong with money on the line; "what would your last desk say about
  you?"
- 5/5: specific stories (STAR-shaped without sounding rehearsed), no
  blame-shifting, firm-specific motivation that survives "why not our
  competitor?"

## Pressure techniques (sprinkle 2–3 per session)

- Challenge a correct answer: "You sure? I get something different."
- Interrupt a ramble: "Give me the number first."
- Stack a constraint mid-answer: "Same question, but now you can't use vol."
- Silence after their answer — do they fill it with hedging?

Score how they handle the pressure, not just whether the content survived.
