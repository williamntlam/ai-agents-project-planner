"""CLI entrypoint for the Agent Application."""

import click
import yaml
import os
from pathlib import Path
from agent_app.orchestration.graph import create_workflow_graph
from agent_app.agents.system_architect_agent import SystemArchitectAgent
from agent_app.agents.api_data_agent import APIDataAgent
from agent_app.agents.reviewer_agent import ReviewerAgent
from agent_app.agents.writer_formatter_agent import WriterFormatterAgent
from agent_app.tools.rag_tool import RAGTool
from agent_app.tools.mcp_tools import MCPTools
from agent_app.schemas.document_state import DocumentState
from agent_app.utils.logging import setup_logging

logger = setup_logging()


def _initialize_rag_tool(config_data: dict):
    """Initialize RAG tool with vector DB connection and embedder."""
    try:
        # Try to import from etl_pipeline
        from etl_pipeline.loaders.vector_loader import PgVectorLoader
        from etl_pipeline.transformers.embedder import Embedder
        
        # Get database connection string from config or environment
        db_connection_string = os.getenv(
            "DATABASE_URL",
            config_data.get("tools", {}).get("mcp_tools", {}).get("db_connection_string", "")
        )
        
        if not db_connection_string:
            logger.warning("No DATABASE_URL found, RAG tool may not work properly")
            return None
        
        # Initialize embedder (use same model as ETL)
        embedder_config = {
            "model_name": "text-embedding-3-small",  # Default, should match ETL config
            "provider": "openai"
        }
        embedder = Embedder(embedder_config)
        
        # Initialize vector DB loader
        vector_db_config = {
            "connection_string": db_connection_string,
            "table_name": "document_chunks",
            "embedding_dimension": 1536,  # text-embedding-3-small dimension
            "batch_size": 100
        }
        vector_db_connection = PgVectorLoader(vector_db_config)
        vector_db_connection.connect()
        
        # Initialize RAG tool
        rag_config = config_data.get("tools", {}).get("rag_tool", {})
        rag_tool = RAGTool(vector_db_connection, embedder, rag_config)
        
        logger.info("RAG tool initialized successfully")
        return rag_tool
        
    except ImportError as e:
        logger.warning(f"Could not import ETL pipeline components: {e}")
        logger.warning("RAG tool will not be available")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize RAG tool: {e}")
        return None


def _initialize_mcp_tools(config_data: dict):
    """Initialize MCP tools with database connection."""
    try:
        # Get database connection string from config or environment
        db_connection_string = os.getenv(
            "DATABASE_URL",
            config_data.get("tools", {}).get("mcp_tools", {}).get("db_connection_string", "")
        )
        
        if not db_connection_string:
            logger.warning("No DATABASE_URL found, MCP tools may not work properly")
            return None
        
        # Initialize MCP tools
        mcp_config = config_data.get("tools", {}).get("mcp_tools", {})
        mcp_tools = MCPTools(db_connection_string, mcp_config)
        
        logger.info("MCP tools initialized successfully")
        return mcp_tools
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP tools: {e}")
        return None


@click.command()
@click.option('--brief', required=True, help='Project brief/requirements')
@click.option('--config', default='config/local.yaml', help='Config file path')
@click.option('--output', default='output/sdd.md', help='Output file path')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(brief: str, config: str, output: str, verbose: bool):
    """Generate System Design Document from project brief."""
    
    # 1. Load config
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"Error: Config file not found: {config}", err=True)
        return
    
    with open(config_path) as f:
        config_data = yaml.safe_load(f)
    
    # 2. Initialize logging
    if verbose:
        logger.setLevel("DEBUG")
    
    logger.info("Starting SDD generation workflow", brief=brief, config=config)
    
    # 3. Initialize tools
    rag_tool = _initialize_rag_tool(config_data)
    mcp_tools = _initialize_mcp_tools(config_data)
    
    tools = {}
    if rag_tool:
        tools['rag_tool'] = rag_tool
    if mcp_tools:
        tools['mcp_tools'] = mcp_tools
    
    if not tools:
        logger.warning("No tools initialized - agents may have limited functionality")
    
    # 4. Initialize agents
    try:
        agents = {
            'system_architect': SystemArchitectAgent(
                config_data['agents']['system_architect'],
                tools
            ),
            'api_data': APIDataAgent(
                config_data['agents']['api_data'],
                tools
            ),
            'reviewer': ReviewerAgent(
                config_data['agents']['reviewer'],
                tools
            ),
            'writer_formatter': WriterFormatterAgent(
                config_data['agents']['writer_formatter'],
                tools
            )
        }
    except KeyError as e:
        click.echo(f"Error: Missing agent configuration: {e}", err=True)
        return
    except Exception as e:
        click.echo(f"Error: Failed to initialize agents: {e}", err=True)
        logger.exception("Agent initialization failed")
        return
    
    # 5. Create workflow graph
    try:
        workflow = create_workflow_graph(agents, config_data)
    except Exception as e:
        click.echo(f"Error: Failed to create workflow: {e}", err=True)
        logger.exception("Workflow creation failed")
        return
    
    # 6. Initialize state
    initial_state = DocumentState(project_brief=brief)
    graph_state = {
        'state': initial_state,
        'current_node': '',
        'iteration_count': 0
    }
    
    # 7. Run workflow
    logger.info("Starting SDD generation workflow", brief=brief)
    try:
        final_state = workflow.invoke(graph_state)
    except Exception as e:
        click.echo(f"Error: Workflow execution failed: {e}", err=True)
        logger.exception("Workflow execution failed")
        return
    
    # 8. Save output
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    final_document = final_state.get('state', {}).final_document
    if not final_document:
        click.echo("Warning: No final document generated", err=True)
        logger.warning("Workflow completed but no final_document in state")
        return
    
    with open(output_path, 'w') as f:
        f.write(final_document)
    
    logger.info("SDD generated successfully", output=str(output_path))
    click.echo(f"✓ SDD generated successfully: {output_path}")


if __name__ == '__main__':
    main()

