import os
import sys
import time
import threading
import readline
from datetime import datetime
import colorama
from colorama import Fore, Style
import requests
import argparse
import json

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
        sys.stdout.write(f"\r{Fore.YELLOW}Bot is thinking {animation[i]}{Style.RESET_ALL}")
        sys.stdout.flush()
        time.sleep(0.1)
        i = (i + 1) % len(animation)

def display_banner(api_url):
    """Display welcome banner."""
    clear_screen()
    print(f"{Fore.CYAN}=" * 60)
    print("Interactive AI Chatbot CLI Client for injective-chain")
    print(f"Connected to: {api_url}")
    print(f"Session ID: {session_id}")
    print("Type 'quit' to exit, 'clear' to clear history, 'help' for commands")
    print("=" * 60 + Style.RESET_ALL)

def display_help():
    """Display available commands."""
    print(f"\n{Fore.GREEN}Available Commands:{Style.RESET_ALL}")
    print("- quit: Exit the chatbot")
    print("- clear: Clear conversation history")
    print("- help: Display this help message")
    print("- history: Show conversation history")
    print("- ping: Check API connection")
    print("- debug: Toggle debug mode")
    print("- session: Show current session ID")
    print()

def format_response(response):
    """Format and clean up the response text."""
    if not response:
        return "No response"
    
    # Remove any partial markdown code blocks
    lines = response.split('\n')
    formatted_lines = []
    in_code_block = False
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        formatted_lines.append(line)
    
    # Close any unclosed code blocks
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
    # Clear any previous output
    sys.stdout.write('\r' + ' ' * 50 + '\r')
    
    # Display debug information if available
    if debug_info:
        print(f"{Fore.YELLOW}Debug: {json.dumps(debug_info, indent=2)}{Style.RESET_ALL}")
    
    # Format and display the response
    formatted_response = format_response(response_text)
    print(f"{Fore.BLUE}Bot: {formatted_response}{Style.RESET_ALL}")
    print()

def run_cli(api_url, debug=False):
    """Run the CLI interface."""
    global animation_stop
    display_banner(api_url)
    
    while True:
        try:
            # Get user input
            user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}").strip()
            
            # Handle commands
            if user_input.lower() == 'quit':
                print(f"\n{Fore.YELLOW}Goodbye! 👋{Style.RESET_ALL}")
                break
                
            elif user_input.lower() == 'clear':
                result = make_request('POST', '/clear', api_url, params={'session_id': session_id})
                if debug:
                    print(f"{Fore.YELLOW}Debug: {json.dumps(result, indent=2)}{Style.RESET_ALL}")
                display_banner(api_url)
                continue
                
            elif user_input.lower() == 'help':
                display_help()
                continue
                
            elif user_input.lower() == 'history':
                result = make_request('GET', '/history', api_url, params={'session_id': session_id})
                history = result.get('history', [])
                print(f"\n{Fore.CYAN}Conversation History:{Style.RESET_ALL}")
                for message in history:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    if message["role"] == "user":
                        print(f"{Fore.GREEN}[{timestamp}] You: {message['content']}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.BLUE}[{timestamp}] Bot: {message['content']}{Style.RESET_ALL}")
                print()
                continue
                
            elif user_input.lower() == 'ping':
                try:
                    result = make_request('GET', '/ping', api_url)
                    print(f"{Fore.GREEN}API is responsive! Status: {result.get('status', 'ok')}{Style.RESET_ALL}")
                    if debug:
                        print(f"{Fore.YELLOW}Debug: {json.dumps(result, indent=2)}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.RED}API is not responding: {str(e)}{Style.RESET_ALL}")
                continue
                
            elif user_input.lower() == 'debug':
                debug = not debug
                print(f"{Fore.YELLOW}Debug mode: {'enabled' if debug else 'disabled'}{Style.RESET_ALL}")
                continue
                
            elif user_input.lower() == 'session':
                print(f"{Fore.CYAN}Current session ID: {session_id}{Style.RESET_ALL}")
                continue
                
            elif not user_input:
                continue

            # Reset animation flag and start typing animation
            animation_stop = False
            animation_thread = threading.Thread(target=display_typing_animation)
            animation_thread.daemon = True
            animation_thread.start()

            try:
                # Send message to API and wait for complete response
                result = make_request('POST', '/chat', api_url, {
                    'message': user_input,
                    'session_id': session_id
                })
                
                # Stop animation and display response
                animation_stop = True
                time.sleep(0.2)  # Give animation time to stop
                display_response(result.get('response'), result if debug else None)
                
            except Exception as e:
                animation_stop = True
                time.sleep(0.2)
                print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
            finally:
                # Ensure animation is stopped
                animation_stop = True
                time.sleep(0.2)
                sys.stdout.write('\r' + ' ' * 50 + '\r')

        except KeyboardInterrupt:
            animation_stop = True
            print(f"\n{Fore.YELLOW}Goodbye! 👋{Style.RESET_ALL}")
            break
        except Exception as e:
            animation_stop = True
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description='Chat CLI Client')
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