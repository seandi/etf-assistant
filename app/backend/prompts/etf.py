TABLES_DESCRIPTION = """
The database has only the table 'etf_msci_world' which contains a set of information on ETFs, with each row corresponding to one ETF.
"""

UNIQUE_COLUMNS = ["name", "ticker"]

TABLES_DESCRIPTION = {
    "etf_search_data": """The table contains the follwing columns:
- "isin": the ISIN of the ETF, it uniquely identifies it,
- "ticker" the ETF ticker,
- "name": the name of the ETF,
- "index": the index that the ETF replicates,
- "inception_date": the date in which the ETF was created,
- "age_in_years": the number of years since the ETF was created,
- "strategy" the investment strategy in terms of time orizon,
- "domicile_country": the country of domicile of the ETF,
- "currency": the currency of the ETF,
- "hedged": indicates if the fund is hedged or not,
- "securities_lending": indicates if the ETF lends securities to third parties or not,
- "dividends": the startegy used for handling dividends, can be either 'Distributing' or 'Accumulating',
- "ter": a number indicating the Total Expense Ratio of the ETF, that is the annual cost of the ETF as a percentage of the investment,
- "replication": the replication strategy adopted, can be 'Full replication', 'Optimized sampling' or 'Swap based Unfunded',
- "size": the amount of money invested in the fund, measured in milions of euros,
- "is_sustainable": whether or not the ETF is sustainale ,
- "number of holdings": how many holdings are in the fund (if available),
- "asset": the asset class of the ETF,
- "instrument",
- "region": the region of the ETF,
- "Borsa Italiana": indicates whether the etf is exchanged at Borsa Italiana or not, 
- "London": indicates whether the etf is exchanged at London or not, 
- "Stuttgart": indicates whether the etf is exchanged at Stuttgart or not,
- "gettex": indicates whether the etf is exchanged at gettex or not,
- "Euronext Amsterdam": indicates whether the etf is exchanged at Euronext Amsterdam or not,
- "Euronext Paris": indicates whether the etf is exchanged at Euronext Paris or not,
- "XETRA": indicates whether the etf is exchanged at XETRA or not,
- "SIX Swiss Exchange": indicates whether the etf is exchanged at SIX Swiss Exchange or not,
- "Euronext Brussels": indicates whether the etf is exchanged at Euronext Brussels or not
""",
}
