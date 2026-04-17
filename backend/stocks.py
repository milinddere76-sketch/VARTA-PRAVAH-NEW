def get_stocks():
    """
    Returns a string containing major Indian stock market indices for the live ticker.
    In production, this can be linked to an API like Yahoo Finance or Google Finance.
    """
    # Current sample data (representing recent trends)
    indices = [
        "NIFTY 50 💹 22,450 (+0.8%)",
        "SENSEX 🚀 74,000 (+1.1%)",
        "RELIANCE 📈 2,950",
        "HDFC BANK 📈 1,550",
        "TCS 📊 3,850"
    ]
    return " • ".join(indices)
