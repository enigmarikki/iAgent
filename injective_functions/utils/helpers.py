from typing import Dict
import re
#TODO: validate this properly and assert type safety here
def validate_market_id(market_id: str = None) -> bool:
    str_id=str(market_id).lower()
    
    if (str_id[:2] == "0x" and len(str_id)==66)or (len(str(market_id))==64):
        return True
    else:
        return False
        
def combine_function_schemas() -> Dict:
    pass
def normalize_ticker(ticker_symbol):
    """
    Normalizes various ticker formats to match the API's ticker format.

    :param ticker_symbol: The ticker symbol to normalize (e.g., 'btcusdt', 'btc-usdt', 'btc')
    :return: The normalized ticker symbol (e.g., 'BTC/USDT PERP')
    """

    ticker_symbol = ticker_symbol.strip().upper()
    ticker_symbol = re.sub(r'[^A-Z0-9/]', '', ticker_symbol)

    # Handle special cases
    if '/' in ticker_symbol:
        base, quote = ticker_symbol.split('/', 1)
    elif '-' in ticker_symbol:
        base, quote = ticker_symbol.split('-', 1)
    elif 'USDT' in ticker_symbol:
        base = ticker_symbol.replace('USDT', '')
        quote = 'USDT'
    else:
        # Default to USDT if no quote currency is provided
        base = ticker_symbol
        quote = 'USDT'

    # Construct the normalized ticker
    normalized_ticker = f"{base}/{quote} PERP"
    return normalized_ticker

