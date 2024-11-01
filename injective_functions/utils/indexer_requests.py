import aiohttp
from typing import Dict
from injective_functions.utils.helpers import normalize_ticker
#This is expected to return a (kv) pair
async def fetch_decimal_denoms(is_mainnet: bool) -> Dict[str, int]:
    #default url
    request_url = ''
    if is_mainnet:
        request_url = "https://sentry.lcd.injective.network/injective/exchange/v1beta1/exchange/denom_decimals"
    else:
        request_url = "https://testnet.lcd.injective.network/injective/exchange/v1beta1/exchange/denom_decimals"

    #fetch request
    response_dic: Dict[str, int] = {}
    async with aiohttp.ClientSession() as session:
        async with session.get(request_url) as response:
            denom_data = await response.json()['denom_decimals']
            for denom in denom_data:
                response_dic[denom["denom"]] = denom["decimals"]
    
    return response_dic

async def get_market_id(ticker_symbol: str, network_type: str = "mainnet"):
    """
    Asynchronously fetches the market_id for a given ticker symbol from the Injective API.

    :param ticker_symbol: The ticker symbol to look up (e.g., 'BTCUSDT', 'btc-usdt', 'btc')
    :return: The market_id as a string if found, else None
    """
    # Normalize the ticker symbol to match the API format
    normalized_ticker = normalize_ticker(ticker_symbol)
    request_url = ''
    # API endpoint for derivative markets
    if network_type == "mainnet":
        request_url = 'https://sentry.lcd.injective.network/injective/exchange/v1beta1/derivative/markets'
    else:
        request_url = 'https://testnet.sentry.lcd.injective.network/injective/exchange/v1beta1/derivative/markets'
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(request_url) as response:
                data = await response.json()

                # Initialize a mapping of tickers to market IDs
                ticker_to_market_id = {}

                # Check if 'markets' key exists in the response
                if 'markets' in data:
                    for market_info in data['markets']:
                        market = market_info.get('market', {})
                        ticker = market.get('ticker', '').upper()
                        market_id = market.get('market_id')

                        # Ensure market_id does not have extra quotes
                        if isinstance(market_id, str):
                            market_id = market_id.strip("'\"")

                        if ticker and market_id:
                            ticker_to_market_id[ticker] = market_id

                    # Get the market_id for the normalized ticker
                    market_id = ticker_to_market_id.get(normalized_ticker)
                    if market_id:
                        return market_id
                    else:
                        print(f"No market ID found for ticker: {normalized_ticker}")
                else:
                    print("No market data found in the response.")
        except aiohttp.ClientError as e:
            print(f"HTTP request failed: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
    return None
