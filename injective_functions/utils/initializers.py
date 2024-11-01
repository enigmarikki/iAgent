from grpc import RpcError
from pyinjective.async_client import AsyncClient
from pyinjective.constant import GAS_FEE_BUFFER_AMOUNT, GAS_PRICE
from pyinjective.core.network import Network
from pyinjective.transaction import Transaction
from pyinjective.wallet import PrivateKey

class ChainInteractor:

    def __init__(self, network_type: str = "mainnet", private_key: str = None) -> None:
        self.private_key = private_key
        if not self.private_key:
            raise ValueError("No private key found in environment variables")
        
        self.network = Network.testnet() if network_type == "testnet" else Network.mainnet()

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


    async def build_and_broadcast_tx(self, msg):
        """Common function to build and broadcast transactions"""
        try:
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
            gas_limit = int(sim_res["gasInfo"]["gasUsed"]) + int(2) * GAS_FEE_BUFFER_AMOUNT
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
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }