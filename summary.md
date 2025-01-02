MoriCodingAgent is an AI agent that works in CLI and helps you write code like Cursor AI.
It can connect to local Ollama or remote Ollama server.

## How Cursor AI Works

Cursor AI is a code-aware IDE and AI programming assistant that:

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
   - Edit code files in the directory you are working on including subdirectories
   - Content aware code generation understanding other files in the project and the context of the code
   - Get a goal from the user and generate itterative code to achieve the goal until the goal is satisfied
   - Run the code and analyze the output and fix the code until the goal is satisfied
   - Code generation from natural language descriptions
   - Automated documentation generation
   - Code explanation and review capabilities
   - Multi-file context awareness

4. **Technical Integration**
   - Uses Large Language Models (LLMs) for code generation
   - Integrates with VS Code-like environment
   - Supports multiple programming languages
   - Maintains local context for better suggestions

This MoriCodingAgent aims to provide similar functionality by leveraging Ollama's models for code assistance and generation.
