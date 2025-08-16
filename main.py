import click
import os
import logging
import sys
import datetime
import time
import threading
import configparser
import shutil
import textwrap
import platform
import ctypes
import re
from colorama import init, Fore, Style
from agent import run_agent, load_llm
from verify_installation import verify_installation

init(autoreset=True)

# Global LLM instance for interactive mode
llm_instance = None

class ProgressTracker:
    def __init__(self):
        self.stages = [
            ("initializing", "Initializing system", 0.1),
            ("loading_llm", "Loading language model", 0.2),
            ("planning", "Analyzing query", 0.3),
            ("searching", "Searching web sources", 0.6),
            ("processing", "Processing results", 0.8),
            ("generating", "Generating report", 1.0)
        ]
        self.current_stage_idx = 0
        self.start_time = time.time()
        self.is_running = False
        self.thread = None
        self.console_lock = threading.Lock()
        self.report_buffer = ""

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._display_loop)
        self.thread.start()

    def update_stage(self, message):
        message_lower = message.lower()
        for idx, (key, _, _) in enumerate(self.stages):
            if key in message_lower:
                self.current_stage_idx = max(self.current_stage_idx, idx)

    def print(self, text):
        with self.console_lock:
            self.report_buffer += text

    def _display_loop(self):
        columns = shutil.get_terminal_size().columns
        is_generating = False
        while self.is_running:
            with self.console_lock:
                # Check if we've switched to the generating stage
                if not is_generating and self.stages[self.current_stage_idx][0] == "generating":
                    is_generating = True
                    # Clear the progress bar line and print the report header
                    print("\r" + " " * columns, end='\r', flush=True)
                    header = " RESEARCH REPORT "
                    print("\n" + Fore.CYAN + header.center(columns, "="))
                
                if is_generating:
                    # In the generating stage, just print the buffered content as is
                    if self.report_buffer:
                        print(self.report_buffer, end="", flush=True)
                        self.report_buffer = ""
                else:
                    # For all other stages, display the progress bar
                    elapsed = time.time() - self.start_time
                    _, display_text, progress = self.stages[self.current_stage_idx]
                    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'][int(elapsed * 10) % 10]
                    bar_length = 20
                    filled = int(bar_length * progress)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    status_line = f"\r{spinner} [{bar}] {display_text} ({elapsed:.1f}s)"
                    print(status_line, end='', flush=True)
            time.sleep(0.05)

    def complete(self):
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join()
        
        columns = shutil.get_terminal_size().columns
        print("\r" + " " * columns, end='\r', flush=True)



def load_config():
    """Load configuration from config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    # Set defaults
    config['llm'] = {
        'model_path': 'models/janhq_Jan-v1-4B-Q4_K_M.gguf'
    }
    config['agent'] = {
        'max_iterations': '3',
        'temperature': '0.6'
    }
    config['search'] = {
        'max_results': '5'
    }
    
    # Read config file if it exists
    if os.path.exists(config_path):
        config.read(config_path)
    
    return config

@click.command()
@click.argument('query', required=False)
@click.option('--temperature', type=float, help='Temperature for LLM generation.')
@click.option('--output', default=None, help='Output file for the report.')
@click.option('--max-iterations', type=int, help='Maximum number of search iterations.')
@click.option('--offline', is_flag=True, help='Run in offline mode (for calculator).')
@click.option('--no-typing', is_flag=True, help='Disable the typing effect.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging for debugging.')
def main(query, temperature, output, max_iterations, offline, no_typing, verbose):
    # Load configuration
    config = load_config()
    
    # Use CLI options if provided, otherwise use config values
    model_path = os.getenv('JANDIVE_MODEL_PATH', config.get('llm', 'model_path'))
    temperature = temperature if temperature is not None else config.getfloat('agent', 'temperature')
    max_iterations = max_iterations if max_iterations is not None else config.getint('agent', 'max_iterations')
    
    # Centralized logging setup
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stderr)
    logging.getLogger('tools.search_tool').setLevel(logging.ERROR) # Suppress warnings

    # Ensure proper UTF-8 encoding for Windows
    if os.name == 'nt':  # Windows
        import ctypes # ctypes is only used here, so it's fine to keep it local
        if sys.stdout.encoding != 'utf-8': # sys is already imported globally
            try:
                # Set Windows console to UTF-8
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleOutputCP(65001)
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception as e:
                logging.warning(f"Could not set UTF-8 encoding: {e}")

    print(Fore.CYAN + "\n=== JanDive CLI v1.0 ===")
    if not query:
        print(Fore.GREEN + "Starting interactive mode...")

    if os.path.exists(model_path):
        print(Fore.GREEN + f"[OK] Model found: {model_path}")
    else:
        print(Fore.RED + "[ERROR] Model not found. Run 'python download_model.py'")

    # Temporarily suppress warnings from search_tool during verification
    search_tool_logger = logging.getLogger('tools.search_tool')
    original_search_tool_level = search_tool_logger.level
    search_tool_logger.setLevel(logging.ERROR)

    if verify_installation(verbose=False): # This now prints a concise "OK"
        print(Fore.GREEN + "[OK] Tools ready: Search, Calculator")
    else:
        print(Fore.RED + "[ERROR] Tools verification failed. Run 'python verify_installation.py --verbose' for details.")
    
    # Restore original logging level
    search_tool_logger.setLevel(original_search_tool_level)

    # On first launch
    if not os.path.exists(".jan_dive_initialized"):
        print(Fore.CYAN + "\n=== WELCOME TO JANDIVE ===")
        print(Fore.GREEN + "This interactive tutorial will help you get started:")
        print(Fore.GREEN + "1. Type a question to begin research")
        print(Fore.GREEN + "2. Use 'history' to review past queries")
        print(Fore.GREEN + "3. Add '--concise' for shorter reports")
        print(Fore.GREEN + "4. Type 'help' at any time for assistance")
        input(Fore.YELLOW + "\nPress Enter to start...")
        with open(".jan_dive_initialized", "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

    if not query:
        print(Fore.YELLOW + "\nInstructions:")
        print("- Enter query (or 'exit' to quit).")
        print("- Reports are auto-saved to timestamped .md files.")
        print("- Use --verbose flag for detailed process logs.")
        print("- Configuration can be modified in config.ini")
        print(Fore.CYAN + "====================================================\n")

    if query:
        process_query(query, temperature, output, max_iterations, offline, no_typing, verbose)
    else:
        # Interactive mode with state
        global llm_instance
        conversation_history = []
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Pre-load the LLM for interactive mode
        if llm_instance is None:
            print(Fore.YELLOW + "Loading LLM for interactive session (this may take a moment)...")
            try:
                llm_instance = load_llm(model_path, config)
                print(Fore.GREEN + "[OK] LLM loaded successfully.")
            except Exception as e:
                print(Fore.RED + f"[ERROR] Failed to load LLM: {e}")
                return

        while True:
            try:
                print(f"\nSession {session_id} | {len(conversation_history)+1} queries")
                user_input = input(Fore.WHITE + "Query: ").strip()

                if user_input.lower() in ['exit', 'quit']:
                    print(Fore.CYAN + "Exiting JanDive...")
                    break

                if user_input.lower() == "history":
                    print("\nPrevious queries:")
                    for i, (q, a) in enumerate(conversation_history, 1):
                        print(f"{i}. {q[:50]}{'...' if len(q) > 50 else ''}")
                    continue

                if user_input.lower() == "save session":
                    filename = f"session_{session_id}.md"
                    with open(filename, 'w') as f:
                        for i, (q, a) in enumerate(conversation_history, 1):
                            f.write(f"## Query {i}: {q}\n\n")
                            f.write(f"{a}\n\n---\n\n")
                    print(f"Session saved to {filename}")
                    continue

                if user_input.lower() in ["help", "?"]:
                    print("\n" + Fore.CYAN + "=== JanDive Help ===")
                    print(Fore.GREEN + "Commands:")
                    print("  [your question]  - Ask a research question")
                    print("  history          - View previous queries")
                    print("  save session     - Save conversation to file")
                    print("  config           - Change settings")
                    print("  exit/quit        - Exit the application")
                    print("\n" + Fore.YELLOW + "Tips:")
                    print("  Add '--concise' for brief answers")
                    print("  Use '--verbose' for detailed logs")
                    continue

                if user_input.lower() == "config":
                    print("\nCurrent configuration:")
                    print(f"1. Temperature: {temperature} (current: {config.getfloat('agent', 'temperature')})")
                    print(f"2. Max iterations: {max_iterations} (current: {config.getint('agent', 'max_iterations')})")
                    print(f"3. Output format: Markdown") # This is a placeholder, as output format is not configurable yet
                    
                    setting = input("Select setting to change (1-3): ").strip()
                    if setting == "1":
                        new_temp = input(f"New temperature (0.0-1.0) [current: {temperature}]: ").strip()
                        try:
                            temperature = float(new_temp)
                            print(f"Temperature set to {temperature}")
                        except ValueError:
                            print("Invalid value, using default")
                    elif setting == "2":
                        new_max_iter = input(f"New max iterations (integer) [current: {max_iterations}]: ").strip()
                        try:
                            max_iterations = int(new_max_iter)
                            print(f"Max iterations set to {max_iterations}")
                        except ValueError:
                            print("Invalid value, using default")
                    else:
                        print("Invalid setting number.")
                    continue # Continue the loop after config

                if user_input.strip():
                    report_content = process_query(user_input, temperature, output, max_iterations, offline, no_typing, verbose, conversation_history, llm=llm_instance)
                    if report_content:
                        # The conversation history is now managed within run_agent
                        pass
            except KeyboardInterrupt:
                print(Fore.CYAN + "\nExiting JanDive...")
                break

def clean_thinking_tokens(text):
    """Comprehensive removal of LLM thinking tokens in various formats, handling multi-line content."""
    # This pattern finds any XML-style tag and removes it, including multi-line content.
    # It specifically includes <think> and <thought> as seen in outputs.
    patterns = [
        r'<tool_call>.*?</tool_call>',
        r'<call>.*?</call>',
        r'<execute>.*?</execute>',
        r'<tool_code>.*?</tool_code>',
        r'<tool_output>.*?</tool_output>',
        r'<thought>.*?</thought>',
        r'<think>.*?</think>',  # Added to catch the observed tag
        r'<plan>.*?</plan>',
        r'<human_input>.*?</human_input>',
        r'<response>.*?</response>',
        r'<tool_code_result>.*?</tool_code_result>',
        r'<tool_code_error>.*?</tool_code_error>',
        r'<tool_code_output>.*?</tool_code_output>',
        r'<tool_code_stdout>.*?</tool_code_stdout>',
        r'<tool_code_stderr>.*?</tool_code_stderr>',
        r'<tool_code_exit_code>.*?</tool_code_exit_code>',
        r'<tool_code_signal>.*?</tool_code_signal>',
        r'<tool_code_background_pids>.*?</tool_code_background_pids>',
        r'<tool_code_process_group_pgid>.*?</tool_code_process_group_pgid>',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    return text.strip()

def process_query(query, temperature, output, max_iterations, offline, no_typing, verbose, conversation_history=None, llm=None):
    detail_level = "standard"
    if "--concise" in query:
        detail_level = "concise"
        query = query.replace("--concise", "").strip()

    progress_tracker = ProgressTracker()
    progress_tracker.start()
    full_report = ""
    sources = []
    
    terminal_width = shutil.get_terminal_size().columns
    header = " RESEARCH REPORT "
    
    try:
        report_stream = run_agent(
            query,
            llm=llm,
            temperature=temperature,
            max_iterations=max_iterations,
            offline=offline,
            status_callback=progress_tracker.update_stage,
            detail_level=detail_level,
            conversation_history=conversation_history
        )
        
        # Stream the report. The ProgressTracker will handle printing.
        for chunk, src in report_stream:
            sources = src
            full_report += chunk
            progress_tracker.print(chunk)
            time.sleep(0.001) # Yield control to the display thread
        
        # Now that the report is complete, stop the progress bar
        progress_tracker.complete()
    except ConnectionError:
        print(Fore.RED + "\n❌ Network Error")
        return None
    finally:
        # Ensure the progress tracker is stopped even if there's an error
        if progress_tracker.is_running:
            progress_tracker.complete()

    # The report has been streamed, now we clean it for saving and history.
    cleaned_report = clean_thinking_tokens(full_report)

    # --- UI/UX and Saving ---
    if sources:
        print("\n\n" + Fore.BLUE + "--- Sources ---" + Style.RESET_ALL)
        for i, s in enumerate(sources, 1):
            print(f"  {i}. {s.get('title', 'N/A')}")
            print(f"     {Fore.GREEN}{s.get('url', 'N/A')}{Style.RESET_ALL}")
    
    print("\n" + Fore.CYAN + "=" * terminal_width)

    if cleaned_report:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}.md"
        
        # Format sources for the report file
        sources_text = ""
        if sources:
            sources_text += "\n\n---\n\n## Sources\n\n"
            for i, s in enumerate(sources, 1):
                title = s.get('title', 'N/A')
                url = s.get('url', 'N/A')
                sources_text += f"{i}. **{title}**\n   - URL: <{url}>\n"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# Research Report: {query}\n\n{cleaned_report}{sources_text}")
            print(f"\n{Fore.GREEN}✔ Report saved to {filename}{Style.RESET_ALL}")
        except IOError as e:
            print(f"\n{Fore.RED}❌ Error saving report: {e}{Style.RESET_ALL}")

    if conversation_history is not None:
        conversation_history.append((query, cleaned_report))

    return full_report

if __name__ == '__main__':
    main()
