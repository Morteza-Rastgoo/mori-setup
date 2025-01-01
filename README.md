# MoriCodingAgent Setup Script

This repository contains the setup script for MoriCodingAgent, an AI agent that works in CLI and helps you write code like Cursor AI. It can connect to local Ollama or remote Ollama server.

## Features

- **Local Setup**: Installs and configures Ollama locally
- **Remote Setup**: Configures Ollama on a remote server
- **Automatic Requirements Check**: Verifies system requirements and dependencies
- **SSH Key Management**: Handles SSH key generation and provides guidance for remote setup
- **Port Management**: Manages Ollama service ports automatically

## Prerequisites

- curl
- SSH and SCP (for remote setup)
- At least 2GB of free disk space
- SSH key pair (will be generated if not present)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/mori-setup.git
cd mori-setup
```

2. Create a `.env` file for remote setup (optional):
```bash
REMOTE_HOST="your.remote.host"
REMOTE_USER="your_username"
REMOTE_PORT=22  # Optional, defaults to 22
```

3. Make the script executable:
```bash
chmod +x setup.sh
```

4. Run the setup:
```bash
# For complete setup (local + remote if configured)
./setup.sh

# For local-only setup
./setup.sh local

# For remote-only setup
./setup.sh remote
```

## How It Works

The setup script provides functionality similar to Cursor AI by:

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

## License

MIT License