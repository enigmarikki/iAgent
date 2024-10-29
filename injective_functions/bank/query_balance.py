# bank/query_balance.py
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network

async def query_balance(address: str, network_type: str = "testnet") -> dict:
    try:
        network = Network.testnet() if network_type == "testnet" else Network.mainnet()
        client = AsyncClient(network)
        
        bank_balances = await client.fetch_bank_balances(address=address)
        
        return {
            "success": True,
            "balances": bank_balances
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }