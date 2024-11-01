from decimal import Decimal
from injective_functions.utils.initializers import ChainInteractor
from injective_functions.utils.helpers import get_bridge_fee
from typing import Dict, List


"""This class handles all account transfer within the account"""
class InjectiveAccounts:
    def __init__(self, private_key : str = None, network_type: str = "mainnet") -> None:
        #Initializes the network and the composer
        
        if not private_key:
            raise ValueError("No private key found in the environment!!")
        self.private_key = private_key
        self.network_type = network_type
        #we could maybe override this by a master class
        #to optimize the number of chain clients we'll spawn
        self.chain_client = ChainInteractor(network_type=self.network_type, private_key=self.private_key)

    #We're using the MsgSubaccountTransfer
    #Handle errors properly here
    async def subaccount_transfer(self, amount: str, denom: str, subaccount_idx: int, dst_subaccount_idx: int) -> Dict:
        await self.chain_client.init_client()

        source_subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        dst_subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        msg = self.chain_client.composer.msg_subaccount_transfer(
        sender=self.chain_client.address.to_acc_bech32(),
        source_subaccount_id=source_subaccount_id,
        destination_subaccount_id=dst_subaccount_id,
        amount=Decimal(amount),
        denom=denom
        )
        await self.chain_client.build_and_broadcast_tx(msg)
    

    #External subaccount transfer
    async def external_subaccount_transfer(self, amount: str, denom: str, subaccount_idx: int, dst_subaccount_id: str) -> Dict:
        await self.chain_client.init_client()
        source_subaccount_id = self.chain_client.address.get_subaccount_id(subaccount_idx)
        msg = self.chain_client.composer.msg_external_transfer(
            sender=self.chain_client.address.to_acc_bech32(),
            source_subaccount_id=source_subaccount_id,
            destination_subaccount_id=dst_subaccount_id,
            amount=Decimal(amount),
            denom=denom,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)
    

    async def send_to_eth(self, denom: str, eth_dest: str, amount: str):
        await self.chain_client.init_client()
        bridge_fee = get_bridge_fee()
        # prepare tx msg
        msg = self.chain_client.composer.MsgSendToEth(
            sender=self.chain_client.address.to_acc_bech32(),
            denom=denom,
            eth_dest=eth_dest,
            amount=Decimal(amount),
            bridge_fee=bridge_fee,
        )
        await self.chain_client.build_and_broadcast_tx(msg)
    
    async def fetch_tx(self, tx_hash: str) -> Dict:
        response = await self.chain_client.client.fetch_tx(hash=tx_hash)
        return 