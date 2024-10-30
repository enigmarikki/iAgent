# bank/query_balance.py
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from pyinjective.async_client import AsyncClient
from pyinjective.core.network import Network
from pyinjective.wallet import PrivateKey
from typing import List

mainnet_test_denoms = {"inj": 1e18, "peggy0xdAC17F958D2ee523a2206206994597C13D831ec7": 1e6}
async def query_balance(network_type: str = "mainnet", private_key: str = None) -> dict:
    try:
        
        network = Network.testnet() if network_type == "testnet" else Network.mainnet()
        client = AsyncClient(network)
        priv_key = PrivateKey.from_hex(private_key)
        pub_key = priv_key.to_public_key()
        address = str(pub_key.to_address().to_acc_bech32())

        bank_balances = await client.fetch_bank_balances(address=address)
        if not mainnet_test_denoms:
            return {
                "success": True,
                "balances": bank_balances
            }
        #print(bank_balances["balances"])
        new_dic = {}
        for token in bank_balances["balances"]:
            if token["denom"] in mainnet_test_denoms.keys():
                new_dic[token["denom"]] = str(int(token["amount"]) / mainnet_test_denoms[token["denom"]])
        print(bank_balances)
        return {
            "success": True,
            "balances": new_dic
        }

            

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }