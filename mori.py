#!/usr/bin/env python3

import click
import os
import sys
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import requests
from pathlib import Path
import subprocess
import time
import tempfile

console = Console()

class MoriAgent:
    def __init__(self, host="localhost", port=11434, model="mistral"):
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"
        self.context = []
        
    def wait_for_ollama(self, timeout=30):
        """Wait for Ollama to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/api/version", timeout=5)
                if response.status_code == 200:
                    return True
                time.sleep(1)
            except requests.exceptions.RequestException:
                console.print("[yellow]Waiting for Ollama to start...[/yellow]")
                time.sleep(2)
        return False
        
    def check_ollama_connection(self):
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
            
    def ensure_model_available(self):
        """Ensure the selected model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]
                if self.model not in available_models:
                    console.print(f"[yellow]Model {self.model} not found. Pulling it now...[/yellow]")
                    pull_response = requests.post(f"{self.base_url}/api/pull", json={"name": self.model})
                    if pull_response.status_code != 200:
                        console.print(f"[red]Failed to pull model {self.model}[/red]")
                        return False
                return True
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error checking models: {str(e)}[/red]")
            return False
            
    def generate_response(self, prompt, system_prompt=None):
        """Generate a response from the model"""
        if not self.check_ollama_connection():
            console.print("[yellow]Ollama not running. Waiting for it to start...[/yellow]")
            if not self.wait_for_ollama():
                console.print("[red]Error: Cannot connect to Ollama. Please make sure it's running.[/red]")
                return None
                
        if not self.ensure_model_available():
            return None
            
        data = {
            "model": self.model,
            "prompt": prompt,
            "context": self.context,
            "stream": False
        }
        
        if system_prompt:
            data["system"] = system_prompt
            
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                self.context = result.get("context", [])
                return result.get("response", "")
            else:
                console.print(f"[red]Error: Server returned status code {response.status_code}[/red]")
        except requests.exceptions.Timeout:
            console.print("[red]Error: Request timed out. The model might be taking too long to respond.[/red]")
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        return None

    def analyze_code(self, file_path):
        """Analyze code and provide insights"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Analyzing code...[/green]")
        prompt = f"""Analyze this code and provide insights:
        
        ```python
        {code}
        ```
        
        Please provide:
        1. A brief summary
        2. Potential improvements
        3. Any security concerns
        4. Code quality assessment
        """
        
        response = self.generate_response(prompt)
        if response:
            console.print(Markdown(response))

    def suggest_improvements(self, file_path):
        """Suggest improvements for the code"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Analyzing code for improvements...[/green]")
        prompt = f"""Review this code and suggest specific improvements:
        
        ```python
        {code}
        ```
        
        Focus on:
        1. Performance optimizations
        2. Code readability
        3. Best practices
        4. Error handling
        """
        
        response = self.generate_response(prompt)
        if response:
            console.print(Markdown(response))

    def explain_code(self, file_path):
        """Explain the code in detail"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Generating code explanation...[/green]")
        prompt = f"""Explain this code in detail:
        
        ```python
        {code}
        ```
        
        Include:
        1. Overall purpose
        2. How it works
        3. Key components
        4. Important functions/methods
        """
        
        response = self.generate_response(prompt)
        if response:
            console.print(Markdown(response))

    def edit_file(self, file_path, instruction):
        """Edit a file based on user instruction"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Analyzing your request...[/green]")
        
        # Create the prompt for code modification
        prompt = f"""I want you to modify this code according to the following instruction:
        
        INSTRUCTION: {instruction}
        
        CURRENT CODE:
        ```python
        {original_code}
        ```
        
        Please provide:
        1. A clear explanation of the changes you'll make
        2. The complete modified code
        3. Any potential risks or considerations
        
        Format your response as follows:
        ---EXPLANATION---
        (Your explanation here)
        
        ---CODE---
        (The complete modified code)
        
        ---NOTES---
        (Any additional notes, risks, or considerations)
        """
        
        response = self.generate_response(prompt)
        if not response:
            return
            
        # Parse the response
        try:
            explanation = response.split("---EXPLANATION---")[1].split("---CODE---")[0].strip()
            new_code = response.split("---CODE---")[1].split("---NOTES---")[0].strip()
            notes = response.split("---NOTES---")[1].strip()
        except IndexError:
            console.print("[red]Error: Couldn't parse the AI response properly[/red]")
            return
            
        # Show the changes
        console.print("\n[bold blue]Proposed Changes:[/bold blue]")
        console.print(Markdown(explanation))
        
        console.print("\n[bold blue]Modified Code:[/bold blue]")
        console.print(Syntax(new_code, "python", theme="monokai"))
        
        if notes:
            console.print("\n[bold blue]Additional Notes:[/bold blue]")
            console.print(Markdown(notes))
        
        # Ask for confirmation
        if Confirm.ask("\nDo you want to apply these changes?"):
            try:
                # Create a backup
                backup_path = f"{file_path}.backup"
                with open(backup_path, 'w') as f:
                    f.write(original_code)
                    
                # Write the new code
                with open(file_path, 'w') as f:
                    f.write(new_code)
                    
                console.print(f"[green]Changes applied successfully! Backup saved to {backup_path}[/green]")
            except Exception as e:
                console.print(f"[red]Error applying changes: {str(e)}[/red]")
                console.print("[yellow]Attempting to restore from backup...[/yellow]")
                try:
                    with open(backup_path, 'r') as f:
                        original_code = f.read()
                    with open(file_path, 'w') as f:
                        f.write(original_code)
                    console.print("[green]Successfully restored from backup[/green]")
                except Exception as restore_error:
                    console.print(f"[red]Error restoring from backup: {str(restore_error)}[/red]")
        else:
            console.print("[yellow]Changes cancelled[/yellow]")

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
@click.option('--model', default='codellama', help='Model to use for generation')
def ask(prompt, model):
    """Ask a coding-related question"""
    agent = MoriAgent(model=model)
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

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
        sys.exit(1) 