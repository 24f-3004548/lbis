# LBIS

## Test Conditions
- Runs on pre-fed Excel data already loaded into the local database.
- No live market API calls for price are used in the current setup.
- LLM answers are obtained using the free model and api key offered by Gemini, so rate limits have been added.

## Production Note
For future production development:
- When switching to paid API, remove these constraints for complete run of algorithm and change API call code.
- The database model should store company/stock names only.
- A finance API should be used to fetch live stock prices instead of relying on pre-fed Excel data stored in the database.
