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
from dotenv import load_dotenv

console = Console()

class MoriAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get remote settings
        self.remote_host = os.getenv('REMOTE_HOST')
        self.remote_user = os.getenv('REMOTE_USER')
        self.remote_port = int(os.getenv('REMOTE_PORT', '22'))
        
        # Get Ollama settings
        self.ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        self.ollama_port = int(os.getenv('OLLAMA_PORT', '11434'))
        self.model = os.getenv('OLLAMA_MODEL', 'mistral')
        self.ollama_remote = os.getenv('OLLAMA_REMOTE', 'false').lower() == 'true'
        
        # Get agent settings
        self.max_iterations = int(os.getenv('DEFAULT_ITERATIONS', '25'))
        
        # Initialize SSH tunnel if using remote Ollama
        self.tunnel_process = None
        if self.ollama_remote:
            self._setup_ssh_tunnel()
        
        # Initialize base URL (always use localhost with SSH tunnel)
        self.base_url = f"http://localhost:{self.ollama_port}"
        
        # Other initializations
        self.context = []
        self.project_files = {}
        self.file_relationships = {}
        self.test_results = {}
        self._available_models = set()
        self._model_pulling = False
        self.auto_mode = False
        
    def _setup_ssh_tunnel(self):
        """Set up SSH tunnel to remote Ollama server"""
        try:
            # Kill any existing processes using the port
            self._cleanup_port(self.ollama_port)
            
            # Create SSH tunnel
            ssh_cmd = [
                'ssh',
                '-N',  # Don't execute remote command
                '-L', f'{self.ollama_port}:localhost:{self.ollama_port}',  # Port forwarding
                '-p', str(self.remote_port),
                f'{self.remote_user}@{self.remote_host}'
            ]
            
            console.print("[green]Setting up SSH tunnel to remote Ollama server...[/green]")
            self.tunnel_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for tunnel to be established
            time.sleep(2)
            if self.tunnel_process.poll() is not None:
                _, stderr = self.tunnel_process.communicate()
                raise Exception(f"Failed to establish SSH tunnel: {stderr.decode()}")
                
            console.print("[green]SSH tunnel established successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]Error setting up SSH tunnel: {str(e)}[/red]")
            if self.tunnel_process:
                self.tunnel_process.kill()
            raise
            
    def _cleanup_port(self, port):
        """Kill any processes using the specified port"""
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
        """Cleanup when the object is destroyed"""
        if self.tunnel_process:
            self.tunnel_process.kill()
            self._cleanup_port(self.ollama_port)
            
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
            if self.ollama_remote and not self.tunnel_process:
                self._setup_ssh_tunnel()
                
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
            
    def ensure_model_available(self):
        """Ensure the selected model is available"""
        if self.model in self._available_models:
            return True
            
        try:
            # Check if model is already downloaded
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                self._available_models = {m["name"] for m in models}
                
                if self.model not in self._available_models and not self._model_pulling:
                    self._model_pulling = True
                    console.print(f"[yellow]Model {self.model} not found. Pulling it now...[/yellow]")
                    
                    # Pull the model
                    with Progress() as progress:
                        task = progress.add_task(f"[cyan]Pulling {self.model}...", total=None)
                        pull_response = requests.post(f"{self.base_url}/api/pull", 
                                                   json={"name": self.model},
                                                   stream=True)
                        
                        if pull_response.status_code == 200:
                            for line in pull_response.iter_lines():
                                if line:
                                    progress.update(task, advance=1)
                            
                            self._available_models.add(self.model)
                            console.print(f"[green]Successfully pulled {self.model}[/green]")
                            self._model_pulling = False
                            return True
                        else:
                            console.print(f"[red]Failed to pull model {self.model}[/red]")
                            self._model_pulling = False
                            return False
                
                return self.model in self._available_models
                
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error checking models: {str(e)}[/red]")
            self._model_pulling = False
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

    def _run_code(self, file_path, test_input=None):
        """Run the code and capture its output and any errors"""
        try:
            # Create a temporary test runner file
            test_runner = f"""
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

try:
    # Capture stdout and stderr
    out = io.StringIO()
    err = io.StringIO()
    
    with redirect_stdout(out), redirect_stderr(err):
        # Execute the file
        with open("{file_path}", "r") as f:
            exec(f.read())
            
    # Get the output
    output = out.getvalue()
    errors = err.getvalue()
    
    print("---OUTPUT---")
    print(output)
    print("---ERRORS---")
    print(errors)
    print("---STATUS---")
    print("success")
    
except Exception as e:
    print("---OUTPUT---")
    print(out.getvalue() if 'out' in locals() else '')
    print("---ERRORS---")
    print(traceback.format_exc())
    print("---STATUS---")
    print("failure")
"""
            with open("test_runner.py", "w") as f:
                f.write(test_runner)
                
            # Run the test runner
            result = subprocess.run(
                [sys.executable, "test_runner.py"],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Parse the output
            output = result.stdout
            sections = {
                "output": "",
                "errors": "",
                "status": "failure"
            }
            
            current_section = None
            for line in output.split('\n'):
                if line.startswith('---') and line.endswith('---'):
                    current_section = line[3:-3].lower()
                elif current_section:
                    sections[current_section] = sections.get(current_section, '') + line + '\n'
            
            return {
                'success': sections['status'].strip() == 'success',
                'output': sections['output'].strip(),
                'errors': sections['errors'].strip()
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'errors': 'Code execution timed out after 30 seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'errors': str(e)
            }
        finally:
            # Clean up
            if os.path.exists("test_runner.py"):
                os.remove("test_runner.py")
                
    def _evaluate_execution(self, execution_result, goal):
        """Evaluate the execution results against the goal"""
        prompt = f"""Evaluate the code execution results against the specified goal:

        GOAL: {goal}

        EXECUTION RESULTS:
        Success: {execution_result['success']}
        
        Output:
        ```
        {execution_result['output']}
        ```
        
        Errors:
        ```
        {execution_result['errors']}
        ```

        Please analyze:
        1. Whether the code runs successfully
        2. If the output matches expectations
        3. Any errors or issues found
        4. Suggestions for fixing problems

        Format your response as follows:
        ---ACHIEVED---
        (Yes/No)

        ---FEEDBACK---
        (Your detailed feedback here)
        """
        
        response = self.generate_response(prompt)
        if not response:
            return {'goal_achieved': False, 'feedback': "Failed to evaluate execution"}
            
        try:
            achieved = response.split("---ACHIEVED---")[1].split("---FEEDBACK---")[0].strip().lower()
            feedback = response.split("---FEEDBACK---")[1].strip()
            
            return {
                'goal_achieved': achieved == 'yes',
                'feedback': feedback
            }
        except Exception:
            return {'goal_achieved': False, 'feedback': "Failed to parse evaluation"}

    def auto_achieve_goal(self, file_path, goal, max_iterations=None):
        """Automatically achieve a goal without user intervention"""
        self.auto_mode = True
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
            
        console.print("[green]Starting autonomous goal-based code generation...[/green]")
        console.print(f"[blue]Goal: {goal}[/blue]")
        
        current_code = original_code
        iteration = 1
        last_feedback = None
        
        while iteration <= self.max_iterations:
            console.print(f"\n[cyan]Iteration {iteration}/{self.max_iterations}[/cyan]")
            
            # Run the current code
            console.print("[green]Running code...[/green]")
            execution_result = self._run_code(file_path)
            
            # Show execution results
            if execution_result['output']:
                console.print("\n[blue]Output:[/blue]")
                console.print(execution_result['output'])
            if execution_result['errors']:
                console.print("\n[red]Errors:[/red]")
                console.print(execution_result['errors'])
                
            # Evaluate execution results
            execution_evaluation = self._evaluate_execution(execution_result, goal)
            
            # Evaluate code against goal
            code_evaluation = self._evaluate_code(current_code, goal, last_feedback)
            
            # Combine evaluations
            goal_achieved = execution_evaluation['goal_achieved'] and code_evaluation['goal_achieved']
            combined_feedback = f"""Code Analysis:
{code_evaluation['feedback']}

Execution Results:
{execution_evaluation['feedback']}"""
            
            if goal_achieved:
                console.print("[green]✓ Goal achieved![/green]")
                break
                
            # Show current status
            console.print("\n[yellow]Current Status:[/yellow]")
            console.print(Markdown(combined_feedback))
            
            # Generate improvements
            new_code = self._improve_code(current_code, goal, combined_feedback)
            if not new_code:
                console.print("[red]Failed to generate improvements[/red]")
                break
                
            # Show proposed changes
            console.print("\n[blue]Proposed Changes:[/blue]")
            console.print(Syntax(new_code, "python", theme="monokai"))
            
            # In auto mode, we automatically apply changes
            current_code = new_code
            last_feedback = combined_feedback
            
            # Create backup
            backup_path = f"{file_path}.backup.{iteration}"
            with open(backup_path, 'w') as f:
                f.write(current_code)
                
            # Apply changes
            with open(file_path, 'w') as f:
                f.write(current_code)
                
            console.print(f"[green]Changes applied automatically. Backup saved to {backup_path}[/green]")
            
            iteration += 1
            
        if iteration > self.max_iterations:
            console.print("[yellow]Maximum iterations reached[/yellow]")
            
        # Final run and evaluation
        final_execution = self._run_code(file_path)
        final_evaluation = self._evaluate_execution(final_execution, goal)
        
        console.print("\n[bold blue]Final Status:[/bold blue]")
        if final_execution['output']:
            console.print("\n[blue]Output:[/blue]")
            console.print(final_execution['output'])
        if final_execution['errors']:
            console.print("\n[red]Errors:[/red]")
            console.print(final_execution['errors'])
            
        console.print("\n[bold blue]Final Evaluation:[/bold blue]")
        console.print(Markdown(final_evaluation['feedback']))
        
        self.auto_mode = False  # Reset auto mode
        
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
        
        # Enhanced prompt for autonomous mode
        if self.auto_mode:
            prompt = f"""As an autonomous coding agent, improve this code to meet the specified goal:

            GOAL: {goal}

            CURRENT CODE:
            ```python
            {code}
            ```
            
            PROJECT CONTEXT:
            {context_info if context_info else "No additional context available"}
            
            CURRENT STATUS:
            {feedback}

            REQUIREMENTS:
            1. Make incremental, safe improvements
            2. Ensure all changes are backward compatible
            3. Maintain existing functionality while adding new features
            4. Follow best practices and coding standards
            5. Include proper error handling
            6. Add comprehensive documentation
            
            Return ONLY the complete improved code without any additional text.
            """
        else:
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

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]An unexpected error occurred: {str(e)}[/red]")
        sys.exit(1) 