from decimal import Decimal
from injective_functions.utils.initializers import ChainInteractor
from injective_functions.utils.helpers import get_bridge_fee
from typing import Dict, List


"""This class handles all auction messages"""
#TODO: add fetch current round function on indexer helper
class InjectiveAuthz:
    def __init__(self, private_key : str = None, network_type: str = "mainnet") -> None:
        #Initializes the network and the composer
        
        if not private_key:
            raise ValueError("No private key found in the environment!!")
        self.private_key = private_key
        self.network_type = network_type
        #we could maybe override this by a master class
        #to optimize the number of chain clients we'll spawn
        self.chain_client = ChainInteractor(network_type=self.network_type, private_key=self.private_key)
    
    #TODO: make sure the messages are handled properly
    async def grant_address_auth(self, grantee_address: str, msg_type: str, duration: int) -> Dict:
        await self.chain_client.init_client()
        msg = self.chain_client.composer.MsgGrantGeneric(
        granter=self.chain_client.address.to_acc_bech32(),
        grantee=grantee_address,
        msg_type=msg_type,
        expire_in=duration,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)



    #TODO: make sure the messages are handled properly
    async def revoke_address_auth(self, grantee_address: str, msg_type: str) -> Dict:
        await self.chain_client.init_client()
        msg = self.chain_client.composer.MsgRevoke(
        granter=self.chain_client.address.to_acc_bech32(),
        grantee=grantee_address,
        msg_type=msg_type,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)


    async def fetch_grants(self, granter: str, grantee: str, msg_type: str) -> Dict:
        try:
            res = await self.chain_client.client.fetch_grants(granter=granter, 
                                                            grantee=grantee, 
                                                            msg_type_url=msg_type)
            
            return {
                "success": True,
                "result": res,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
     

        pass