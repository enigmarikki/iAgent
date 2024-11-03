from decimal import Decimal
from injective_functions.base import InjectiveBase
from typing import Dict


"""This class handles all auction messages"""
#TODO: add fetch current round function on indexer helper
class InjectiveAuction(InjectiveBase):
    def __init__(self, chain_client) -> None:
        #Initializes the network and the composer
        super().__init__(chain_client)

    async def send_bid_auction(self, round: int, amount: str) -> Dict:
        await self.chain_client.init_client()
        msg = self.chain_client.composer.MsgBid(sender=self.chain_client.address.to_acc_bech32(), 
                                                round=round, 
                                                bid_amount=Decimal(amount))
        return await self.chain_client.build_and_broadcast_tx(msg)

    
