from decimal import Decimal
from injective_functions.utils.initializers import ChainInteractor
from typing import Dict


"""This class handles all auction messages"""
#TODO: add fetch current round function on indexer helper
class InjectiveAuction:
    def __init__(self, private_key : str = None, network_type: str = "mainnet") -> None:
        #Initializes the network and the composer
        
        if not private_key:
            raise ValueError("No private key found in the environment!!")
        self.private_key = private_key
        self.network_type = network_type
        #we could maybe override this by a master class
        #to optimize the number of chain clients we'll spawn
        self.chain_client = ChainInteractor(network_type=self.network_type, private_key=self.private_key)
    
    async def send_bid_auction(self, round: int, amount: str) -> Dict:
        await self.chain_client.init_client()
        msg = self.chain_client.composer.MsgBid(sender=self.chain_client.address.to_acc_bech32(), 
                                                round=round, 
                                                bid_amount=Decimal(amount))
        return await self.chain_client.build_and_broadcast_tx(msg)

    #Add a fetch current burn auction round
    
