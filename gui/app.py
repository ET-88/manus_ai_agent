"""
GUI Application for Manus AI Agent

Provides a graphical user interface for interacting with the agent system.
"""

import os
import sys
import json
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox,
    QTabWidget, QSplitter, QFrame, QGroupBox, QFormLayout,
    QComboBox, QProgressBar, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCursor

from ..agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

# Helper thread for running async tasks
class AsyncTaskThread(QThread):
    """Thread for running async tasks without blocking the GUI"""
    
    # Define signals for communicating with the main thread
    task_started = pyqtSignal()
    task_progress = pyqtSignal(str)
    task_complete = pyqtSignal(dict)
    task_error = pyqtSignal(str)
    
    def __init__(self, orchestrator: AgentOrchestrator, task: str, yolo_mode: bool = False):
        """
        Initialize the async task thread
        
        Args:
            orchestrator: The agent orchestrator instance
            task: The task to run
            yolo_mode: Whether to run in autonomous mode
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.task = task
        self.yolo_mode = yolo_mode
    
    async def _run_task_async(self):
        """Run the task asynchronously"""
        try:
            self.task_started.emit()
            
            # Execute the task
            results = await self.orchestrator.run_task(self.task, self.yolo_mode)
            
            # Emit the completion signal with results
            self.task_complete.emit(results)
            
        except Exception as e:
            logger.error(f"Error running task: {str(e)}", exc_info=True)
            self.task_error.emit(str(e))
    
    def run(self):
        """Run the thread"""
        # Set up asyncio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async task
            loop.run_until_complete(self._run_task_async())
        finally:
            loop.close()


class ManusAgentGUI(QMainWindow):
    """Main GUI window for the Manus AI Agent"""
    
    def __init__(self, orchestrator: AgentOrchestrator):
        """
        Initialize the GUI
        
        Args:
            orchestrator: The agent orchestrator instance
        """
        super().__init__()
        self.orchestrator = orchestrator
        self.task_thread = None
        self.current_task_results = None
        
        # Set up the main window
        self.setWindowTitle("Manus AI Agent")
        self.setMinimumSize(900, 700)
        
        # Create the central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Set up the GUI components
        self._setup_input_section()
        self._setup_tabs()
        self._setup_status_bar()
        
        # Connect events
        self._connect_events()
        
        logger.info("GUI initialized")
    
    def _setup_input_section(self):
        """Set up the task input section"""
        input_group = QGroupBox("Task Input")
        input_layout = QVBoxLayout()
        
        # Task input field
        task_layout = QHBoxLayout()
        task_label = QLabel("Task:")
        task_label.setFixedWidth(80)
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter a task for the AI agent to execute...")
        self.submit_button = QPushButton("Run Task")
        self.submit_button.setFixedWidth(100)
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_input)
        task_layout.addWidget(self.submit_button)
        
        # Options layout
        options_layout = QHBoxLayout()
        
        # YOLO mode checkbox
        self.yolo_checkbox = QCheckBox("YOLO Mode (Run without asking for permission)")
        options_layout.addWidget(self.yolo_checkbox)
        options_layout.addStretch()
        
        # Add to input layout
        input_layout.addLayout(task_layout)
        input_layout.addLayout(options_layout)
        
        # Set the layout for the group
        input_group.setLayout(input_layout)
        
        # Add to main layout
        self.main_layout.addWidget(input_group)
    
    def _setup_tabs(self):
        """Set up the main tab widget"""
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.execution_tab = QWidget()
        self.plan_tab = QWidget()
        self.history_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Set up each tab
        self._setup_execution_tab()
        self._setup_plan_tab()
        self._setup_history_tab()
        self._setup_settings_tab()
        
        # Add tabs to the tab widget
        self.tab_widget.addTab(self.execution_tab, "Execution")
        self.tab_widget.addTab(self.plan_tab, "Plan")
        self.tab_widget.addTab(self.history_tab, "History")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        # Add to main layout
        self.main_layout.addWidget(self.tab_widget, 1)  # 1 is the stretch factor
    
    def _setup_execution_tab(self):
        """Set up the execution tab"""
        layout = QVBoxLayout(self.execution_tab)
        
        # Splitter for top/bottom sections
        splitter = QSplitter(Qt.Vertical)
        
        # Top section - execution output
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        output_label = QLabel("Execution Output:")
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        
        top_layout.addWidget(output_label)
        top_layout.addWidget(self.output_text)
        
        # Bottom section - tools execution
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        tools_label = QLabel("Tool Executions:")
        self.tools_text = QTextEdit()
        self.tools_text.setReadOnly(True)
        
        bottom_layout.addWidget(tools_label)
        bottom_layout.addWidget(self.tools_text)
        
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        
        # Add splitter to layout
        layout.addWidget(splitter)
    
    def _setup_plan_tab(self):
        """Set up the plan tab"""
        layout = QVBoxLayout(self.plan_tab)
        
        # Plan display
        plan_label = QLabel("Task Plan:")
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        
        layout.addWidget(plan_label)
        layout.addWidget(self.plan_text)
    
    def _setup_history_tab(self):
        """Set up the history tab"""
        layout = QVBoxLayout(self.history_tab)
        
        # History controls
        controls_layout = QHBoxLayout()
        
        history_label = QLabel("Task History:")
        self.history_dropdown = QComboBox()
        self.history_dropdown.setMinimumWidth(400)
        self.load_history_button = QPushButton("Load")
        self.clear_history_button = QPushButton("Clear")
        
        controls_layout.addWidget(history_label)
        controls_layout.addWidget(self.history_dropdown)
        controls_layout.addWidget(self.load_history_button)
        controls_layout.addWidget(self.clear_history_button)
        controls_layout.addStretch()
        
        # History display
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        
        layout.addLayout(controls_layout)
        layout.addWidget(self.history_text)
    
    def _setup_settings_tab(self):
        """Set up the settings tab"""
        layout = QVBoxLayout(self.settings_tab)
        
        # API settings
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(os.getenv("OPENROUTER_API_KEY", ""))
        
        self.model_dropdown = QComboBox()
        default_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "gpt-4-turbo-preview"
        ]
        self.model_dropdown.addItems(default_models)
        self.model_dropdown.setCurrentText(os.getenv("DEFAULT_MODEL", "claude-3-sonnet-20240229"))
        
        api_layout.addRow("OpenRouter API Key:", self.api_key_input)
        api_layout.addRow("Default Model:", self.model_dropdown)
        api_group.setLayout(api_layout)
        
        # Security settings
        security_group = QGroupBox("Security Settings")
        security_layout = QFormLayout()
        
        self.sandbox_checkbox = QCheckBox()
        self.sandbox_checkbox.setChecked(True)
        
        self.max_execution_time = QLineEdit()
        self.max_execution_time.setText("300")
        
        security_layout.addRow("Enable Sandbox:", self.sandbox_checkbox)
        security_layout.addRow("Max Execution Time (s):", self.max_execution_time)
        security_group.setLayout(security_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.save_settings_button = QPushButton("Save Settings")
        self.reset_settings_button = QPushButton("Reset to Defaults")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_settings_button)
        buttons_layout.addWidget(self.reset_settings_button)
        
        # Add everything to layout
        layout.addWidget(api_group)
        layout.addWidget(security_group)
        layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def _setup_status_bar(self):
        """Set up the status bar"""
        self.status_bar = self.statusBar()
        
        # Task progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setVisible(False)
        
        # Status text
        self.status_label = QLabel("Ready")
        
        # Add to status bar
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.addPermanentWidget(self.status_label)
    
    def _connect_events(self):
        """Connect event handlers"""
        # Task submission
        self.submit_button.clicked.connect(self.run_task)
        self.task_input.returnPressed.connect(self.run_task)
        
        # History tab
        self.load_history_button.clicked.connect(self.load_history_item)
        self.clear_history_button.clicked.connect(self.clear_history)
        
        # Settings tab
        self.save_settings_button.clicked.connect(self.save_settings)
        self.reset_settings_button.clicked.connect(self.reset_settings)
    
    def run_task(self):
        """Run a task with the agent orchestrator"""
        task = self.task_input.text().strip()
        
        if not task:
            QMessageBox.warning(self, "Invalid Task", "Please enter a task to execute.")
            return
        
        # Check if another task is already running
        if self.task_thread and self.task_thread.isRunning():
            QMessageBox.warning(self, "Task Running", "Another task is already running. Please wait for it to complete.")
            return
        
        # Get YOLO mode setting
        yolo_mode = self.yolo_checkbox.isChecked()
        
        # Create and start the task thread
        self.task_thread = AsyncTaskThread(self.orchestrator, task, yolo_mode)
        
        # Connect signals
        self.task_thread.task_started.connect(self.on_task_started)
        self.task_thread.task_progress.connect(self.on_task_progress)
        self.task_thread.task_complete.connect(self.on_task_complete)
        self.task_thread.task_error.connect(self.on_task_error)
        
        # Start the thread
        self.task_thread.start()
        
        logger.info(f"Started task: {task}, YOLO mode: {yolo_mode}")
    
    def on_task_started(self):
        """Handle task started event"""
        # Update UI
        self.progress_bar.setVisible(True)
        self.status_label.setText("Running task...")
        self.submit_button.setEnabled(False)
        self.output_text.clear()
        self.tools_text.clear()
        self.plan_text.clear()
        
        # Show initial message
        self.output_text.append("Task started, generating plan...\n")
    
    def on_task_progress(self, message: str):
        """
        Handle task progress event
        
        Args:
            message: Progress message
        """
        # Update output text
        self.output_text.append(message)
        self.output_text.moveCursor(QTextCursor.End)
    
    def on_task_complete(self, results: Dict[str, Any]):
        """
        Handle task completion event
        
        Args:
            results: Task execution results
        """
        # Store the results
        self.current_task_results = results
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.status_label.setText("Task completed")
        self.submit_button.setEnabled(True)
        
        # Display the results
        self._display_task_results(results)
        
        # Update history dropdown
        self._update_history_dropdown()
        
        logger.info("Task completed")
    
    def on_task_error(self, error_message: str):
        """
        Handle task error event
        
        Args:
            error_message: Error message
        """
        # Update UI
        self.progress_bar.setVisible(False)
        self.status_label.setText("Task failed")
        self.submit_button.setEnabled(True)
        
        # Display error
        self.output_text.append(f"\nERROR: {error_message}")
        self.output_text.moveCursor(QTextCursor.End)
        
        # Show error message
        QMessageBox.critical(self, "Task Error", f"An error occurred while executing the task:\n\n{error_message}")
        
        logger.error(f"Task error: {error_message}")
    
    def _display_task_results(self, results: Dict[str, Any]):
        """
        Display task execution results in the UI
        
        Args:
            results: Task execution results
        """
        # Display plan
        plan = results.get("plan", [])
        plan_text = "# Task Plan\n\n"
        
        for i, step in enumerate(plan):
            status = step.get("status", "unknown")
            status_text = {
                "pending": "⏳ Pending",
                "in_progress": "⏳ In Progress",
                "completed": "✅ Completed",
                "failed": "❌ Failed",
                "unknown": "❓ Unknown"
            }.get(status, status)
            
            plan_text += f"## Step {i+1}: {step.get('description', 'Unknown step')}\n"
            plan_text += f"**Status:** {status_text}\n\n"
            
            if step.get("subtasks"):
                plan_text += "**Subtasks:**\n"
                for subtask in step.get("subtasks", []):
                    plan_text += f"- {subtask}\n"
                plan_text += "\n"
        
        self.plan_text.setPlainText(plan_text)
        
        # Display execution results
        execution = results.get("execution", {})
        steps = execution.get("steps", [])
        
        output_text = "# Task Execution Results\n\n"
        output_text += f"**Overall Status:** {execution.get('overall_status', 'unknown')}\n"
        if "duration" in execution:
            output_text += f"**Duration:** {execution['duration']:.2f} seconds\n\n"
        
        for step in steps:
            step_num = step.get("step_num", "?")
            description = step.get("description", "Unknown step")
            status = step.get("status", "unknown")
            
            output_text += f"## Step {step_num}: {description}\n"
            output_text += f"**Status:** {status}\n\n"
            
            step_result = step.get("result", {})
            if "summary" in step_result:
                output_text += f"**Summary:** {step_result['summary']}\n\n"
            
            if "execution_text" in step_result:
                output_text += "**Execution:**\n"
                output_text += f"{step_result['execution_text']}\n\n"
        
        self.output_text.setPlainText(output_text)
        
        # Display tool executions
        tools_text = "# Tool Executions\n\n"
        
        for step in steps:
            step_num = step.get("step_num", "?")
            step_result = step.get("result", {})
            tool_executions = step_result.get("tool_executions", [])
            
            if tool_executions:
                tools_text += f"## Step {step_num} Tool Executions\n\n"
                
                for i, execution in enumerate(tool_executions):
                    tool = execution.get("tool", "unknown")
                    args = execution.get("args", {})
                    success = execution.get("success", False)
                    result = execution.get("result", "")
                    
                    tools_text += f"### {i+1}. {tool}\n"
                    tools_text += f"**Success:** {'Yes' if success else 'No'}\n"
                    tools_text += f"**Arguments:** {json.dumps(args, indent=2)}\n\n"
                    
                    if result:
                        tools_text += "**Result:**\n"
                        tools_text += f"```\n{result}\n```\n\n"
                    
                    if "error" in execution:
                        tools_text += f"**Error:** {execution['error']}\n\n"
        
        self.tools_text.setPlainText(tools_text)
    
    def load_history_item(self):
        """Load and display a history item"""
        selected_index = self.history_dropdown.currentIndex()
        
        if selected_index < 0 or selected_index >= len(self.orchestrator.task_history):
            return
        
        # Get the selected history item
        history_item = self.orchestrator.task_history[selected_index]
        
        # Display it
        self._display_task_results(history_item)
        
        # Show message
        self.status_label.setText(f"Loaded history item: {history_item.get('task', 'Unknown task')}")
    
    def clear_history(self):
        """Clear task history"""
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all task history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Clear the history
            self.orchestrator.task_history = []
            
            # Update dropdown
            self._update_history_dropdown()
            
            # Clear display
            self.history_text.clear()
            
            # Show message
            self.status_label.setText("Task history cleared")
    
    def save_settings(self):
        """Save settings"""
        # Get values from UI
        api_key = self.api_key_input.text()
        default_model = self.model_dropdown.currentText()
        enable_sandbox = self.sandbox_checkbox.isChecked()
        
        try:
            max_execution_time = int(self.max_execution_time.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Setting", "Max execution time must be a number.")
            return
        
        # Update settings
        settings = self.orchestrator.settings
        settings.openrouter_api_key = api_key
        settings.default_model = default_model
        settings.enable_sandbox = enable_sandbox
        settings.max_execution_time = max_execution_time
        
        # Update environment variables
        os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ["DEFAULT_MODEL"] = default_model
        os.environ["ENABLE_SANDBOX"] = str(enable_sandbox).lower()
        os.environ["MAX_EXECUTION_TIME"] = str(max_execution_time)
        
        # Save settings to file
        from ..config.settings import save_settings
        if save_settings(settings):
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            self.status_label.setText("Settings saved")
        else:
            QMessageBox.warning(self, "Save Failed", "Failed to save settings.")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        # Confirm with user
        confirm = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Reset UI
            self.api_key_input.setText(os.getenv("OPENROUTER_API_KEY", ""))
            self.model_dropdown.setCurrentText("claude-3-sonnet-20240229")
            self.sandbox_checkbox.setChecked(True)
            self.max_execution_time.setText("300")
            
            # Reset orchestrator settings
            from ..config.settings import load_settings
            self.orchestrator.settings = load_settings()
            
            # Show message
            self.status_label.setText("Settings reset to defaults")
    
    def _update_history_dropdown(self):
        """Update the history dropdown with current history items"""
        # Clear dropdown
        self.history_dropdown.clear()
        
        # Add history items
        for item in self.orchestrator.task_history:
            task = item.get("task", "Unknown task")
            timestamp = item.get("timestamp", 0)
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            self.history_dropdown.addItem(f"{time_str} - {task}")

def start_gui(orchestrator: AgentOrchestrator):
    """
    Start the GUI application
    
    Args:
        orchestrator: The agent orchestrator instance
    """
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = ManusAgentGUI(orchestrator)
    window.show()
    
    # Run the application
    sys.exit(app.exec_()) 