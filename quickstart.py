import os
import sys
import time
import threading
import readline
from datetime import datetime
import colorama
from colorama import Fore, Style, Back
import requests
import argparse
import json
from decimal import Decimal

# Initialize colorama for cross-platform colored output
colorama.init()

# Global configuration
DEFAULT_API_URL = "http://localhost:5000"
session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
animation_stop = False

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_typing_animation():
    """Display a typing animation while waiting for the response."""
    animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not animation_stop:
        sys.stdout.write(f"\r{Fore.YELLOW}Processing transaction {animation[i]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.1)
        i = (i + 1) % len(animation)

def display_banner(api_url):
    """Display welcome banner."""
    clear_screen()
    print(f"{Fore.CYAN}=" * 80)
    print(f"{Back.BLUE}{Fore.WHITE} Injective Protocol Interactive CLI Client {Style.RESET_ALL}")
    print(f"{Fore.CYAN}Connected to: {api_url}")
    print(f"Session ID: {session_id}")
    print(f"Network: TESTNET,MAINNET")
    print("=" * 80)
    print(f"{Fore.YELLOW}Available Commands:")
    print("General: quit, clear, help, history, ping, debug, session")
    print("Trading: place_limit_order, place_market_order, cancel_order")
    print("Banking: check_balance, transfer")
    print("Staking: stake_tokens")
    print("=" * 80 + Style.RESET_ALL)

def display_help():
    """Display available commands."""
    print(f"\n{Fore.GREEN}Available Commands:{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}General Commands:{Style.RESET_ALL}")
    print("- quit: Exit the client")
    print("- clear: Clear conversation history")
    print("- help: Display this help message")
    print("- history: Show conversation history")
    print("- ping: Check API connection")
    print("- debug: Toggle debug mode")
    print("- session: Show current session ID")
    
    print(f"\n{Fore.CYAN}Trading Commands Examples:{Style.RESET_ALL}")
    print('- "Place a limit order to sell 0.1 BTC at $50000"')
    print('- "Buy 0.5 ETH at market price"')
    print('- "Cancel order 0x123..."')
    
    print(f"\n{Fore.CYAN}Banking Commands Examples:{Style.RESET_ALL}")
    print('- "Check balance for inj1..."')
    print('- "Transfer 1 INJ to inj1..."')
    
    print(f"\n{Fore.CYAN}Staking Commands Examples:{Style.RESET_ALL}")
    print('- "Stake 100 INJ with validator injvaloper1..."')
    print()

def format_transaction_response(response):
    """Format blockchain transaction response."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except:
            return response
            
    if isinstance(response, dict):
        if "error" in response:
            return f"{Fore.RED}Transaction Error: {response['error']}{Style.RESET_ALL}"
            
        result = []
        if "result" in response:
            tx_result = response["result"]
            result.append(f"{Fore.GREEN}Transaction Successful{Style.RESET_ALL}")
            if isinstance(tx_result, dict):
                if "txhash" in tx_result:
                    result.append(f"Transaction Hash: {tx_result['txhash']}")
                if "height" in tx_result:
                    result.append(f"Block Height: {tx_result['height']}")
                
        if "gas_wanted" in response:
            result.append(f"Gas Wanted: {response['gas_wanted']}")
        if "gas_fee" in response:
            result.append(f"Gas Fee: {response['gas_fee']}")
            
        return "\n".join(result)
    
    return str(response)

def format_balance_response(response):
    """Format balance query response."""
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except:
            return response
            
    if isinstance(response, dict):
        if "error" in response:
            return f"{Fore.RED}Query Error: {response['error']}{Style.RESET_ALL}"
            
        if "balances" in response:
            result = [f"{Fore.CYAN}Account Balances:{Style.RESET_ALL}"]
            for token in response["balances"]:
                amount = Decimal(token.get("amount", 0)) / Decimal(10**18)  # Convert from wei
                denom = token.get("denom", "UNKNOWN")
                result.append(f"- {amount:.8f} {denom}")
            return "\n".join(result)
            
    return str(response)

def format_response(response_text, response_type=None):
    """Format and clean up the response text based on type."""
    if not response_text:
        return "No response"
    
    try:
        # Try to parse as JSON first
        response_data = json.loads(response_text) if isinstance(response_text, str) else response_text
        
        # Determine the type of response based on content
        if isinstance(response_data, dict):
            if "balances" in response_data:
                return format_balance_response(response_data)
            elif any(key in response_data for key in ["result", "gas_wanted", "gas_fee"]):
                return format_transaction_response(response_data)
    except:
        pass
    
    # Default formatting for regular messages
    lines = response_text.split('\n')
    formatted_lines = []
    in_code_block = False
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        formatted_lines.append(line)
    
    if in_code_block:
        formatted_lines.append('```')
    
    return '\n'.join(formatted_lines)

def make_request(method, endpoint, api_url, data=None, params=None):
    """Make HTTP request to API with error handling."""
    try:
        url = f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=30)
        else:
            response = requests.post(url, json=data, params=params, headers=headers, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")

def display_response(response_text, debug_info=None):
    """Display the bot's response with proper formatting."""
    sys.stdout.write('\r' + ' ' * 50 + '\r')
    
    if debug_info:
        print(f"{Fore.YELLOW}Debug: {json.dumps(debug_info, indent=2)}{Style.RESET_ALL}")
    
    formatted_response = format_response(response_text)
    print(f"{Fore.BLUE}Response: {formatted_response}{Style.RESET_ALL}")
    print()

def run_cli(api_url, debug=False):
    """Run the CLI interface."""
    global animation_stop
    display_banner(api_url)
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}Command: {Style.RESET_ALL}").strip()
            
            if user_input.lower() == 'quit':
                print(f"\n{Fore.YELLOW}Exiting Injective Protocol CLI... 👋{Style.RESET_ALL}")
                break
                
            # ... [rest of the command handling remains the same] ...

            animation_stop = False
            animation_thread = threading.Thread(target=display_typing_animation)
            animation_thread.daemon = True
            animation_thread.start()

            try:
                result = make_request('POST', '/chat', api_url, {
                    'message': user_input,
                    'session_id': session_id
                })
                
                animation_stop = True
                time.sleep(0.2)
                display_response(result.get('response'), result if debug else None)
                
            except Exception as e:
                animation_stop = True
                time.sleep(0.2)
                print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            finally:
                animation_stop = True
                time.sleep(0.2)
                sys.stdout.write('\r' + ' ' * 50 + '\r')

        except KeyboardInterrupt:
            animation_stop = True
            print(f"\n{Fore.YELLOW}Exiting Injective Protocol CLI... 👋{Style.RESET_ALL}")
            break
        except Exception as e:
            animation_stop = True
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description='Injective Protocol CLI Client')
    parser.add_argument('--url', default=DEFAULT_API_URL, help='API URL')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    try:
        run_cli(args.url, args.debug)
    except Exception as e:
        print(f"{Fore.RED}Failed to start CLI: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()