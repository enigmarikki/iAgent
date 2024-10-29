# staking/stake.py
import asyncio
import os
from decimal import Decimal
from grpc import RpcError
from pyinjective.async_client import AsyncClient
from pyinjective.constant import GAS_FEE_BUFFER_AMOUNT, GAS_PRICE
from pyinjective.core.network import Network
from pyinjective.transaction import Transaction
from pyinjective.wallet import PrivateKey

async def stake_tokens(
    private_key: str,
    validator_address: str,
    amount: Decimal,
    network_type: str = "testnet"
) -> dict:
    try:
        # select network
        network = Network.testnet() if network_type == "testnet" else Network.mainnet()

        # initialize grpc client
        client = AsyncClient(network)
        composer = await client.composer()
        await client.sync_timeout_height()

        # load account
        priv_key = PrivateKey.from_hex(private_key)
        pub_key = priv_key.to_public_key()
        address = pub_key.to_address()
        await client.fetch_account(address.to_acc_bech32())

        # prepare tx msg
        msg = composer.MsgDelegate(
            delegator_address=address.to_acc_bech32(),
            validator_address=validator_address,
            amount=float(amount)
        )

        # build sim tx
        tx = (
            Transaction()
            .with_messages(msg)
            .with_sequence(client.get_sequence())
            .with_account_num(client.get_number())
            .with_chain_id(network.chain_id)
        )
        
        sim_sign_doc = tx.get_sign_doc(pub_key)
        sim_sig = priv_key.sign(sim_sign_doc.SerializeToString())
        sim_tx_raw_bytes = tx.get_tx_data(sim_sig, pub_key)

        # simulate tx
        sim_res = await client.simulate(sim_tx_raw_bytes)

        # build tx
        gas_price = GAS_PRICE
        gas_limit = int(sim_res["gasInfo"]["gasUsed"]) + GAS_FEE_BUFFER_AMOUNT
        gas_fee = "{:.18f}".format((gas_price * gas_limit) / pow(10, 18)).rstrip("0")
        fee = [
            composer.coin(
                amount=gas_price * gas_limit,
                denom=network.fee_denom,
            )
        ]
        
        tx = tx.with_gas(gas_limit).with_fee(fee).with_memo("").with_timeout_height(client.timeout_height)
        sign_doc = tx.get_sign_doc(pub_key)
        sig = priv_key.sign(sign_doc.SerializeToString())
        tx_raw_bytes = tx.get_tx_data(sig, pub_key)

        # broadcast tx
        res = await client.broadcast_tx_sync_mode(tx_raw_bytes)
        
        return {
            "success": True,
            "result": res,
            "gas_wanted": gas_limit,
            "gas_fee": f"{gas_fee} INJ"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }