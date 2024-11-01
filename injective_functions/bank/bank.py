from decimal import Decimal
from injective_functions.utils.initializers import ChainInteractor
from injective_functions.utils.indexer_requests import fetch_decimal_denoms
from typing import Dict, List

class InjectiveBank:
    def __init__(self, private_key : str = None, network_type: str = "mainnet") -> None:
        #Initializes the network and the composer
        
        if not private_key:
            raise ValueError("No private key found in the environment!!")
        self.private_key = private_key
        self.network_type = network_type
        #we could maybe override this by a master class
        #to optimize the number of chain clients we'll spawn
        self.chain_client = ChainInteractor(network_type=self.network_type, private_key=self.private_key)

    async def transfer_funds(self, amount: Decimal, denom: str = None, to_address: str = None) -> Dict:
        await self.chain_client.init_client()
        msg = self.chain_client.composer.MsgSend(
            from_address=self.chain_client.address.to_acc_bech32(),
            to_address=str(to_address),
            amount=float(amount),
            denom=denom,
        )        
        return await self.chain_client.build_and_broadcast_tx(msg)
    
    async def query_balances(self, denom_list: List[str] = None)-> Dict:
        await self.chain_client.init_client()
        denoms: Dict[str, int] = await fetch_decimal_denoms(self.network_type)
        bank_balances = await self.chain_client.client.fetch_balances(address=self.chain_client.address)["balances"]
        #hash the bank balances as a kv pair
        human_readable_balances = {token["denom"] : str(int(token["amount"])/ denoms[token["denom"]]) for token in bank_balances}
        #check if denom is an arg fron the openai func calling
        filtered_balances = dict()
        if len(denom_list) > 0:
            #filter the balances
            #TODO: replace with lambda func
            for denom in denom_list:
                if denom in human_readable_balances:
                    filtered_balances[denom] = human_readable_balances[denom]
                else:
                    filtered_balances[denom] = "The token is not on mainnet!"
            return filtered_balances
        
        else:
            return filtered_balances
    
    async def query_spendable_balances(self, denom_list: List[str] = None)-> Dict:
        denoms: Dict[str, int] = await fetch_decimal_denoms(self.network_type)
        bank_balances = await self.chain_client.client.fetch_spendable_balances(address=self.chain_client.address)["balances"]
        #hash the bank balances as a kv pair
        human_readable_balances = {token["denom"] : str(int(token["amount"])/ denoms[token["denom"]]) for token in bank_balances}
        #check if denom is an arg fron the openai func calling
        filtered_balances = dict()
        if len(denom_list) > 0:
            #filter the balances
            #TODO: replace with lambda func
            for denom in denom_list:
                if denom in human_readable_balances:
                    filtered_balances[denom] = human_readable_balances[denom]
                else:
                    filtered_balances[denom] = "The token is not on mainnet!"
            return filtered_balances
        
        else:
            return filtered_balances

    async def query_total_supply(self, denom_list: List[str] = None) -> Dict:
        #we request this over and over again because new tokens can be added
        denoms: Dict[str, int] = await fetch_decimal_denoms(self.network_type)
        total_supply = await self.chain_client.client.fetch_total_supply()["supply"]
        human_readable_supply = {token["denom"] : str(int(token["amount"])/ denoms[token["denom"]]) for token in total_supply}
        #check if denom is an arg fron the openai func calling
        filtered_supply = dict()
        if len(denom_list) > 0:
            #filter the balances
            #TODO: replace with lambda func
            for denom in denom_list:
                if denom in human_readable_supply:
                    filtered_supply[denom] = human_readable_supply[denom]
                else:
                    filtered_supply[denom] = "The token is not on mainnet!"
            return filtered_supply
        
        else:
            return filtered_supply

