from openai import OpenAI
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from datetime import datetime
import argparse
from injective_functions.exchange import trader
from injective_functions.bank.bank_transfer import transfer_funds
from injective_functions.bank.query_balance import query_balance
from injective_functions.staking.stake import stake_tokens
import json
import asyncio
# Initialize Flask app
app = Flask(__name__)

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
        
        # Initialize conversation histories (support multiple sessions)
        self.conversations = {}
        self.injective_trader = trader.InjectiveTrading()
        self.function_schemas = self.load_function_schemas()
    def load_function_schemas(self):
        """Load function schemas from JSON file"""
        try:
            with open('injective_function_schemas.json', 'r') as f:
                schemas = json.load(f)
                return schemas['functions']
        except FileNotFoundError:
            print("Warning: injective_function_schemas.json not found")
            return []

    async def execute_function(self, function_name: str, arguments: dict) -> dict:
        """Execute the appropriate Injective function"""
        try:
            if function_name == "place_limit_order":
                return await self.injective_trader.place_limit_order(**arguments)
            elif function_name == "place_market_order":
                return await self.injective_trader.place_market_order(**arguments)
            elif function_name == "cancel_order":
                return await self.injective_trader.cancel_order(**arguments)
            elif function_name == "query_balance":
                return await query_balance(**arguments)
            elif function_name == "transfer_funds":
                return await transfer_funds(**arguments)
            elif function_name == "stake_tokens":
                return await stake_tokens(**arguments)
            else:
                return {"error": f"Unknown function {function_name}"}
            
            #add endpoints for the qeury balance and stake
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_response(self, message, session_id='default'):
        """
        Get response from OpenAI API.
        """
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
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful and friendly assistant. Keep responses natural and engaging."}
                ] + self.conversations[session_id],
                max_tokens=2000,
                temperature=0.7
            )

            # Extract and store bot's response
            bot_message = response.choices[0].message.content.strip()
            if bot_message.function_call:
                function_name = bot_message.function_call.name
                function_args = json.loads(bot_message.function_call.arguments)
                
                # Execute the function
                function_response = await self.execute_function(function_name, function_args)
                
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
                second_response = self.client.chat.completions.create(
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
                
                return final_response
            
            bot_message = bot_message.content.strip()
            self.conversations[session_id].append({
                "role": "assistant",
                "content": bot_message
            })
            return bot_message
            
        except Exception as e:
            return f"Error: {str(e)}"

    def clear_history(self, session_id='default'):
        """
        Clear conversation history for a specific session.
        """
        if session_id in self.conversations:
            self.conversations[session_id].clear()

    def get_history(self, session_id='default'):
        """
        Get conversation history for a specific session.
        """
        return self.conversations.get(session_id, [])

# Initialize chat agent
agent = InjectiveChatAgent()

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })
    
#these are flask routes
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
            
        session_id = data.get('session_id', 'default')
        response = agent.get_response(data['message'], session_id)
        
        return jsonify({
            "response": response,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/history', methods=['GET'])
def history_endpoint():
    """Get chat history endpoint"""
    session_id = request.args.get('session_id', 'default')
    return jsonify({
        "history": agent.get_history(session_id)
    })

@app.route('/clear', methods=['POST'])
def clear_endpoint():
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

    print(f"Starting API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()