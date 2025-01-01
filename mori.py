#!/usr/bin/env python3

import click
import os
import sys
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
import requests
from pathlib import Path
import subprocess

console = Console()

class MoriAgent:
    def __init__(self, host="localhost", port=11434, model="codellama"):
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"
        self.context = []
        
    def check_ollama_connection(self):
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/version")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
            
    def generate_response(self, prompt, system_prompt=None):
        """Generate a response from the model"""
        if not self.check_ollama_connection():
            console.print("[red]Error: Cannot connect to Ollama. Make sure it's running.[/red]")
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
            response = requests.post(f"{self.base_url}/api/generate", json=data)
            if response.status_code == 200:
                result = response.json()
                self.context = result.get("context", [])
                return result.get("response", "")
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        return None

    def analyze_code(self, file_path):
        """Analyze code and provide insights"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        with open(file_path, 'r') as f:
            code = f.read()
            
        prompt = f"""Analyze this code and provide insights:
        
        ```
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
            
        with open(file_path, 'r') as f:
            code = f.read()
            
        prompt = f"""Review this code and suggest specific improvements:
        
        ```
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
            
        with open(file_path, 'r') as f:
            code = f.read()
            
        prompt = f"""Explain this code in detail:
        
        ```
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
            console.print("\nAvailable models:")
            for model in models:
                console.print(f"- {model['name']}")
        else:
            console.print("[red]Error: Failed to fetch models[/red]")
    except requests.exceptions.RequestException:
        console.print("[red]Error: Cannot connect to Ollama[/red]")

if __name__ == '__main__':
    cli() 