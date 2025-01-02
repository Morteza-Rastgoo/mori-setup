#!/usr/bin/env python3

import os
import sys
import time
import json
import click
import logging
import requests
import subprocess
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Confirm
from rich.progress import Progress
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

console = Console()

class MoriAgent:
    def __init__(self):
        self.load_env()
        self._setup_directories()
        self._load_system_info()
        self._setup_ssh_tunnel()
        
    def _load_system_info(self):
        """Load system information and optimal model selection."""
        try:
            with open(os.path.expanduser('~/.mori/system_info.txt'), 'r') as f:
                info = {}
                current_section = None
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        if line.startswith('# '):
                            current_section = line[2:].lower().replace(' ', '_')
                            info[current_section] = {}
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if current_section:
                            info[current_section][key] = value
                        else:
                            info[key] = value
                
                self.system_info = info
                self.optimal_model = info.get('selected_model', {}).get('OPTIMAL_MODEL', 'mistral:7b-instruct-q4_K_M')
        except Exception as e:
            logging.warning(f"Failed to load system info: {e}")
            self.system_info = {}
            self.optimal_model = 'mistral:7b-instruct-q4_K_M'
    
    def _setup_directories(self):
        """Setup necessary directories."""
        os.makedirs(os.path.expanduser('~/.mori'), exist_ok=True)
        os.makedirs('backups', exist_ok=True)
    
    def generate_response(self, prompt, timeout=300):
        """Generate a response using the optimal model."""
        try:
            response = requests.post(
                f'http://127.0.0.1:{self.local_port}/api/generate',
                json={
                    'model': self.optimal_model,
                    'prompt': prompt,
                    'stream': True
                },
                timeout=timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Process streaming response
            full_response = ""
            with Progress() as progress:
                task = progress.add_task("[cyan]Generating response...", total=None)
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                full_response += data['response']
                                progress.update(task, advance=1)
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
            
            return full_response.strip()
        except requests.exceptions.Timeout:
            logging.error(f"Request timed out after {timeout} seconds")
            raise
        except Exception as e:
            logging.error(f"Failed to generate response: {e}")
            raise
    
    def ensure_model_available(self):
        """Ensure the optimal model is available."""
        try:
            response = requests.get(f'http://127.0.0.1:{self.local_port}/api/tags')
            response.raise_for_status()
            models_data = response.json()
            
            # Extract model names from the response
            available_models = set()
            if isinstance(models_data, list):
                for model in models_data:
                    if isinstance(model, dict) and 'name' in model:
                        available_models.add(model['name'])
            elif isinstance(models_data, dict) and 'models' in models_data:
                for model in models_data['models']:
                    if isinstance(model, dict) and 'name' in model:
                        available_models.add(model['name'])
            
            if self.optimal_model not in available_models:
                logging.info(f"Model {self.optimal_model} not found. Pulling it now...")
                response = requests.post(
                    f'http://127.0.0.1:{self.local_port}/api/pull',
                    json={'name': self.optimal_model}
                )
                response.raise_for_status()
                logging.info(f"Successfully pulled {self.optimal_model}")
        except Exception as e:
            logging.error(f"Failed to ensure model availability: {e}")
            raise

    def load_env(self):
        """Load environment variables and initialize settings."""
        load_dotenv()
        
        # Get remote settings
        self.remote_host = os.getenv('REMOTE_HOST')
        self.remote_user = os.getenv('REMOTE_USER')
        self.remote_port = int(os.getenv('REMOTE_PORT', '22'))
        
        # Get Ollama settings
        self.ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        self.ollama_port = int(os.getenv('OLLAMA_PORT', '11434'))
        self.local_port = int(os.getenv('LOCAL_PORT', self.ollama_port))  # Use separate local port if specified
        
        # Get agent settings
        self.max_iterations = int(os.getenv('DEFAULT_ITERATIONS', '25'))
        
        # Initialize SSH tunnel if using remote Ollama
        self.tunnel_process = None

    def _setup_ssh_tunnel(self):
        """Set up SSH tunnel to remote Ollama server."""
        try:
            # Kill any existing processes using the port
            self._cleanup_port(self.local_port)
            
            # Create SSH tunnel with direct command
            tunnel_cmd = f"ssh -N -L {self.local_port}:127.0.0.1:{self.ollama_port} -p {self.remote_port} {self.remote_user}@{self.remote_host}"
            
            logging.info(f"Setting up SSH tunnel to remote Ollama server (local port: {self.local_port})...")
            self.tunnel_process = subprocess.Popen(
                tunnel_cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for tunnel to be established
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                time.sleep(2)
                if self.tunnel_process.poll() is not None:
                    _, stderr = self.tunnel_process.communicate()
                    raise Exception(f"Failed to establish SSH tunnel: {stderr.decode()}")
                
                # Try to connect to Ollama
                try:
                    response = requests.get(f"http://127.0.0.1:{self.local_port}/api/version", timeout=5)
                    if response.status_code == 200:
                        logging.info("SSH tunnel established successfully")
                        return
                except requests.exceptions.RequestException:
                    retry_count += 1
                    logging.warning(f"Waiting for tunnel (attempt {retry_count}/{max_retries})...")
            
            raise Exception("Failed to establish SSH tunnel after multiple attempts")
            
        except Exception as e:
            logging.error(f"Error setting up SSH tunnel: {str(e)}")
            if self.tunnel_process:
                self.tunnel_process.kill()
            raise
            
    def _cleanup_port(self, port):
        """Kill any processes using the specified port."""
        try:
            # Find processes using the port
            cmd = f"lsof -ti:{port}"
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            if result.stdout:
                # Kill the processes
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(['kill', '-9', pid])
                    except Exception:
                        pass
        except Exception:
            pass
            
    def __del__(self):
        """Cleanup when the object is destroyed."""
        if self.tunnel_process:
            self.tunnel_process.kill()
            self._cleanup_port(self.local_port)

    def analyze_code(self, file_path):
        """Analyze code and provide insights."""
        try:
            # Ensure model is available
            self.ensure_model_available()
            
            # Read the file content
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Generate analysis prompt
            prompt = f"""Please analyze the following code and provide insights about:
1. Code structure and organization
2. Potential improvements
3. Security concerns
4. Code quality assessment

Code to analyze:

```
{code}
```

Please provide a detailed analysis."""

            # Generate response
            console.print("[green]Analyzing code...[/green]")
            response = self.generate_response(prompt)
            
            if response:
                console.print("\n[bold]Code Analysis:[/bold]")
                console.print(Markdown(response))
            else:
                console.print("[red]Error: Failed to generate analysis[/red]")
            
        except Exception as e:
            logging.error(f"Failed to analyze code: {e}")
            raise

@click.group()
def cli():
    """MoriCodingAgent - Your AI coding assistant"""
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def analyze(file_path):
    """Analyze code and provide insights"""
    agent = MoriAgent()
    agent.analyze_code(file_path)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def improve(file_path):
    """Suggest improvements for the code"""
    agent = MoriAgent()
    agent.suggest_improvements(file_path)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def explain(file_path):
    """Explain the code in detail"""
    agent = MoriAgent()
    agent.explain_code(file_path)

@cli.command()
@click.argument('prompt')
def ask(prompt):
    """Ask a coding-related question"""
    agent = MoriAgent()
    console.print("[green]Thinking...[/green]")
    response = agent.generate_response(prompt)
    if response:
        console.print(Markdown(response))

@cli.command()
def models():
    """List available models"""
    agent = MoriAgent()
    try:
        response = requests.get(f"{agent.base_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            console.print("\n[green]Available models:[/green]")
            for model in models:
                console.print(f"- {model['name']}")
        else:
            console.print("[red]Error: Failed to fetch models[/red]")
    except requests.exceptions.RequestException:
        console.print("[red]Error: Cannot connect to Ollama[/red]")

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--instruction', '-i', prompt='What changes would you like to make?',
              help='Instruction for modifying the code')
def edit(file_path, instruction):
    """Edit a file based on your instructions"""
    agent = MoriAgent()
    agent.edit_file(file_path, instruction)

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('goal')
@click.option('--max-iterations', '-m', type=int, 
              help='Maximum number of improvement iterations (default from DEFAULT_ITERATIONS in .env)')
def auto(file_path, goal, max_iterations):
    """Automatically achieve a goal without user intervention.
    
    The agent will iteratively improve the code until the goal is achieved or the maximum number
    of iterations is reached. The default number of iterations can be set in the .env file using
    the DEFAULT_ITERATIONS variable (defaults to 25 if not set).
    """
    agent = MoriAgent()
    agent.auto_achieve_goal(file_path, goal, max_iterations)

@cli.command('analyze-project')
@click.argument('project_dir', type=click.Path(exists=True))
def analyze_project(project_dir):
    """Analyze a project directory to understand requirements and structure"""
    agent = MoriAgent()
    agent.analyze_project(project_dir)

@cli.command('generate-project')
@click.argument('project_dir', type=click.Path(exists=True))
@click.option('--goal', '-g', help='Specific goal for the project implementation')
def generate_project(project_dir, goal):
    """Generate a complete project based on analysis and optional goal"""
    agent = MoriAgent()
    agent.generate_project(project_dir, goal)

@cli.command()
@click.option('--models', '-m', help='Comma-separated list of models to benchmark')
def benchmark(models):
    """Benchmark available models and select the fastest one"""
    agent = MoriAgent()
    if models:
        models_list = [m.strip() for m in models.split(',')]
        agent.benchmark_models(models_list)
    else:
        agent.benchmark_models()

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
        sys.exit(1) 