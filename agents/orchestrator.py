"""
Agent Orchestrator Module

Manages the multi-agent system for task planning and execution.
"""

import os
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple

from langchain.agents import initialize_agent, Tool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..api.openrouter import OpenRouterAPI
from ..config.settings import Settings
from .tools import (
    WebScraper, 
    ShellExecutor,
    FileManager,
    WebSearchTool
)

logger = logging.getLogger(__name__)

# Prompt templates
PLANNING_TEMPLATE = """
You are an expert AI planning agent focused on breaking down complex tasks into clear, actionable steps.

TASK: {task}

YOUR GOAL: Create a detailed, step-by-step plan to accomplish this task efficiently.

CONSTRAINTS:
- Consider the available tools: {tools}
- If the task requires web access, include specific URLs or search queries
- If the task requires executing commands, specify them clearly
- Identify any potential credentials or access requirements
- Highlight any potential issues or challenges that might arise

Please respond with a structured plan in the following format:
1. [Step description]
   - Sub-task 1
   - Sub-task 2
2. [Next step description]
   - Sub-task 1
   - Sub-task 2

PLAN:
"""

EXECUTION_TEMPLATE = """
You are an expert AI execution agent responsible for carrying out specific tasks.

TASK STEP: {task_step}
OVERALL CONTEXT: {context}

YOUR GOAL: Execute this specific step as effectively as possible, using the tools available to you.

AVAILABLE TOOLS: {tools}

INSTRUCTIONS:
1. Consider which tool is most appropriate for this specific step
2. Execute the step with precision
3. Report back with the results, including any relevant information retrieved
4. If you encounter any errors or issues, try an alternative approach
5. If you require user input or authentication, request it clearly

Execute this step now.
"""

class AgentOrchestrator:
    """
    Orchestrates multiple specialized agents to plan and execute complex tasks.
    """
    
    def __init__(self, openrouter_api: OpenRouterAPI, settings: Settings):
        """
        Initialize the agent orchestrator
        
        Args:
            openrouter_api: Instance of OpenRouterAPI for LLM access
            settings: Application settings
        """
        self.openrouter_api = openrouter_api
        self.settings = settings
        self.task_history = []
        self.current_plan = None
        self.execution_results = {}
        
        # Initialize tools
        self.web_scraper = WebScraper()
        self.shell_executor = ShellExecutor(
            allowed_commands=settings.allowed_commands,
            blocked_commands=settings.blocked_commands,
            enable_sandbox=settings.enable_sandbox
        )
        self.file_manager = FileManager()
        self.web_search = WebSearchTool()
        
        logger.info("Agent orchestrator initialized with all tools")
    
    def get_available_tools(self) -> List[Tool]:
        """
        Get the list of available tools for agent use
        
        Returns:
            List of LangChain Tool objects
        """
        return [
            Tool(
                name="web_scraper",
                func=self.web_scraper.scrape,
                description="Scrapes content from a specified URL"
            ),
            Tool(
                name="shell_command",
                func=self.shell_executor.run_command,
                description="Executes a shell command in a sandboxed environment"
            ),
            Tool(
                name="file_manager",
                func=self.file_manager.manage_file,
                description="Creates, reads, updates, or deletes files in the working directory"
            ),
            Tool(
                name="web_search",
                func=self.web_search.search,
                description="Performs a web search for the provided query"
            )
        ]
    
    async def plan_task(self, task: str) -> List[Dict[str, Any]]:
        """
        Generate a plan for executing a complex task
        
        Args:
            task: The task description
            
        Returns:
            List of steps to execute the task
        """
        logger.info(f"Planning task: {task}")
        
        # Prepare tools description for the prompt
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.get_available_tools()])
        
        # Create planning prompt
        planning_prompt = PLANNING_TEMPLATE.format(
            task=task,
            tools=tools_desc
        )
        
        # Get planning response from LLM
        planning_response = self.openrouter_api.generate_completion(
            prompt=planning_prompt,
            temperature=self.settings.planning_temperature,
            max_tokens=self.settings.max_planning_tokens
        )
        
        # Parse the planning response into steps
        plan_text = planning_response.get("completion", "")
        plan_steps = self._parse_plan(plan_text)
        
        self.current_plan = plan_steps
        logger.info(f"Generated plan with {len(plan_steps)} steps")
        
        return plan_steps
    
    def _parse_plan(self, plan_text: str) -> List[Dict[str, Any]]:
        """
        Parse a plan text into structured steps
        
        Args:
            plan_text: The plan text from the LLM
            
        Returns:
            List of plan steps as dictionaries
        """
        # Simple parsing logic - this could be improved with more robust parsing
        lines = plan_text.strip().split("\n")
        
        steps = []
        current_step = None
        current_subtasks = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a step line (starts with a number)
            if line[0].isdigit() and ". " in line:
                # If we have a current step, add it to steps before starting a new one
                if current_step is not None:
                    steps.append({
                        "description": current_step,
                        "subtasks": current_subtasks,
                        "status": "pending"
                    })
                
                # Start a new step
                step_parts = line.split(". ", 1)
                if len(step_parts) == 2:
                    current_step = step_parts[1]
                    current_subtasks = []
            
            # Check if this is a subtask line
            elif line.startswith("-") or line.startswith("*"):
                subtask = line[1:].strip()
                if subtask and current_step is not None:
                    current_subtasks.append(subtask)
        
        # Add the last step if there is one
        if current_step is not None:
            steps.append({
                "description": current_step,
                "subtasks": current_subtasks,
                "status": "pending"
            })
        
        return steps
    
    async def execute_plan(self, plan: List[Dict[str, Any]], yolo_mode: bool = False) -> Dict[str, Any]:
        """
        Execute a task plan
        
        Args:
            plan: The plan steps to execute
            yolo_mode: Whether to run in autonomous mode without asking for permission
            
        Returns:
            Results of task execution
        """
        logger.info(f"Executing plan with {len(plan)} steps, YOLO mode: {yolo_mode}")
        
        results = {
            "steps": [],
            "overall_status": "in_progress",
            "start_time": time.time()
        }
        
        for i, step in enumerate(plan):
            step_num = i + 1
            logger.info(f"Executing step {step_num}: {step['description']}")
            
            # Execute the step
            step_result = await self.execute_step(step, step_num, len(plan), yolo_mode)
            
            # Record the result
            results["steps"].append({
                "step_num": step_num,
                "description": step["description"],
                "result": step_result,
                "status": step_result.get("status", "unknown")
            })
            
            # Update the plan step status
            step["status"] = step_result.get("status", "unknown")
            
            # If the step failed and we're not in YOLO mode, stop execution
            if step_result.get("status") == "failed" and not yolo_mode:
                logger.warning(f"Step {step_num} failed, stopping plan execution")
                results["overall_status"] = "failed"
                break
        
        # Check if all steps completed successfully
        if results["overall_status"] != "failed":
            results["overall_status"] = "completed"
        
        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]
        
        return results
    
    async def execute_step(
        self, 
        step: Dict[str, Any], 
        step_num: int, 
        total_steps: int,
        yolo_mode: bool
    ) -> Dict[str, Any]:
        """
        Execute a single step in the plan
        
        Args:
            step: The step to execute
            step_num: The step number
            total_steps: Total number of steps in the plan
            yolo_mode: Whether to run in autonomous mode
            
        Returns:
            Result of step execution
        """
        # Create context for execution agent
        context = f"This is step {step_num} of {total_steps} in the plan."
        
        # If there are previous steps, add their results to the context
        if step_num > 1 and self.execution_results:
            prev_results = []
            for prev_num in range(1, step_num):
                if prev_num in self.execution_results:
                    prev_result = self.execution_results[prev_num]
                    prev_results.append(f"Step {prev_num} result: {prev_result.get('summary', 'No summary available')}")
            
            if prev_results:
                context += "\n\nPrevious step results:\n" + "\n".join(prev_results)
        
        # Prepare tools description for the prompt
        tools_desc = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.get_available_tools()])
        
        # Create execution prompt
        execution_prompt = EXECUTION_TEMPLATE.format(
            task_step=step["description"] + "\n\nSubtasks:\n" + "\n".join([f"- {st}" for st in step["subtasks"]]),
            context=context,
            tools=tools_desc
        )
        
        # Get execution response from LLM
        execution_response = self.openrouter_api.generate_completion(
            prompt=execution_prompt,
            temperature=self.settings.execution_temperature,
            max_tokens=self.settings.max_execution_tokens
        )
        
        # Parse the execution plan
        execution_text = execution_response.get("completion", "")
        
        # Here we would actually execute the tools based on the agent's response
        # For now, we'll just simulate execution
        tool_executions = self._simulate_tool_execution(execution_text, yolo_mode)
        
        # Prepare result
        result = {
            "execution_text": execution_text,
            "tool_executions": tool_executions,
            "status": "completed" if all(te["success"] for te in tool_executions) else "failed",
            "summary": self._generate_summary(execution_text, tool_executions)
        }
        
        # Store the result
        self.execution_results[step_num] = result
        
        return result
    
    def _simulate_tool_execution(self, execution_text: str, yolo_mode: bool) -> List[Dict[str, Any]]:
        """
        Parse an execution response and execute any identified tools
        
        Args:
            execution_text: The execution agent's response
            yolo_mode: Whether to run in autonomous mode
            
        Returns:
            List of tool execution results
        """
        # In a real implementation, this would parse the execution_text to identify tools to execute
        # For now, we'll just simulate it with a placeholder implementation
        
        # This is a placeholder - in a real implementation, we'd extract actual tool calls
        tool_calls = []
        if "web_scraper" in execution_text.lower():
            tool_calls.append({"tool": "web_scraper", "args": {"url": "https://example.com"}})
        if "shell_command" in execution_text.lower():
            tool_calls.append({"tool": "shell_command", "args": {"command": "ls -la"}})
        if "file_manager" in execution_text.lower():
            tool_calls.append({"tool": "file_manager", "args": {"action": "read", "path": "example.txt"}})
        if "web_search" in execution_text.lower():
            tool_calls.append({"tool": "web_search", "args": {"query": "example search query"}})
        
        # Execute the identified tools
        execution_results = []
        for call in tool_calls:
            if not yolo_mode:
                # In non-YOLO mode, we'd check for user permission here
                # but for the simulation, we'll just assume all are approved
                pass
                
            # In a real implementation, we would actually execute the tool
            # For now, just simulate success
            execution_results.append({
                "tool": call["tool"],
                "args": call["args"],
                "success": True,
                "result": f"Simulated result for {call['tool']}"
            })
                
        return execution_results
    
    def _generate_summary(self, execution_text: str, tool_executions: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the step execution
        
        Args:
            execution_text: The execution agent's response
            tool_executions: List of tool execution results
            
        Returns:
            Summary text
        """
        # In a real implementation, we might send this back to the LLM for summarization
        # For now, generate a simple summary
        
        success_count = sum(1 for te in tool_executions if te["success"])
        failed_count = len(tool_executions) - success_count
        
        if failed_count == 0:
            status = "All tools executed successfully."
        elif success_count == 0:
            status = "All tool executions failed."
        else:
            status = f"{success_count} tools succeeded, {failed_count} tools failed."
        
        return f"Step execution: {status} Tools used: {', '.join(te['tool'] for te in tool_executions)}."
    
    async def run_task(self, task: str, yolo_mode: bool = False) -> Dict[str, Any]:
        """
        Run a complete task through planning and execution
        
        Args:
            task: The task description
            yolo_mode: Whether to run in autonomous mode
            
        Returns:
            Complete task results
        """
        logger.info(f"Running task: {task}, YOLO mode: {yolo_mode}")
        
        # Generate plan
        plan = await self.plan_task(task)
        
        # Execute plan
        execution_results = await self.execute_plan(plan, yolo_mode)
        
        # Combine results
        results = {
            "task": task,
            "plan": plan,
            "execution": execution_results,
            "yolo_mode": yolo_mode,
            "timestamp": time.time()
        }
        
        # Record in history
        self.task_history.append(results)
        
        return results 