from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.pretty import Pretty

from .agents import CompetitorAgent, CustomerAgent, GTMResearchAgent, PricingAgent
from .cognee_client import CogneeClient
from .config import get_settings
from .ingest import ingest_markdown_file
from .openai_client import check_openai_api
from .redis_client import ping_redis
from .retrieve import retrieve_context

console = Console()
app = typer.Typer(add_completion=False, help="FounderOS Memory Wiki commands")


def _print(data) -> None:
    console.print(Pretty(data, expand_all=True))


def run_check_redis() -> dict:
    return ping_redis(settings=get_settings())


def run_check_cognee() -> dict:
    return CogneeClient(get_settings()).health_check()


def run_check_openai() -> dict:
    return check_openai_api(get_settings())


def run_ingest(path: str) -> dict:
    return ingest_markdown_file(path)


def run_query(query: str, top_k: int = 5) -> list[dict]:
    return retrieve_context(query, top_k=top_k)


def run_agent(agent_name: str, query: str) -> dict:
    agent_key = agent_name.strip().lower()
    agent_map = {
        "gtm": GTMResearchAgent,
        "competitor": CompetitorAgent,
        "customer": CustomerAgent,
        "pricing": PricingAgent,
    }
    agent_cls = agent_map.get(agent_key)
    if agent_cls is None:
        raise typer.BadParameter(
            f"Unknown agent '{agent_name}'. Use one of: {', '.join(sorted(agent_map))}."
        )
    return agent_cls().run(query)


@app.command("check-redis")
def check_redis() -> None:
    _print(run_check_redis())


@app.command("check-cognee")
def check_cognee() -> None:
    _print(run_check_cognee())


@app.command("check-openai")
def check_openai() -> None:
    _print(run_check_openai())


@app.command("ingest")
def ingest(path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)]) -> None:
    _print(run_ingest(str(path)))


@app.command("query")
def query(
    q: Annotated[str, typer.Argument(help="Natural-language search query")],
    top_k: Annotated[int, typer.Option(min=1, max=20)] = 5,
) -> None:
    _print(run_query(q, top_k=top_k))


@app.command("agent")
def agent(
    agent_name: Annotated[str, typer.Argument(help="gtm, competitor, customer, or pricing")],
    q: Annotated[str, typer.Argument(help="Question for the agent")],
) -> None:
    _print(run_agent(agent_name, q))


if __name__ == "__main__":
    app()
