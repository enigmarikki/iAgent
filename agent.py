
from openai import OpenAI
import os
from dotenv import load_dotenv
from quart import Quart, request, jsonify
from datetime import datetime
import argparse
from injective_functions.exchange import trader
from injective_functions.bank.bank_transfer import transfer_funds
from injective_functions.bank.query_balance import query_balance
from injective_functions.staking.stake import stake_tokens
import json
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve
import aiohttp
async def get_market_id(ticker_symbol):
    """
    Asynchronously fetches the market_id for a given ticker symbol from the Injective API.

    :param ticker_symbol: The ticker symbol to look up (e.g., 'BTCUSDT', 'btc-usdt', 'btc')
    :return: The market_id as a string if found, else None
    """
    # Normalize the ticker symbol to match the API format
    normalized_ticker = normalize_ticker(ticker_symbol)

    # API endpoint for derivative markets
    url = 'https://sentry.lcd.injective.network/injective/exchange/v1beta1/derivative/markets'

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()

                # Initialize a mapping of tickers to market IDs
                ticker_to_market_id = {}

                # Check if 'markets' key exists in the response
                if 'markets' in data:
                    for market_info in data['markets']:
                        market = market_info.get('market', {})
                        ticker = market.get('ticker', '').upper()
                        market_id = market.get('market_id')

                        # Ensure market_id does not have extra quotes
                        if isinstance(market_id, str):
                            market_id = market_id.strip("'\"")

                        if ticker and market_id:
                            ticker_to_market_id[ticker] = market_id

                    # Get the market_id for the normalized ticker
                    market_id = ticker_to_market_id.get(normalized_ticker)
                    if market_id:
                        return market_id
                    else:
                        print(f"No market ID found for ticker: {normalized_ticker}")
                else:
                    print("No market data found in the response.")
        except aiohttp.ClientError as e:
            print(f"HTTP request failed: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
    return None

def normalize_ticker(ticker_symbol):
    """
    Normalizes various ticker formats to match the API's ticker format.

    :param ticker_symbol: The ticker symbol to normalize (e.g., 'btcusdt', 'btc-usdt', 'btc')
    :return: The normalized ticker symbol (e.g., 'BTC/USDT PERP')
    """
    # Remove any non-alphanumeric characters except '/'
    import re
    ticker_symbol = ticker_symbol.strip().upper()
    ticker_symbol = re.sub(r'[^A-Z0-9/]', '', ticker_symbol)

    # Handle special cases
    if ticker_symbol == 'BTC':
        base = 'BTC'
        quote = 'USDT'  # Default quote currency
    elif '/' in ticker_symbol:
        base, quote = ticker_symbol.split('/', 1)
    elif 'USDT' in ticker_symbol:
        base = ticker_symbol.replace('USDT', '')
        quote = 'USDT'
    else:
        # Default to USDT if no quote currency is provided
        base = ticker_symbol
        quote = 'USDT'

    # Construct the normalized ticker
    normalized_ticker = f"{base}/{quote} PERP"
    return normalized_ticker

# Initialize Quart app (async version of Flask)
app = Quart(__name__)

class InjectiveChatAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API key from environment variable
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Initialize conversation histories
        self.conversations = {}
        self.function_schemas = self.load_function_schemas()

    def load_function_schemas(self):
        """Load function schemas from JSON file"""
        try:
            with open('function_schemas.json', 'r') as f:
                schemas = json.load(f)
                print(schemas)
                return schemas['functions']
        except FileNotFoundError:
            print("Warning: function_schemas.json not found")
            return []

    async def execute_function(self, function_name: str, arguments: dict, private_key) -> dict:
        """Execute the appropriate Injective function"""
        try:
            
            self.injective_trader = trader.InjectiveTrading(private_key)
            if function_name == "place_limit_order":
                arguments["market_id"] = str(await get_market_id(arguments["market_id"]))
                return await self.injective_trader.place_limit_order(**arguments)
            elif function_name == "place_market_order":
                arguments["market_id"] = await get_market_id(arguments["market_id"])
                return await self.injective_trader.place_market_order(**arguments)
            #elif function_name == "cancel_order":
            #    return await self.injective_trader.cancel_order(**arguments)
            elif function_name == "query_balance":
                return await query_balance(**arguments)
            #FIXME: unify the message parsing
            elif function_name == "transfer_funds":
                arguments["private_key"] = private_key
                return await transfer_funds(**arguments)
            elif function_name == "stake_tokens":
                arguments["private_key"] = private_key
                return await stake_tokens(**arguments)
            else:
                return {"error": f"Unknown function {function_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_response(self, message, session_id='default', private_key=None):
        """Get response from OpenAI API."""
        try:
            # Initialize conversation history for new sessions
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            # Add user message to conversation history
            self.conversations[session_id].append({
                "role": "user",
                "content": message
            })
            
            # Get response from OpenAI
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful crypto trading assistant on Injective Protocol. 
                        You can help with trading, checking balances, transfers, and staking. 
                        For general questions, provide informative and engaging responses.
                        When users want to perform actions, use the appropriate function calls."""
                    }
                ] + self.conversations[session_id],
                functions=self.function_schemas,
                function_call="auto",  # Let the model decide when to call functions
                max_tokens=2000,
                temperature=0.7
            )

            response_message = response.choices[0].message
            
            # Handle function calling
            if hasattr(response_message, 'function_call') and response_message.function_call:
                # Extract function details
                function_name = response_message.function_call.name
                function_args = json.loads(response_message.function_call.arguments)
                print(function_args)
                # Execute the function
                function_response = await self.execute_function(function_name, function_args, private_key)
                
                # Add function call and response to conversation
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": function_name,
                        "arguments": json.dumps(function_args)
                    }
                })
                
                self.conversations[session_id].append({
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_response)
                })
                
                # Get final response
                second_response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4-turbo-preview",
                    messages=self.conversations[session_id],
                    max_tokens=2000,
                    temperature=0.7
                )
                
                final_response = second_response.choices[0].message.content.strip()
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": final_response
                })
                
                return {
                    "response": final_response,
                    "function_call": {
                        "name": function_name,
                        "result": function_response
                    },
                    "session_id": session_id
                }
            
            # Handle regular response
            bot_message = response_message.content
            if bot_message:
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": bot_message
                })
                
                return {
                    "response": bot_message,
                    "function_call": None,
                    "session_id": session_id
                }
            else:
                default_response = "I'm here to help you with trading on Injective Protocol. You can ask me about trading, checking balances, making transfers, or staking. How can I assist you today?"
                self.conversations[session_id].append({
                    "role": "assistant",
                    "content": default_response
                })
                
                return {
                    "response": default_response,
                    "function_call": None,
                    "session_id": session_id
                }
                
        except Exception as e:
            error_response = f"I apologize, but I encountered an error: {str(e)}. How else can I help you?"
            return {
                "response": error_response,
                "function_call": None,
                "session_id": session_id
            }
            
    def clear_history(self, session_id='default'):
        """Clear conversation history for a specific session."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id='default'):
        """Get conversation history for a specific session."""
        return self.conversations.get(session_id, [])

# Initialize chat agent
agent = InjectiveChatAgent()

@app.route('/ping', methods=['GET'])
async def ping():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/chat', methods=['POST'])
async def chat_endpoint():
    """Main chat endpoint"""
    data = await request.get_json()
    try:
        if not data or 'message' not in data:
            return jsonify({
                "error": "No message provided",
                "response": "Please provide a message to continue our conversation.",
                "session_id": data.get('session_id', 'default'),
                "agent_id": data.get('agent_id', 'default'),
                "agent_privatekey": data.get('agent_private_key', 'default')
            }), 400
            
        session_id = data.get('session_id', 'default')
        response = await agent.get_response(data['message'], session_id)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "response": "I apologize, but I encountered an error. Please try again.",
            "session_id": data.get('session_id', 'default')
        }), 500

@app.route('/history', methods=['GET'])
async def history_endpoint():
    """Get chat history endpoint"""
    session_id = request.args.get('session_id', 'default')
    return jsonify({
        "history": agent.get_history(session_id)
    })

@app.route('/clear', methods=['POST'])
async def clear_endpoint():
    """Clear chat history endpoint"""
    session_id = request.args.get('session_id', 'default')
    agent.clear_history(session_id)
    return jsonify({"status": "success"})

def main():
    parser = argparse.ArgumentParser(description='Run the chatbot API server')
    parser.add_argument('--port', type=int, default=5000, help='Port for API server')
    parser.add_argument('--host', default="0.0.0.0", help='Host for API server')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()

    config = Config()
    config.bind = [f"{args.host}:{args.port}"]
    config.debug = args.debug

    print(f"Starting API server on {args.host}:{args.port}")
    asyncio.run(serve(app, config))

if __name__ == "__main__":
    main()