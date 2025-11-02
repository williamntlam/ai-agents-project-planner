# Why Use YAML Config Files?

## The Problem: Hardcoding Configuration

Without YAML config files, you'd hardcode settings directly in your Python code:

```python
# BAD: Hardcoded in extractors/filesystem_extractor.py
def extract(self):
    base_path = "/data/standards"  # ❌ Hardcoded!
    extensions = [".md", ".pdf"]   # ❌ Hardcoded!
    
# BAD: Hardcoded in transformers/chunker.py
def chunk(self, text):
    chunk_size = 1000    # ❌ Hardcoded!
    overlap = 200        # ❌ Hardcoded!

# BAD: Hardcoded in transformers/embedder.py
def embed(self, text):
    model = "openai/text-embedding-3-small"  # ❌ Hardcoded!
    batch_size = 32                          # ❌ Hardcoded!
```

## Why This is Bad

### 1. **Different Settings for Dev vs Production**
- **Local dev:** Small chunk sizes (500), test database
- **Production:** Larger chunks (2000), production database
- **Problem:** You'd need to edit code every time you switch environments!

### 2. **Changing Settings Requires Code Changes**
```python
# Want to try a different embedding model?
# You have to edit the Python file, commit, deploy...

# Want to adjust chunk size?
# Edit code again...
```

### 3. **Multiple Configurations**
- Different chunk sizes for different document types
- Different extractor paths for different data sources
- Can't easily switch between configurations

### 4. **No Centralized Configuration**
- Settings scattered across multiple Python files
- Hard to see what the pipeline is configured to do
- Difficult to review/document changes

## The Solution: YAML Config Files

### With YAML Config Files:

**`config/local.yaml`** (Development)
```yaml
extractors:
  filesystem:
    base_path: "./test_data"  # Local test folder
    extensions: [".md", ".pdf"]

transformers:
  chunker:
    chunk_size: 500          # Smaller for testing
    chunk_overlap: 100
  embedder:
    model: "text-embedding-3-small"
    batch_size: 10           # Smaller batches for dev

loaders:
  vector_db:
    connection_string: "postgresql://localhost:5432/test_db"
```

**`config/prod.yaml`** (Production)
```yaml
extractors:
  filesystem:
    base_path: "/data/production/standards"  # Production path
    extensions: [".md", ".pdf", ".docx"]

transformers:
  chunker:
    chunk_size: 2000         # Larger chunks for production
    chunk_overlap: 400
  embedder:
    model: "text-embedding-3-large"  # Better model
    batch_size: 64           # Larger batches

loaders:
  vector_db:
    connection_string: "${DATABASE_URL}"  # From environment
```

### How You Use It in Code:

**`main.py`**
```python
import yaml

# Load config
with open("config/local.yaml") as f:
    config = yaml.safe_load(f)

# Use config throughout your pipeline
extractor = FilesystemExtractor(
    base_path=config['extractors']['filesystem']['base_path'],
    extensions=config['extractors']['filesystem']['extensions']
)

chunker = Chunker(
    chunk_size=config['transformers']['chunker']['chunk_size'],
    chunk_overlap=config['transformers']['chunker']['chunk_overlap']
)
```

## Real-World Benefits

### 1. **Switch Environments Easily**
```bash
# Run locally
python -m etl_pipeline.main --config config/local.yaml

# Run in production
python -m etl_pipeline.main --config config/prod.yaml
```

### 2. **Tune Parameters Without Code Changes**
```yaml
# Try different chunk sizes - just edit YAML, no code changes!
chunker:
  chunk_size: 1500  # Changed from 1000 to 1500
```

### 3. **Version Control Configs Separately**
- `base.yaml` - Default settings (committed)
- `local.yaml` - Your personal dev settings (not committed, gitignored)
- `prod.yaml` - Production settings (committed, but no secrets)

### 4. **Easy to Understand Pipeline Settings**
Anyone can read the YAML file and understand:
- Where data comes from
- How documents are chunked
- What embedding model is used
- Where data goes

### 5. **Support Multiple Scenarios**
```yaml
# config/fast.yaml - Fast processing (smaller chunks, lower quality)
# config/quality.yaml - High quality (larger chunks, better embeddings)
# config/test.yaml - Quick tests
```

## Example: The Same Code, Different Configs

**Your Python code stays the same:**
```python
def run_pipeline(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # All components use config - code never changes!
    extractor = create_extractor(config['extractors'])
    transformer = create_transformer(config['transformers'])
    loader = create_loader(config['loaders'])
```

**But you can run it differently:**
```bash
# Development: Small batches, test data
python main.py --config config/local.yaml

# Production: Optimized for scale
python main.py --config config/prod.yaml

# Experiment: Try new settings
python main.py --config config/experiment.yaml
```

## Summary

**Without YAML configs:** Change code → test → commit → deploy (slow, risky)

**With YAML configs:** Edit YAML → run (instant, safe)

YAML configs let you **separate configuration from code**, which is a best practice in software engineering!

