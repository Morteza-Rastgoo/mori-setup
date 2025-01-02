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
from rich.progress import Progress
import requests
from pathlib import Path
import subprocess
import time
import tempfile
import glob

console = Console()

class MoriAgent:
    def __init__(self, host="localhost", port=11434, model="mistral"):
        self.host = host
        self.port = port
        self.model = model
        self.base_url = f"http://{host}:{port}"
        self.context = []
        self.project_files = {}
        self.file_relationships = {}
        self.max_iterations = 5  # Maximum number of improvement iterations
        
    def scan_project(self, start_path="."):
        """Scan the project directory and analyze file relationships"""
        console.print("[green]Scanning project structure...[/green]")
        
        # Get all Python files
        python_files = []
        for root, _, files in os.walk(start_path):
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, start_path)
                    python_files.append(rel_path)
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing files...", total=len(python_files))
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        self.project_files[file_path] = {
                            'content': content,
                            'imports': self._extract_imports(content),
                            'classes': self._extract_classes(content),
                            'functions': self._extract_functions(content)
                        }
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read {file_path}: {str(e)}[/yellow]")
                progress.update(task, advance=1)
        
        # Analyze relationships
        self._analyze_relationships()
        
    def _extract_imports(self, content):
        """Extract import statements from code"""
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        return imports
        
    def _extract_classes(self, content):
        """Extract class names and their methods"""
        classes = {}
        current_class = None
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('class '):
                class_name = line[6:].split('(')[0].strip()
                current_class = class_name
                classes[current_class] = []
            elif current_class and line.startswith('def '):
                method_name = line[4:].split('(')[0].strip()
                classes[current_class].append(method_name)
        return classes
        
    def _extract_functions(self, content):
        """Extract function names and their parameters"""
        functions = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('def ') and not line.startswith('    def'):
                func_name = line[4:].split('(')[0].strip()
                functions.append(func_name)
        return functions
        
    def _analyze_relationships(self):
        """Analyze relationships between files"""
        for file_path, info in self.project_files.items():
            self.file_relationships[file_path] = {
                'imports_from': [],
                'imported_by': [],
                'related_files': []
            }
            
            # Find import relationships
            for imp in info['imports']:
                for other_file, other_info in self.project_files.items():
                    if other_file == file_path:
                        continue
                    
                    # Check if this file imports from other files
                    if any(c in imp for c in other_info['classes'].keys()) or \
                       any(f in imp for f in other_info['functions']):
                        self.file_relationships[file_path]['imports_from'].append(other_file)
                        
                    # Check if other files import from this file
                    if any(c in '\n'.join(other_info['imports']) for c in info['classes'].keys()) or \
                       any(f in '\n'.join(other_info['imports']) for f in info['functions']):
                        self.file_relationships[file_path]['imported_by'].append(other_file)
            
            # Find related files (files with similar classes/functions)
            for other_file, other_info in self.project_files.items():
                if other_file == file_path:
                    continue
                    
                # Check for similar class names or function names
                if (set(info['classes'].keys()) & set(other_info['classes'].keys())) or \
                   (set(info['functions']) & set(other_info['functions'])):
                    self.file_relationships[file_path]['related_files'].append(other_file)
                    
    def get_file_context(self, file_path):
        """Get context information for a specific file"""
        if not os.path.exists(file_path):
            return None
            
        rel_path = os.path.relpath(file_path)
        context = []
        
        # If we haven't scanned the project yet, do it now
        if not self.project_files:
            self.scan_project()
        
        if rel_path in self.file_relationships:
            relationships = self.file_relationships[rel_path]
            
            # Add import relationships
            if relationships['imports_from']:
                context.append("This file imports from: " + ", ".join(relationships['imports_from']))
            if relationships['imported_by']:
                context.append("This file is imported by: " + ", ".join(relationships['imported_by']))
            
            # Add related files
            if relationships['related_files']:
                context.append("Related files with similar functionality: " + ", ".join(relationships['related_files']))
            
            # Add class and function information
            if rel_path in self.project_files:
                file_info = self.project_files[rel_path]
                if file_info['classes']:
                    context.append("Classes defined: " + ", ".join(file_info['classes'].keys()))
                if file_info['functions']:
                    context.append("Functions defined: " + ", ".join(file_info['functions']))
        
        return "\n".join(context)

    def edit_file(self, file_path, instruction):
        """Edit a file based on user instruction with project context"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Analyzing project context...[/green]")
        context_info = self.get_file_context(file_path)
        
        console.print("[green]Analyzing your request...[/green]")
        
        # Create the prompt for code modification with context
        prompt = f"""I want you to modify this code according to the following instruction, taking into account the project context:

        INSTRUCTION: {instruction}
        
        PROJECT CONTEXT:
        {context_info if context_info else "No additional context available"}
        
        CURRENT CODE:
        ```python
        {original_code}
        ```
        
        Please provide:
        1. A clear explanation of the changes you'll make
        2. The complete modified code
        3. Any potential risks or considerations, especially regarding project dependencies
        
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
                
                # Update project context
                self.scan_project()
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

    def analyze_code(self, file_path):
        """Analyze code with project context"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Analyzing project context...[/green]")
        context_info = self.get_file_context(file_path)
        
        console.print("[green]Analyzing code...[/green]")
        prompt = f"""Analyze this code and provide insights, taking into account the project context:
        
        PROJECT CONTEXT:
        {context_info if context_info else "No additional context available"}
        
        CODE TO ANALYZE:
        ```python
        {code}
        ```
        
        Please provide:
        1. A brief summary
        2. Potential improvements
        3. Any security concerns
        4. Code quality assessment
        5. Integration considerations with related project files
        """
        
        response = self.generate_response(prompt)
        if response:
            console.print(Markdown(response))

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

    def achieve_goal(self, file_path, goal, max_iterations=None):
        """Iteratively improve code until the specified goal is achieved"""
        if not os.path.exists(file_path):
            console.print(f"[red]Error: File {file_path} not found[/red]")
            return
            
        if max_iterations is not None:
            self.max_iterations = max_iterations
            
        try:
            with open(file_path, 'r') as f:
                original_code = f.read()
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")
            return
            
        console.print("[green]Starting goal-based code generation...[/green]")
        console.print(f"[blue]Goal: {goal}[/blue]")
        
        current_code = original_code
        iteration = 1
        last_feedback = None
        
        while iteration <= self.max_iterations:
            console.print(f"\n[cyan]Iteration {iteration}/{self.max_iterations}[/cyan]")
            
            # Evaluate current code against goal
            evaluation = self._evaluate_code(current_code, goal, last_feedback)
            
            if evaluation['goal_achieved']:
                console.print("[green]✓ Goal achieved![/green]")
                break
                
            # Show current status
            console.print("\n[yellow]Current Status:[/yellow]")
            console.print(Markdown(evaluation['feedback']))
            
            # Generate improvements
            new_code = self._improve_code(current_code, goal, evaluation['feedback'])
            if not new_code:
                console.print("[red]Failed to generate improvements[/red]")
                break
                
            # Show proposed changes
            console.print("\n[blue]Proposed Changes:[/blue]")
            console.print(Syntax(new_code, "python", theme="monokai"))
            
            # Ask for confirmation
            if Confirm.ask("\nApply these changes?"):
                current_code = new_code
                last_feedback = evaluation['feedback']
                
                # Create backup
                backup_path = f"{file_path}.backup.{iteration}"
                with open(backup_path, 'w') as f:
                    f.write(current_code)
                    
                # Apply changes
                with open(file_path, 'w') as f:
                    f.write(current_code)
                    
                console.print(f"[green]Changes applied. Backup saved to {backup_path}[/green]")
            else:
                if not Confirm.ask("Continue to next iteration?"):
                    break
                    
            iteration += 1
            
        if iteration > self.max_iterations:
            console.print("[yellow]Maximum iterations reached[/yellow]")
            
        # Final evaluation
        final_evaluation = self._evaluate_code(current_code, goal, last_feedback)
        console.print("\n[bold blue]Final Status:[/bold blue]")
        console.print(Markdown(final_evaluation['feedback']))
        
    def _evaluate_code(self, code, goal, previous_feedback=None):
        """Evaluate how well the code meets the specified goal"""
        context_info = self.get_file_context(os.path.abspath('.'))
        
        prompt = f"""Evaluate how well this code meets the specified goal:

        GOAL: {goal}

        CODE:
        ```python
        {code}
        ```
        
        PROJECT CONTEXT:
        {context_info if context_info else "No additional context available"}
        
        PREVIOUS FEEDBACK:
        {previous_feedback if previous_feedback else "No previous feedback"}

        Please provide:
        1. Whether the goal has been achieved (Yes/No)
        2. Detailed feedback on current status
        3. Specific areas that need improvement
        4. Any potential issues or concerns

        Format your response as follows:
        ---ACHIEVED---
        (Yes/No)

        ---FEEDBACK---
        (Your detailed feedback here)
        """
        
        response = self.generate_response(prompt)
        if not response:
            return {'goal_achieved': False, 'feedback': "Failed to evaluate code"}
            
        try:
            achieved = response.split("---ACHIEVED---")[1].split("---FEEDBACK---")[0].strip().lower()
            feedback = response.split("---FEEDBACK---")[1].strip()
            
            return {
                'goal_achieved': achieved == 'yes',
                'feedback': feedback
            }
        except Exception:
            return {'goal_achieved': False, 'feedback': "Failed to parse evaluation"}
            
    def _improve_code(self, code, goal, feedback):
        """Generate improved code based on feedback"""
        context_info = self.get_file_context(os.path.abspath('.'))
        
        prompt = f"""Improve this code to better meet the specified goal:

        GOAL: {goal}

        CURRENT CODE:
        ```python
        {code}
        ```
        
        PROJECT CONTEXT:
        {context_info if context_info else "No additional context available"}
        
        CURRENT STATUS:
        {feedback}

        Please provide improved code that better meets the goal.
        Keep existing functionality intact while making necessary improvements.
        Maintain code style and documentation standards.
        
        Return ONLY the complete improved code without any additional text.
        """
        
        response = self.generate_response(prompt)
        if not response:
            return None
            
        # Clean up the response to extract only the code
        try:
            if "```python" in response:
                code = response.split("```python")[1].split("```")[0].strip()
            elif "```" in response:
                code = response.split("```")[1].split("```")[0].strip()
            else:
                code = response.strip()
            return code
        except Exception:
            return None

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

@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('goal')
@click.option('--max-iterations', '-m', type=int, help='Maximum number of improvement iterations')
def achieve(file_path, goal, max_iterations):
    """Iteratively improve code to achieve a specific goal"""
    agent = MoriAgent()
    agent.achieve_goal(file_path, goal, max_iterations)

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
        sys.exit(1) 