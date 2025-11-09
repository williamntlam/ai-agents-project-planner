# Providing Input to Docker Container

## Current Implementation: Command-Line Arguments

The current `main.py` accepts input via command-line arguments. Here's how to provide input to the Docker container:

### Method 1: Using `docker exec` (Recommended)

```bash
# Start the container (if not running)
docker-compose up -d agent_app

# Run with input via command-line arguments
docker exec -it agent_app python main.py \
  --brief "Build a REST API for a todo list application with user authentication" \
  --verbose
```

The `-it` flags are important:
- `-i` = interactive (keeps STDIN open)
- `-t` = tty (allocates a pseudo-TTY for proper terminal interaction)

### Method 2: Override Command in docker-compose.yml

Edit `docker-compose.yml`:
```yaml
agent_app:
  # ...
  command: ["python", "main.py", "--brief", "Your project brief here", "--verbose"]
```

Then restart:
```bash
docker-compose restart agent_app
```

### Method 3: Using `docker-compose run` (One-off execution)

```bash
docker-compose run --rm agent_app python main.py \
  --brief "Your project brief" \
  --config config/local.yaml \
  --output output/sdd.md \
  --verbose
```

The `--rm` flag removes the container after execution.

## Interactive Input (Not Yet Implemented)

Currently, the app doesn't support interactive prompts. However, if you want to add interactive mode, here's how it would work:

### How Interactive Mode Would Work

1. **Add interactive flag to CLI**:
```python
@click.option('--interactive', is_flag=True, help='Interactive mode for clarifications')
```

2. **Handle prompts in Docker**:
```python
if interactive:
    answer = click.prompt("What is the expected traffic volume?")
```

3. **Run with interactive mode**:
```bash
docker exec -it agent_app python main.py \
  --brief "Build an API" \
  --interactive
```

The `-it` flags are **essential** for interactive mode - they allow the container to:
- Read from your terminal (STDIN)
- Display prompts properly (TTY)

## Passing Input via Files

### Option 1: Mount a file and read from it

```bash
# Create input file
echo "Build a REST API for a todo list application" > input.txt

# Mount and use
docker exec -it agent_app sh -c \
  "python main.py --brief \"\$(cat /app/input.txt)\""
```

### Option 2: Use environment variables

Modify `main.py` to read from environment:
```python
brief = os.getenv('PROJECT_BRIEF') or brief
```

Then in docker-compose.yml:
```yaml
agent_app:
  environment:
    PROJECT_BRIEF: "Your brief here"
```

## Handling Clarifications (Future Feature)

When agents request clarifications, you would:

1. **Check for pending clarifications**:
```python
if state.clarification_requests:
    for request in state.clarification_requests:
        if interactive:
            answer = click.prompt(request['question'])
            # Add to state
```

2. **Run interactively**:
```bash
docker exec -it agent_app python main.py \
  --brief "Build an API" \
  --interactive
```

3. **Or provide answers via file**:
```json
{
  "clarifications": [
    {"question": "What is the expected traffic?", "answer": "10k req/s"}
  ]
}
```

## Best Practices

1. **Always use `-it` flags** for any interactive commands
2. **Use `docker exec`** for one-off runs with different inputs
3. **Use command override** for repeated runs with same input
4. **Use volumes** to share input/output files between host and container

## Example Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Run with your input
docker exec -it agent_app python main.py \
  --brief "Build a microservice for order processing" \
  --output output/my_sdd.md \
  --verbose

# 3. Check output (mounted to ./output on host)
cat output/my_sdd.md

# 4. Run again with different input
docker exec -it agent_app python main.py \
  --brief "Build a user authentication service" \
  --output output/auth_sdd.md
```

