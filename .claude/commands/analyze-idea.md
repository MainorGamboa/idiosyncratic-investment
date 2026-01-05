# Analyze New Idea Command

Expects: ticker symbol as argument (e.g., /analyze-idea SRPT)

Execute the full analysis pipeline for a new ticker:

1. Run `screen` skill with the ticker to check kill screens (fast pass/fail)
2. If kill screens pass, run `analyze` skill to create full watchlist file
3. Run `score` skill to complete 6-filter scoring and generate BUY/CONDITIONAL/PASS decision
4. Display the final score and recommendation
5. If BUY score (≥8.25), ask if user wants to proceed with `open` skill
6. If CONDITIONAL score (6.5-8.24), explain what additional confirmation is needed

Stop immediately if kill screens fail and log to trades/passed/.
