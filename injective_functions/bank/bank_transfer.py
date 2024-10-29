# bank/bank_transfer.py
import asyncio
import os
from decimal import Decimal
from grpc import RpcError
import dotenv
from pyinjective.async_client import AsyncClient
from pyinjective.constant import GAS_FEE_BUFFER_AMOUNT, GAS_PRICE
from pyinjective.core.network import Network
from pyinjective.transaction import Transaction
from pyinjective.wallet import PrivateKey

async def transfer_funds(
    to_address: str,
    amount: Decimal,
    denom: str = "INJ",
    network_type: str = "mainnet",
    private_key: str = None,
) -> dict:
    try:
        # select network
        
        if not private_key:
            raise ValueError("No private key found in environment variables")
        
        network = Network.mainnet()
        
        # initialize grpc client
        client = AsyncClient(network)
        composer = await client.composer()
        await client.sync_timeout_height()

        # load account
        priv_key = PrivateKey.from_hex(private_key)
        pub_key = priv_key.to_public_key()
        address = pub_key.to_address()
        await client.fetch_account(address.to_acc_bech32())
        print(f"from address : {address.to_acc_bech32()}, to address : {str(to_address)}")
        # prepare tx msg
        msg = composer.MsgSend(
            from_address=address.to_acc_bech32(),
            to_address=str(to_address),
            amount=float(amount),
            denom=denom,
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
        gas_limit = int(sim_res["gasInfo"]["gasUsed"]) + 2 * GAS_FEE_BUFFER_AMOUNT
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