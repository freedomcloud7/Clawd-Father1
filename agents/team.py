"""
OpenClaw Team — orchestrates the full agent team around a task.
"""
import anyio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    SystemMessage,
    TextBlock,
    RateLimitEvent,
)

import config
from .definitions import AGENT_DEFINITIONS, ORCHESTRATOR_SYSTEM_PROMPT

console = Console()


class OpenClawTeam:
    """
    The OpenClaw autonomous agent team.

    The Godfather orchestrator receives tasks and delegates to specialist subagents
    (researcher, developer, analyst, reviewer, writer) via the Agent tool.
    """

    def __init__(self, cwd: str = config.CWD, model: str = config.MODEL):
        self.cwd = cwd
        self.model = model
        self._options = ClaudeAgentOptions(
            cwd=cwd,
            model=model,
            max_turns=config.MAX_TURNS,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash",
                           "WebSearch", "WebFetch", "Agent"],
            agents=AGENT_DEFINITIONS,
            permission_mode="acceptEdits",
        )

    async def run_task(self, task: str) -> str:
        """Run a single task and return the result."""
        console.print(Panel(
            f"[bold cyan]{task}[/bold cyan]",
            title="[bold]OpenClaw Task[/bold]",
            border_style="cyan",
        ))

        result = ""
        session_id = None

        async for message in query(prompt=task, options=self._options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                session_id = message.data.get("session_id")
                console.print(f"[dim]Session: {session_id}[/dim]")

            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        console.print(Markdown(block.text))

            elif isinstance(message, ResultMessage):
                result = message.result
                stop = message.stop_reason
                console.print(Panel(
                    Markdown(result) if result else "[dim]No output[/dim]",
                    title=f"[bold green]Done[/bold green] [dim]({stop})[/dim]",
                    border_style="green",
                ))

            elif isinstance(message, RateLimitEvent):
                status = message.rate_limit_info.status
                console.print(f"[yellow]Rate limit: {status}[/yellow]")

        return result

    async def run_interactive(self) -> None:
        """Run the agent team in an interactive REPL loop."""
        console.print(Panel(
            "[bold]OpenClaw[/bold] Autonomous Agent Team\n"
            "[dim]Type your task and press Enter. Type [bold]exit[/bold] to quit.[/dim]",
            border_style="magenta",
        ))

        while True:
            try:
                task = Prompt.ask("\n[bold magenta]Task[/bold magenta]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Goodbye.[/dim]")
                break

            if not task:
                continue
            if task.lower() in ("exit", "quit", "q"):
                console.print("[dim]Goodbye.[/dim]")
                break

            await self.run_task(task)
