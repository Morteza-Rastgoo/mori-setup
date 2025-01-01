# MoriCodingAgent

MoriCodingAgent is an AI coding assistant that works in CLI and helps you write code like Cursor AI. It can connect to local Ollama or remote Ollama server.

## Features

- **Local Setup**: Installs and configures Ollama locally
- **Remote Setup**: Configures Ollama on a remote server
- **Code Analysis**: Analyzes your code and provides insights
- **Code Improvements**: Suggests code improvements and best practices
- **Code Explanation**: Explains code in detail
- **Interactive CLI**: Easy-to-use command-line interface
- **Multiple Models**: Support for different Ollama models

## Prerequisites

- Python 3.7+
- curl
- SSH and SCP (for remote setup)
- At least 2GB of free disk space
- SSH key pair (will be generated if not present)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Morteza-Rastgoo/mori-setup.git
cd mori-setup
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file for remote setup (optional):
```bash
REMOTE_HOST="your.remote.host"
REMOTE_USER="your_username"
REMOTE_PORT=22  # Optional, defaults to 22
```

4. Make the scripts executable:
```bash
chmod +x setup.sh mori.py
```

5. Run the Ollama setup:
```bash
# For complete setup (local + remote if configured)
./setup.sh

# For local-only setup
./setup.sh local

# For remote-only setup
./setup.sh remote
```

## CLI Usage

MoriCodingAgent provides several commands to help with your coding:

### Analyze Code
```bash
./mori.py analyze path/to/your/file.py
```
Analyzes your code and provides insights about:
- Code summary
- Potential improvements
- Security concerns
- Code quality

### Suggest Improvements
```bash
./mori.py improve path/to/your/file.py
```
Suggests specific improvements for:
- Performance optimizations
- Code readability
- Best practices
- Error handling

### Explain Code
```bash
./mori.py explain path/to/your/file.py
```
Provides detailed explanation of:
- Overall purpose
- How it works
- Key components
- Important functions/methods

### Ask Questions
```bash
./mori.py ask "How do I implement a binary search in Python?"
```
Get answers to coding questions with:
- Code examples
- Explanations
- Best practices

### List Available Models
```bash
./mori.py models
```
Shows all available Ollama models you can use.

### Using Different Models
```bash
./mori.py ask --model codellama "What is a decorator in Python?"
```

## How It Works

The agent works by:

1. **Code Understanding**
   - Analyzes your entire codebase for context
   - Understands project structure and dependencies
   - Maintains awareness of file relationships

2. **Real-Time Assistance**
   - Provides inline code completions
   - Offers context-aware suggestions
   - Helps with code refactoring and bug fixing

3. **Key Features**
   - Chat interface for code-related questions
   - Code generation from natural language descriptions
   - Automated documentation generation
   - Code explanation and review capabilities
   - Multi-file context awareness

4. **Technical Integration**
   - Uses Large Language Models (LLMs) for code generation
   - Integrates with VS Code-like environment
   - Supports multiple programming languages
   - Maintains local context for better suggestions

## Security Notes

- The script uses key-based SSH authentication only
- Passwords are disabled for SSH connections
- SSH keys are automatically generated if not present
- Remote setup requires proper SSH key configuration

## Troubleshooting

If you encounter issues:

1. **Port 11434 in use**:
   - The script will attempt to free the port automatically
   - If unsuccessful, manually check: `lsof -i:11434`

2. **SSH Connection Issues**:
   - Ensure SSH key is properly added to remote host
   - Verify remote host is reachable
   - Check if SSH port is open
   - Verify username has proper access

3. **Ollama Connection Issues**:
   - Make sure Ollama is running (`ollama serve`)
   - Check if the port is accessible
   - Verify the model is downloaded

## License

MIT License