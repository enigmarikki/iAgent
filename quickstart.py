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
from typing import Dict, Optional
import secrets
from eth_account import Account
import yaml
from pyinjective.wallet import PrivateKey

# Initialize colorama for cross-platform colored output
colorama.init()

class AgentManager:
    """Manages multiple trading agents and their private keys"""
    
    def __init__(self, config_path: str = "agents_config.yaml"):
        self.config_path = config_path
        self.agents: Dict[str, dict] = self._load_agents()
        self.current_agent: Optional[str] = None
        
    def _load_agents(self) -> Dict[str, dict]:
        """Load agents from config file"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
        
    def _save_agents(self):
        """Save agents to config file"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.agents, f)
            
    def create_agent(self, name: str) -> dict:
        """Create a new agent with a private key"""
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already exists")
            
        # Generate new private key
        private_key = str(secrets.token_hex(32))
        account = Account.from_key(private_key)
        inj_pub_key = PrivateKey.from_hex(private_key).to_public_key().to_address().to_acc_bech32()
        agent_info = {
            "private_key": private_key,
            "address": str(inj_pub_key),
            "created_at": datetime.now().isoformat()
        }
        
        self.agents[name] = agent_info
        self._save_agents()
        return agent_info
        
    def delete_agent(self, name: str):
        """Delete an existing agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
            
        del self.agents[name]
        if self.current_agent == name:
            self.current_agent = None
        self._save_agents()
        
    def switch_agent(self, name: str):
        """Switch to a different agent"""
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")
        self.current_agent = name
        
    def get_current_agent(self) -> Optional[dict]:
        """Get current agent information"""
        if self.current_agent:
            return self.agents[self.current_agent]
        return None
        
    def list_agents(self) -> Dict[str, dict]:
        """List all available agents"""
        return self.agents

class InjectiveCLI:
    """Enhanced CLI interface with agent management"""
    
    def __init__(self, api_url: str, debug: bool = False):
        self.api_url = api_url
        self.debug = debug
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.animation_stop = False
        self.agent_manager = AgentManager()

    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_typing_animation(self):
        """Display a typing animation while waiting for response."""
        animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while not self.animation_stop:
            sys.stdout.write(f"\r{Fore.YELLOW}Processing transaction {animation[i]}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(animation)

    def format_response(self, response_text, response_type=None):
        """Format and clean up the response text based on type."""
        if not response_text:
            return "No response"
        
        try:
            # Try to parse as JSON first
            response_data = json.loads(response_text) if isinstance(response_text, str) else response_text
            
            # Determine the type of response based on content
            if isinstance(response_data, dict):
                if "balances" in response_data:
                    return self.format_balance_response(response_data)
                elif any(key in response_data for key in ["result", "gas_wanted", "gas_fee"]):
                    return self.format_transaction_response(response_data)
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

    def format_transaction_response(self, response):
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

    def format_balance_response(self, response):
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

    def display_response(self, response_text, debug_info=None):
        """Display the bot's response with proper formatting."""
        sys.stdout.write('\r' + ' ' * 50 + '\r')
        
        if debug_info:
            print(f"{Fore.YELLOW}Debug: {json.dumps(debug_info, indent=2)}{Style.RESET_ALL}")
        
        formatted_response = self.format_response(response_text)
        print(f"{Fore.BLUE}Response: {formatted_response}{Style.RESET_ALL}")
        print()
        
    def display_banner(self):
        """Display welcome banner with agent information"""
        self.clear_screen()
        print(f"{Fore.CYAN}=" * 80)
        print(Fore.BLUE + """
        ██╗███╗   ██╗     ██╗███████╗ ██████╗████████╗██╗██╗   ██╗███████╗
        ██║████╗  ██║     ██║██╔════╝██╔════╝╚══██╔══╝██║██║   ██║██╔════╝
        ██║██╔██╗ ██║     ██║█████╗  ██║        ██║   ██║██║   ██║█████╗  
        ██║██║╚██╗██║██   ██║██╔══╝  ██║        ██║   ██║╚██╗ ██╔╝██╔══╝  
        ██║██║ ╚████║╚█████╔╝███████╗╚██████╗   ██║   ██║ ╚████╔╝ ███████╗
        ╚═╝╚═╝  ╚═══╝ ╚════╝ ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
        """ + Fore.RESET)
        print(f"{Back.BLUE}{Fore.WHITE} Injective Chain Interactive Agent CLI Client {Style.RESET_ALL}")
        print(f"{Fore.CYAN}Connected to: {self.api_url}")
        print(f"Session ID: {self.session_id}")
        
        current_agent = self.agent_manager.get_current_agent()
        if current_agent:
            print(f"Current Agent: {self.agent_manager.current_agent}")
            print(f"Agent Address: {current_agent['address']}")
        else:
            print(f"{Fore.YELLOW}No agent selected please select an agent{Style.RESET_ALL}")
            
        print(f"Network: TESTNET,MAINNET")
        print("=" * 80)
        print(f"{Fore.YELLOW}Available Commands:")
        print("General: quit, clear, help, history, ping, debug, session")
        print("Agents: create_agent, delete_agent, switch_agent, list_agents")
        print("Trading: place_limit_order, place_market_order, cancel_order")
        print("Banking: check_balance, transfer")
        print("Staking: stake_tokens")
        print("=" * 80 + Style.RESET_ALL)
        
    def handle_agent_commands(self, command: str, args: str) -> bool:
        """Handle agent-related commands"""
        try:
            if command == "create_agent":
                if not args:
                    print(f"{Fore.RED}Error: Agent name required{Style.RESET_ALL}")
                    return True
                agent_info = self.agent_manager.create_agent(args)
                print(f"{Fore.GREEN}Created agent '{args}'{Style.RESET_ALL}")
                print(f"Address: {agent_info['address']}")
                return True
                
            elif command == "delete_agent":
                if not args:
                    print(f"{Fore.RED}Error: Agent name required{Style.RESET_ALL}")
                    return True
                self.agent_manager.delete_agent(args)
                print(f"{Fore.GREEN}Deleted agent '{args}'{Style.RESET_ALL}")
                return True
                
            elif command == "switch_agent":
                if not args:
                    print(f"{Fore.RED}Error: Agent name required{Style.RESET_ALL}")
                    return True
                self.agent_manager.switch_agent(args)
                print(f"{Fore.GREEN}Switched to agent '{args}'{Style.RESET_ALL}")
                return True
                
            elif command == "list_agents":
                agents = self.agent_manager.list_agents()
                if not agents:
                    print(f"{Fore.YELLOW}No agents configured{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}Available Agents:{Style.RESET_ALL}")
                    for name, info in agents.items():
                        current = "*" if name == self.agent_manager.current_agent else " "
                        print(f"{current} {name}: {info['address']}")
                return True
                
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            return True
            
        return False
        
    def make_request(self, method: str, endpoint: str, data: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        """Make API request with current agent information"""
        try:
            url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Add current agent information to request if available
            current_agent = self.agent_manager.get_current_agent()
            if current_agent and data:
                data['agent_key'] = current_agent['private_key']
                
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            else:
                response = requests.post(url, json=data, params=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
            
    def run(self):
        """Run the enhanced CLI interface"""
        self.display_banner()
        
        while True:
            try:
                user_input = input(f"{Fore.GREEN}Command: {Style.RESET_ALL}").strip()
                
                if user_input.lower() == 'quit':
                    print(f"\n{Fore.YELLOW}Exiting Injective Chain CLI... 👋{Style.RESET_ALL}")
                    break
                    
                # Handle 'clear' command
                if user_input.lower() == 'clear':
                    self.clear_screen()
                    self.display_banner()
                    continue
                    
                # Split command and arguments
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # Handle agent-specific commands
                if self.handle_agent_commands(command, args):
                    continue
                    
                # Check if agent is selected for trading commands
                if command in ['place_limit_order', 'place_market_order', 'cancel_order', 'transfer', 'stake_tokens']:
                    if not self.agent_manager.get_current_agent():
                        print(f"{Fore.RED}Error: No agent selected. Use 'switch_agent' to select an agent.{Style.RESET_ALL}")
                        continue
                
                self.animation_stop = False
                animation_thread = threading.Thread(target=self.display_typing_animation)
                animation_thread.daemon = True
                animation_thread.start()
                agent = self.agent_manager.get_current_agent()
                # Make API request to the chat endpoint
                try:
                    result = self.make_request('POST', '/chat', {
                        'message': user_input,
                        'session_id': self.session_id,
                        'agent_id': agent["address"],
                        'agent_key': agent["private_key"]
                        
                    })
                    
                    self.animation_stop = True
                    time.sleep(0.2)
                    self.display_response(result.get('response'), result if self.debug else None)
                    
                except Exception as e:
                    self.animation_stop = True
                    time.sleep(0.2)
                    print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
                    
            except KeyboardInterrupt:
                self.animation_stop = True
                print(f"\n{Fore.YELLOW}Exiting Injective Chain CLI... 👋{Style.RESET_ALL}")
                break
            except Exception as e:
                self.animation_stop = True
                print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description='Injective Chain CLI Client')
    parser.add_argument('--url', default="http://localhost:5000", help='API URL')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    try:
        cli = InjectiveCLI(args.url, args.debug)
        cli.run()
    except Exception as e:
        print(f"{Fore.RED}Failed to start CLI: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()