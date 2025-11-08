"""CLI entrypoint for the Agent Application."""

import click
import yaml
from pathlib import Path
from agent_app.utils.logging import setup_logging

logger = setup_logging()


@click.command()
@click.option('--brief', required=True, help='Project brief/requirements')
@click.option('--additional-context', help='Additional context or clarifications')
@click.option('--requirements-file', type=click.Path(exists=True), help='JSON/YAML file with structured requirements')
@click.option('--config', default='config/local.yaml', help='Config file path')
@click.option('--output', default='output/sdd.md', help='Output file path')
@click.option('--interactive', is_flag=True, help='Interactive mode for clarifications')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(
    brief: str,
    additional_context: str,
    requirements_file: str,
    config: str,
    output: str,
    interactive: bool,
    verbose: bool
):
    """Generate System Design Document from project brief.
    
    Supports multiple input methods:
    - Basic: --brief "Your project description"
    - With context: --brief "..." --additional-context "More details"
    - Structured: --brief "..." --requirements-file requirements.json
    - Interactive: --interactive (prompts for clarifications)
    """
    
    if verbose:
        logger.setLevel("DEBUG")
    
    logger.info("Agent Application CLI entrypoint", brief=brief, config=config)
    
    # Load requirements from file if provided
    requirements = None
    if requirements_file:
        import json
        import yaml
        from pathlib import Path
        
        file_path = Path(requirements_file)
        with open(file_path) as f:
            if file_path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
            requirements = data.get('requirements')
            # Also check for additional_context in file
            if not additional_context and 'additional_context' in data:
                additional_context = data['additional_context']
    
    # TODO: Implement full workflow
    # 1. Load config
    # 2. Initialize tools (RAG, MCP)
    # 3. Initialize agents
    # 4. Create LangGraph workflow
    # 5. Create initial state with all input
    # 6. Handle clarifications if interactive mode
    # 7. Run workflow
    # 8. Save output
    
    click.echo(f"Generating SDD for: {brief}")
    if additional_context:
        click.echo(f"Additional context: {additional_context[:100]}...")
    if requirements_file:
        click.echo(f"Requirements file: {requirements_file}")
    if interactive:
        click.echo("Interactive mode: Will prompt for clarifications")
    click.echo(f"Config: {config}")
    click.echo(f"Output: {output}")
    click.echo("\n⚠️  Implementation in progress. See IMPLEMENTATION_GUIDE.md")


if __name__ == '__main__':
    main()

