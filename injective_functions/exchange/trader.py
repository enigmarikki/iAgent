import asyncio
import os
import uuid
from decimal import Decimal
import json
import dotenv
from grpc import RpcError
from pyinjective.async_client import AsyncClient
from pyinjective.constant import GAS_FEE_BUFFER_AMOUNT, GAS_PRICE
from pyinjective.core.network import Network
from pyinjective.transaction import Transaction
from pyinjective.wallet import PrivateKey
from openai import OpenAI
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

class InjectiveTrading:
    def __init__(self):
        dotenv.load_dotenv()
        self.private_key = os.getenv("INJECTIVE_PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("No private key found in environment variables")
        
        self.network = Network.testnet()
        
    async def init_client(self):
        """Initialize the Injective client and required components"""
        self.client = AsyncClient(self.network)
        self.composer = await self.client.composer()
        await self.client.sync_timeout_height()

        # Initialize account
        self.priv_key = PrivateKey.from_hex(self.private_key)
        self.pub_key = self.priv_key.to_public_key()
        self.address = self.pub_key.to_address()
        await self.client.fetch_account(self.address.to_acc_bech32())
        self.subaccount_id = self.address.get_subaccount_id(index=0)

    async def build_and_broadcast_tx(self, msg):
        """Common function to build and broadcast transactions"""
        tx = (
            Transaction()
            .with_messages(msg)
            .with_sequence(self.client.get_sequence())
            .with_account_num(self.client.get_number())
            .with_chain_id(self.network.chain_id)
        )
        
        sim_sign_doc = tx.get_sign_doc(self.pub_key)
        sim_sig = self.priv_key.sign(sim_sign_doc.SerializeToString())
        sim_tx_raw_bytes = tx.get_tx_data(sim_sig, self.pub_key)

        try:
            sim_res = await self.client.simulate(sim_tx_raw_bytes)
        except RpcError as ex:
            return {"error": str(ex)}

        gas_price = GAS_PRICE
        gas_limit = int(sim_res["gasInfo"]["gasUsed"]) + GAS_FEE_BUFFER_AMOUNT
        gas_fee = "{:.18f}".format((gas_price * gas_limit) / pow(10, 18)).rstrip("0")
        
        fee = [
            self.composer.coin(
                amount=gas_price * gas_limit,
                denom=self.network.fee_denom,
            )
        ]

        tx = tx.with_gas(gas_limit).with_fee(fee).with_memo("").with_timeout_height(self.client.timeout_height)
        sign_doc = tx.get_sign_doc(self.pub_key)
        sig = self.priv_key.sign(sign_doc.SerializeToString())
        tx_raw_bytes = tx.get_tx_data(sig, self.pub_key)

        res = await self.client.broadcast_tx_sync_mode(tx_raw_bytes)
        return {
            "result": res,
            "gas_wanted": gas_limit,
            "gas_fee": f"{gas_fee} INJ"
        }

    async def place_limit_order(self, price: float, quantity: float, side: str, market_id: str):
        """Place a limit order"""
        await self.init_client()
        
        msg = self.composer.msg_create_derivative_limit_order(
            sender=self.address.to_acc_bech32(),
            fee_recipient = self.address.to_acc_bech32(),
            market_id=market_id ,
            subaccount_id=self.subaccount_id,
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            margin=self.composer.calculate_margin(
                quantity=Decimal(str(quantity)),
                price=Decimal(str(price)),
                leverage=Decimal(1),
                is_reduce_only=False
            ),
            order_type=side,
            cid=str(uuid.uuid4()),
        )
        
        return await self.build_and_broadcast_tx(msg)

    async def place_market_order(self, quantity: float, side: str, market_id: str):
        """Place a market order"""
        await self.init_client()
        
        # For market orders, we'll use the current price as an estimate
        # In a real implementation, you'd want to fetch the current market price
        estimated_price = await self.client.fetch_derivative_mid_price_and_tob(
        market_id=market_id)["midPrice"]
        
        msg = self.composer.msg_create_derivative_market_order(
            sender=self.address.to_acc_bech32(),
            fee_recipient=self.address.to_acc_bech32(),
            market_id=market_id,
            subaccount_id=self.subaccount_id,
            price=Decimal(estimated_price),
            quantity=Decimal(str(quantity)),
            margin=self.composer.calculate_margin(
                quantity=Decimal(str(quantity)),
                price=Decimal(estimated_price),
                leverage=Decimal(1),
                is_reduce_only=False
            ),
            order_type=side,
            cid=str(uuid.uuid4()),
        )
        
        return await self.build_and_broadcast_tx(msg)
