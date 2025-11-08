"""CLI entrypoint for the Agent Application."""

import click
import yaml
from pathlib import Path
from agent_app.utils.logging import setup_logging

logger = setup_logging()


@click.command()
@click.option('--brief', required=True, help='Project brief/requirements')
@click.option('--config', default='config/local.yaml', help='Config file path')
@click.option('--output', default='output/sdd.md', help='Output file path')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(brief: str, config: str, output: str, verbose: bool):
    """Generate System Design Document from project brief."""
    
    if verbose:
        logger.setLevel("DEBUG")
    
    logger.info("Agent Application CLI entrypoint", brief=brief, config=config)
    
    # TODO: Implement full workflow
    # 1. Load config
    # 2. Initialize tools (RAG, MCP)
    # 3. Initialize agents
    # 4. Create LangGraph workflow
    # 5. Run workflow
    # 6. Save output
    
    click.echo(f"Generating SDD for: {brief}")
    click.echo(f"Config: {config}")
    click.echo(f"Output: {output}")
    click.echo("\n⚠️  Implementation in progress. See IMPLEMENTATION_GUIDE.md")


if __name__ == '__main__':
    main()

