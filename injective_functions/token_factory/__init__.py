from injective_functions.utils.initializers import ChainInteractor
from injective_functions.utils.indexer_requests import fetch_decimal_denoms
from typing import Dict, List
from injective_functions.base import InjectiveBase

# TODO: Convert raw exchange message formats to human readable


class InjectiveTokenFactory(InjectiveBase):
    def __init__(self, chain_client) -> None:
        # Initializes the network and the composer
        super().__init__(chain_client)

    async def create_denom(
        self, subdenom: str, name: str, symbol: str, decimals: int
    ) -> Dict:
        try:
            self.chain_client.init_client()
            msg = self.chain_client.composer.msg_create_denom(
                sender=self.chain_client.address.to_acc_bech32(),
                subdenom=subdenom,
                name=name,
                symbol=symbol,
                decimals=decimals,
            )

            # broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "result": str(e)}

    async def mint(self, denom: str, amount: int) -> Dict:
        try:
            self.chain_client.init_client()
            amount = self.chain_client.composer.coin(amount=amount, denom=denom)
            msg = self.chain_client.composer.msg_mint(
                sender=self.chain_client.address.to_acc_bech32(),
                amount=amount,
            )

            # broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "result": str(e)}

    async def burn(self, denom: str, amount: int) -> Dict:
        try:
            self.chain_client.init_client()
            amount = self.chain_client.composer.coin(amount=amount, denom=denom)
            msg = self.chain_client.composer.msg_burn(
                sender=self.chain_client.address.to_acc_bech32(),
                amount=amount,
            )

            # broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "result": str(e)}

    async def set_denom_metadata(
        self,
        sender: str,
        description: str,
        denom: str,
        subdenom: str,
        token_decimals: int,
        name: str,
        symbol: str,
        uri: str,
        uri_hash: str,
        amount: int,
    ) -> Dict:
        try:

            msg = self.chain_client.composer.msg_set_denom_metadata(
                sender=sender,
                description=description,
                denom=denom,
                subdenom=subdenom,
                token_decimals=token_decimals,
                name=name,
                symbol=symbol,
                uri=uri,
                uri_hash=uri_hash,
            )

            # broadcast the transaction
            res = await self.chain_client.message_broadcaster.broadcast([msg])
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "result": str(e)}
