# bank/query_balance.py
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from pyinjective.wallet import PrivateKey
async def query_balance(network_type: str = "mainnet", private_key: str = None) -> dict:
    try:
        network = Network.testnet() if network_type == "testnet" else Network.mainnet()
        client = AsyncClient(network)
        priv_key = PrivateKey.from_hex(private_key)
        pub_key = priv_key.to_public_key()
        address = str(pub_key.to_address().to_acc_bech32())

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