from decimal import Decimal
from injective_functions.base import InjectiveBase
from injective_functions.utils.helpers import VaultContractType, SpotRedemptionType
from typing import List, Dict
import json

#class SpotRedemptionType:
#    BaseQnly = "BaseOnly"
#    QuoteOnly = "QuoteOnly"
#    BaseAndQuote = "BaseAndQuote"
#    FixedBaseAndQuote = "FixedBaseAndQuote"
#    VariableBaseAndQuote = "VariableBaseAndQuote"

class MitoContracts(InjectiveBase):
    def __init__(self, chain_client):
        super().__init__(chain_client)
        self.contract_type = {
                "ManagedVault" : "crates.io:managed-vault",
                "CPMM" : "crates.io:vault-cpmm-spot",
                "ASMMSpot" : "crates.io:vault-cpmm-asmm-spot",
                "ASMMPerp" : "crates.io:vault-cpmm-asmm-perp" 
        }

    # TODO: add fetch functions to get mito launchpads
    # currently there is no python-sdk endpoints
    def _order_funds_by_denom(self, amounts: List[Tuple[float, str]]) -> str:
        """Sort and format funds by denom"""
        sorted_amounts = sorted(amounts, key=lambda x: x[1])
        return ",".join(f"{amount}{denom}" for amount, denom in sorted_amounts)
    # This section deals with all the transactions related to mito
    # Subscribe to Launchpad
    async def subscribe_to_launchpad(
        self, contract_address: str, quote_denom: str, amount: float
    ) -> Dict:
        json_data = json.dumps({"msg": {}, "action": "subscribe"})
        funds = f"{amount}{quote_denom}"
        msg = self.chain_client.composer.msg_execute_contract_compat(
            sender=self.chain_client.address.to_acc_bech32(),
            contract=contract_address,
            msg=json_data,
            funds=funds,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)

    # Claim Launchpad Subscription
    async def claim_launchpad_subscription(self, contract_address: str) -> Dict:
        json_data = json.dumps({"msg": {}, "action": "Claim"})
        msg = self.chain_client.composer.msg_execute_contract_compat(
            sender=self.chain_client.address.to_acc_bech32(),
            contract=contract_address,
            msg=json_data,
        )
        return await self.chain_client.build_and_broadcast_tx(msg)
    # Subcribe to spot
    #TODO: Add support to derivative vaults
    async def subscription_mito_spot(
        self,
        base_amount: float,
        base_denom: str,
        quote_amount: float,
        quote_denom: str,
        vault_subaccount_id: str,
        max_penalty: float,
        vault_master_address: str,
        vault_contract_type: str,
        spot_redemption_type: str,
        trader_subaccount_idx: float = 0,
    ) -> Dict:
        """
        Subscribe to Mito spot trading vault
        """
        subscription_args = (
            {"slippage": {"max_penalty": str(max_penalty)}}
            if vault_contract_type == "CPMM"
            else {}
        )

        data = {
            "vault_subaccount_id": vault_subaccount_id,
            "trader_subaccount_id": self.chain_client.address.get_subaccount_id(trader_subaccount_idx),
            "msg": {"subscribe": subscription_args},
        }

        funds_list = []
        if spot_redemption_type != "QuoteOnly" and base_amount > 0:
            funds_list.append((base_amount, base_denom))
        if spot_redemption_type != "BaseOnly" and quote_amount > 0:
            funds_list.append((quote_amount, quote_denom))

        funds = self._order_funds_by_denom(funds_list)

        msg = self.chain_client.composer.msg_privileged_execute_contract(
            sender=self.chain_client.address.to_acc_bech32(),
            contract=vault_master_address,
            msg=json.dumps(data),
            funds=funds,
        )

        return await self.chain_client.build_and_broadcast_tx(msg)
