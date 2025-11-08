#!/usr/bin/env python3
"""CLI entrypoint for ETL pipeline to generate vector database from documents."""
import sys
import os
from pathlib import Path
from typing import Optional
import click
from datetime import datetime, UTC

from etl_pipeline.utils.config_loader import load_config, get_config_path
from etl_pipeline.utils.logging import setup_logging
from etl_pipeline.extractors.filesystem_extractor import FilesystemExtractor
from etl_pipeline.transformers.normalizer import Normalizer
from etl_pipeline.transformers.chunker import Chunker
from etl_pipeline.transformers.embedder import Embedder
from etl_pipeline.transformers.metadata_enricher import MetadataEnricher
from etl_pipeline.loaders.vector_loader import PgVectorLoader
from etl_pipeline.loaders.audit_loader import AuditLoader
from etl_pipeline.models.document import RawDocument, Document
from etl_pipeline.models.chunk import Chunk
from etl_pipeline.utils.exceptions import ExtractionError, TransformationError, LoadingError


class ETLPipeline:
    """Main ETL pipeline orchestrator."""
    
    def __init__(self, config: dict):
        """Initialize pipeline with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = setup_logging(config.get('logging', {}))
        
        # Initialize components
        self.extractor = None
        self.normalizer = None
        self.chunker = None
        self.embedder = None
        self.metadata_enricher = None
        self.vector_loader = None
        self.audit_loader = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all pipeline components based on config."""
        # Initialize extractor
        if self.config.get('extractors', {}).get('filesystem', {}).get('enabled', True):
            self.extractor = FilesystemExtractor(
                self.config.get('extractors', {}).get('filesystem', {})
            )
        
        # Initialize transformers
        transformers_config = self.config.get('transformers', {})
        
        if transformers_config.get('normalizer', {}).get('enabled', True):
            self.normalizer = Normalizer(transformers_config.get('normalizer', {}))
        
        if transformers_config.get('chunker', {}).get('enabled', True):
            self.chunker = Chunker(transformers_config.get('chunker', {}))
        
        if transformers_config.get('embedder', {}).get('enabled', True):
            self.embedder = Embedder(transformers_config.get('embedder', {}))
        
        if transformers_config.get('metadata_enricher', {}).get('enabled', True):
            self.metadata_enricher = MetadataEnricher(
                transformers_config.get('metadata_enricher', {})
            )
        
        # Initialize loaders
        loaders_config = self.config.get('loaders', {})
        
        if loaders_config.get('vector_db', {}).get('enabled', True):
            self.vector_loader = PgVectorLoader(loaders_config.get('vector_db', {}))
        
        if loaders_config.get('audit', {}).get('enabled', True):
            self.audit_loader = AuditLoader(loaders_config.get('audit', {}))
    
    def run(self) -> dict:
        """Run the complete ETL pipeline.
        
        Returns:
            Dictionary with pipeline execution statistics
        """
        start_time = datetime.now(UTC)
        stats = {
            'start_time': start_time.isoformat(),
            'documents_processed': 0,
            'chunks_created': 0,
            'errors': [],
            'success': False
        }
        
        self.logger.info("Starting ETL pipeline", extra={
            'start_time': start_time.isoformat(),
            'config': {
                'incremental': self.config.get('pipeline', {}).get('incremental', False),
                'continue_on_error': self.config.get('pipeline', {}).get('continue_on_error', True)
            }
        })
        
        # Connect to loaders
        if self.vector_loader:
            self.vector_loader.connect()
        if self.audit_loader:
            self.audit_loader.connect()
        
        try:
            # Extract phase
            self.logger.info("Phase 1: Extraction")
            documents = list(self._extract())
            stats['documents_extracted'] = len(documents)
            
            self.logger.info(f"Extracted {len(documents)} documents", extra={
                'document_count': len(documents)
            })
            
            # Process each document
            for raw_doc in documents:
                try:
                    # Transform phase
                    document = self._normalize(raw_doc)
                    chunks = self._chunk(document)
                    enriched_chunks = self._enrich_metadata(chunks, document)
                    embedded_chunks = self._embed(enriched_chunks)
                    
                    # Load phase
                    self._load(embedded_chunks)
                    
                    # Audit
                    self._audit(raw_doc, document, len(embedded_chunks), success=True)
                    
                    stats['documents_processed'] += 1
                    stats['chunks_created'] += len(embedded_chunks)
                    
                    self.logger.info("Document processed successfully", extra={
                        'document_id': str(raw_doc.id),
                        'source': raw_doc.source,
                        'chunks_created': len(embedded_chunks)
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing document {raw_doc.source}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True, extra={
                        'document_id': str(raw_doc.id),
                        'source': raw_doc.source
                    })
                    
                    stats['errors'].append({
                        'document_id': str(raw_doc.id),
                        'source': raw_doc.source,
                        'error': str(e)
                    })
                    
                    if self.config.get('pipeline', {}).get('continue_on_error', True):
                        continue
                    else:
                        raise
            
            stats['success'] = True
            end_time = datetime.now(UTC)
            stats['end_time'] = end_time.isoformat()
            stats['duration_seconds'] = (end_time - start_time).total_seconds()
            
            self.logger.info("ETL pipeline completed successfully", extra=stats)
            
        except Exception as e:
            end_time = datetime.now(UTC)
            stats['end_time'] = end_time.isoformat()
            stats['duration_seconds'] = (end_time - start_time).total_seconds()
            stats['error'] = str(e)
            
            self.logger.error("ETL pipeline failed", exc_info=True, extra=stats)
            raise
        
        finally:
            # Disconnect from loaders
            if self.vector_loader:
                try:
                    self.vector_loader.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting vector loader: {e}")
            if self.audit_loader:
                try:
                    self.audit_loader.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting audit loader: {e}")
        
        return stats
    
    def _extract(self):
        """Extract raw documents."""
        if not self.extractor:
            raise ValueError("No extractor configured")
        
        self.logger.info("Extracting documents", extra={
            'extractor_type': type(self.extractor).__name__
        })
        
        return self.extractor.extract()
    
    def _normalize(self, raw_doc: RawDocument) -> Document:
        """Normalize raw document."""
        if not self.normalizer:
            raise ValueError("No normalizer configured")
        
        return self.normalizer.normalize(raw_doc)
    
    def _chunk(self, document: Document) -> list[Chunk]:
        """Chunk document into smaller pieces."""
        if not self.chunker:
            raise ValueError("No chunker configured")
        
        return self.chunker.chunk(document)
    
    def _enrich_metadata(self, chunks: list[Chunk], document: Document) -> list[Chunk]:
        """Enrich chunks with metadata."""
        if not self.metadata_enricher:
            return chunks
        
        enriched = []
        for chunk in chunks:
            enriched_chunk = self.metadata_enricher.enrich_chunk(chunk, document)
            enriched.append(enriched_chunk)
        
        return enriched
    
    def _embed(self, chunks: list[Chunk]) -> list[Chunk]:
        """Generate embeddings for chunks."""
        if not self.embedder:
            raise ValueError("No embedder configured")
        
        self.logger.info("Generating embeddings", extra={
            'chunk_count': len(chunks),
            'batch_size': self.config.get('transformers', {}).get('embedder', {}).get('batch_size', 100)
        })
        
        # Use embed_chunks method which handles Chunk objects
        embedded = self.embedder.embed_chunks(chunks)
        
        return embedded
    
    def _load(self, chunks: list[Chunk]):
        """Load chunks into vector database."""
        if not self.vector_loader:
            raise ValueError("No vector loader configured")
        
        self.logger.info("Loading chunks to vector database", extra={
            'chunk_count': len(chunks)
        })
        
        self.vector_loader.load_chunks(chunks)
    
    def _audit(self, raw_doc: RawDocument, document: Document, chunk_count: int, success: bool):
        """Log processing to audit system."""
        if not self.audit_loader:
            return
        
        try:
            # Log extraction
            if raw_doc:
                self.audit_loader.log_extraction(
                    source_path=raw_doc.source,
                    status='success' if success else 'failed'
                )
            
            # Log transformation
            if document:
                self.audit_loader.log_transformation(
                    document_id=str(document.id),
                    chunks_created=chunk_count,
                    status='success' if success else 'failed'
                )
            
            # Log loading
            self.audit_loader.log_loading(
                chunks_loaded=chunk_count if success else 0,
                status='success' if success else 'failed'
            )
        except Exception as e:
            # Don't fail the pipeline if audit logging fails
            self.logger.warning(f"Audit logging failed: {e}")


@click.command()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to configuration file (YAML). If not provided, uses ETL_ENV env var or defaults to local.yaml'
)
@click.option(
    '--env',
    '-e',
    type=click.Choice(['local', 'prod', 'staging'], case_sensitive=False),
    help='Environment name (local, prod, staging). Overrides ETL_ENV env var'
)
@click.option(
    '--base-config',
    type=click.Path(exists=True),
    help='Path to base configuration file (optional, for merging with env config)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Run pipeline without actually loading data (for testing)'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose logging (DEBUG level)'
)
def main(config: Optional[str], env: Optional[str], base_config: Optional[str], dry_run: bool, verbose: bool):
    """ETL Pipeline CLI - Generate vector database from documents.
    
    This command runs the complete ETL pipeline:
    1. Extracts documents from configured sources
    2. Normalizes and chunks documents
    3. Generates embeddings
    4. Loads into vector database (pgvector)
    
    Examples:
    
        # Use default config (local.yaml)
        python -m etl_pipeline.main
        
        # Use specific config file
        python -m etl_pipeline.main --config config/prod.yaml
        
        # Use environment name
        python -m etl_pipeline.main --env prod
        
        # Dry run (test without loading)
        python -m etl_pipeline.main --dry-run
    """
    try:
        # Determine config path
        if config:
            config_path = config
        elif env:
            from etl_pipeline.utils.config_loader import get_config_path
            config_path = get_config_path(env)
        else:
            from etl_pipeline.utils.config_loader import get_config_path
            config_path = get_config_path()
        
        # Determine base config path
        if not base_config:
            base_config_path = Path(config_path).parent / 'base.yaml'
            if not base_config_path.exists():
                base_config_path = None
        else:
            base_config_path = base_config
        
        # Load configuration
        config_dict = load_config(config_path, base_config_path)
        
        # Override log level if verbose
        if verbose:
            config_dict.setdefault('logging', {})['level'] = 'DEBUG'
        
        # Override dry-run mode
        if dry_run:
            config_dict.setdefault('loaders', {}).setdefault('vector_db', {})['enabled'] = False
            click.echo("DRY RUN MODE: Vector database loading disabled", err=True)
        
        # Initialize and run pipeline
        pipeline = ETLPipeline(config_dict)
        stats = pipeline.run()
        
        # Print summary
        click.echo("\n" + "="*60)
        click.echo("ETL Pipeline Summary")
        click.echo("="*60)
        click.echo(f"Status: {'SUCCESS' if stats['success'] else 'FAILED'}")
        click.echo(f"Documents Processed: {stats['documents_processed']}")
        click.echo(f"Chunks Created: {stats['chunks_created']}")
        if stats.get('duration_seconds'):
            click.echo(f"Duration: {stats['duration_seconds']:.2f} seconds")
        if stats.get('errors'):
            click.echo(f"Errors: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                click.echo(f"  - {error['source']}: {error['error']}")
        click.echo("="*60 + "\n")
        
        # Exit with appropriate code
        sys.exit(0 if stats['success'] else 1)
        
    except FileNotFoundError as e:
        click.echo(f"Error: Configuration file not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
