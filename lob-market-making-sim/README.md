# To configure virtual environment
poetry install                   
poetry run python -m ipykernel install \
    --user --name approxlob-env \
    --display-name "Poetry (approxlob)"

# To run
poetry run python <filename>

# Structure
## engine.py
Runs the simulation and tracks information within an order book. Events will be applied one at a time. Also handles the cash and inventory of the simulated market-maker.
* `update_quotes`: calculates the new bid and ask quotes based on current market status
* `apply_event`: applies the current market event and sees if a profit is made by the agent, and if so, updates the appropriate attributes

## order_book.py
A level one order book. Quotes placed by the agent (and not read from LOBSTER data) have a special oid of -1, as specified in the constructor.
* `place_agent_quote`: creates and *applies* the event for the agent's current quote
* `cancel_agent_quote`: creates and *applies* and event to remove the agent's current quote
* `apply`: applies the given event to the order book and returns the number of events processed (if there is an attempt to modify an oid that is not currently in the book, the event is ignored)