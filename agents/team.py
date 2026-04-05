"""
OpenClaw Team — orchestrates the full agent colony using the Anthropic API directly.
"""
import json
import anyio
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

import config
from .definitions import AGENT_DEFINITIONS, GODFATHER_SYSTEM_PROMPT

console = Console()


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def run_specialist(name: str, task: str) -> str:
    """Run a specialist agent on a task and return its response."""
    agent = AGENT_DEFINITIONS.get(name)
    if not agent:
        return f"Unknown specialist: {name}"

    client = get_client()
    tools = []
    if "web_search" in agent.tools:
        tools.append({"type": "web_search_20260209", "name": "web_search"})

    console.print(f"\n[bold cyan]→ {name.upper()}[/bold cyan]: {task[:80]}...")

    messages = [{"role": "user", "content": task}]
    result_text = ""

    for _ in range(config.MAX_TURNS):
        kwargs = {
            "model": config.MODEL,
            "max_tokens": 4096,
            "system": agent.system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = client.messages.create(**kwargs)

        # Collect text from response
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        if response.stop_reason == "end_turn":
            break

        # Handle tool use (web search)
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Web search results come back automatically
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search completed."
                    })
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
        else:
            break

    console.print(f"[dim]{result_text[:200]}...[/dim]" if len(result_text) > 200 else f"[dim]{result_text}[/dim]")
    return result_text or "No response from specialist."


def run_godfather(task: str) -> str:
    """Run the Godfather orchestrator on a task."""
    client = get_client()

    # Tools the Godfather can use
    tools = [
        {
            "type": "web_search_20260209",
            "name": "web_search",
        },
        {
            "name": "delegate_to_specialist",
            "description": "Delegate a specific task to a specialist agent on your team.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "specialist": {
                        "type": "string",
                        "enum": ["researcher", "strategist", "developer", "analyst", "writer"],
                        "description": "Which specialist to delegate to"
                    },
                    "task": {
                        "type": "string",
                        "description": "The specific task for the specialist to complete"
                    }
                },
                "required": ["specialist", "task"]
            }
        }
    ]

    messages = [{"role": "user", "content": task}]
    final_text = ""

    console.print(Panel(
        f"[bold cyan]{task}[/bold cyan]",
        title="[bold]The Godfather[/bold]",
        border_style="magenta"
    ))

    for turn in range(config.MAX_TURNS):
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=8096,
            system=GODFATHER_SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
            thinking={"type": "adaptive"},
        )

        # Extract text
        for block in response.content:
            if hasattr(block, "text"):
                final_text = block.text
                if final_text.strip():
                    console.print(Markdown(final_text))

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "delegate_to_specialist":
                        specialist = block.input.get("specialist", "")
                        subtask = block.input.get("task", "")
                        result = run_specialist(specialist, subtask)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                    elif block.name == "web_search":
                        # Web search handled automatically by API
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Search completed."
                        })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
        else:
            break

    return final_text


class OpenClawTeam:
    """Main interface for the OpenClaw agent colony."""

    def run_task(self, task: str) -> str:
        return run_godfather(task)

    def run_interactive(self) -> None:
        console.print(Panel(
            "[bold]OpenClaw Colony[/bold] — Autonomous Money-Making System\n"
            "[dim]Type your goal and press Enter. Type [bold]exit[/bold] to quit.[/dim]",
            border_style="magenta"
        ))

        while True:
            try:
                task = input("\n[Goal] → ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Shutting down colony.[/dim]")
                break

            if not task:
                continue
            if task.lower() in ("exit", "quit", "q"):
                console.print("[dim]Colony offline.[/dim]")
                break

            self.run_task(task)
