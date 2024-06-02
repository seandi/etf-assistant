ETF_DB_PATH = "data/sqlite/etf.sqlite3"
MAX_ROWS_TO_PASS = 3
N_SUGGESTIONS = 3
COLUMNS_TO_PASS = ["isin", "name"]
SEARCH_TABLES = ["etf_search_data"]
DB_DIALECT = "sqlite"
CATALOG_COLUMNS = [
    "strategy",
    "domicile_country",
    "currency",
    "dividends",
    "replication",
    "asset",
    "instrument",
    "region",
]

CATALOG_DB_PATH = "data/retriever/test_catalog"
CATALOG_DB_COLLECTION = "etf_properties"
CORRECTION_THRESHOLD = 0.85
