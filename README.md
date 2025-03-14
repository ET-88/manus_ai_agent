# Manus AI Agent

An autonomous AI agent system inspired by Manus AI, capable of handling complex tasks through multi-agent orchestration and LLM integration via OpenRouter.

## Features

- Multi-agent architecture for complex task planning and execution
- GUI interface for task input and monitoring
- "YOLO Mode" for autonomous task execution without user confirmation
- OpenRouter API integration for access to advanced LLMs like Claude 3.5 Sonnet
- Secure sandbox environment for running potentially risky operations

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables (create a `.env` file based on `.env.example`)
4. Run the application:
   ```
   python main.py
   ```

## VPS Deployment

For deploying on a Hostinger VPS or similar:

1. Connect to your VPS via SSH
2. Clone the repository
3. Install dependencies
4. Set up environment variables
5. Run the application with a process manager like `supervisord` or use `nohup` for persistent operation

## Environment Variables

Create a `.env` file with the following variables:

```
OPENROUTER_API_KEY=your_openrouter_api_key
DEFAULT_MODEL=claude-3-opus-20240229
```

## Security Notice

This system includes features for executing shell commands and automating tasks. Always run in a properly sandboxed environment to prevent security issues. 