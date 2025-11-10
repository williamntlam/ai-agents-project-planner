# LangChain Integration in AI Agents Project Planner

## Overview

This project uses **LangChain** as the core framework for LLM interactions and text processing. LangChain provides a standardized interface for working with language models, message handling, and document processing utilities.

## LangChain Components Used

### 1. **LangChain OpenAI Integration** (`langchain_openai`)

#### Component: `ChatOpenAI`
- **Location**: Used in all agent classes
- **Purpose**: Provides a standardized interface to OpenAI's chat models (GPT-4, GPT-3.5, etc.)

#### Usage Pattern:
```python
from langchain_openai import ChatOpenAI

# Initialize LLM client
llm = ChatOpenAI(
    model='gpt-4o-mini',           # Model name
    temperature=0.7,                # Creativity/randomness (0.0-2.0)
    max_tokens=6000,                # Maximum output tokens
    api_key=os.getenv('OPENAI_API_KEY')  # API key
)

# Invoke with messages
response = llm.invoke(messages)
content = response.content  # Extract text response
```

#### Where It's Used:
1. **SystemArchitectAgent** (`agent_app/agents/system_architect_agent.py`)
   - Generates High-Level Design (HLD) documents
   - Model: `gpt-4o-mini`, Temperature: `0.7`, Max Tokens: `6000`

2. **APIDataAgent** (`agent_app/agents/api_data_agent.py`)
   - Generates Low-Level Design (LLD) with API specifications
   - Model: `gpt-4o-mini`, Temperature: `0.7`, Max Tokens: `6000`

3. **DatabaseDesignerAgent** (`agent_app/agents/database_designer_agent.py`)
   - Generates database schemas and security specifications
   - Model: `gpt-4o-mini`, Temperature: `0.5` (lower for precision), Max Tokens: `6000`

4. **WriterFormatterAgent** (`agent_app/agents/writer_formatter_agent.py`)
   - Formats and assembles final documents
   - Model: `gpt-4o-mini`, Temperature: `0.5`, Max Tokens: `4000`

5. **ReviewerAgent** (`agent_app/agents/reviewer_agent.py`)
   - Reviews document quality and generates feedback
   - Model: `gpt-4o-mini`, Temperature: `0.3` (lowest for consistency), Max Tokens: `2000`

### 2. **LangChain Core Messages** (`langchain_core.messages`)

#### Components: `SystemMessage`, `HumanMessage`
- **Purpose**: Structured message types for chat-based LLM interactions
- **Why**: Ensures proper message formatting and role separation

#### Usage Pattern:
```python
from langchain_core.messages import HumanMessage, SystemMessage

# Build conversation messages
messages = [
    SystemMessage(content="""You are a senior system architect...
    [System instructions defining the agent's role and behavior]
    """),
    HumanMessage(content=prompt)  # User/agent prompt
]

# Send to LLM
response = self.llm.invoke(messages)
```

#### Message Types:
- **SystemMessage**: Defines the AI's role, behavior, and constraints
  - Contains instructions like "You are a senior system architect..."
  - Sets the context and personality for the LLM
  - Typically includes principles, best practices, and approach guidelines

- **HumanMessage**: Contains the actual task/prompt
  - The specific request or question
  - Includes context from RAG, project brief, etc.
  - The "user" input in the conversation

#### Example from SystemArchitectAgent:
```python
messages = [
    SystemMessage(content="""You are a senior system architect with deep expertise...
    
    Core Principles You Follow:
    - SOLID principles
    - DRY (Don't Repeat Yourself)
    - KISS (Keep It Simple, Stupid)
    ...
    """),
    HumanMessage(content=f"""You are a senior system architect. Generate a comprehensive HLD...
    
    Project Brief:
    {brief}
    
    Relevant Architectural Patterns:
    {context}
    ...
    """)
]
```

### 3. **LangChain Text Splitters** (`langchain_text_splitters`)

#### Components: `RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter`
- **Location**: `etl_pipeline/transformers/chunker.py`
- **Purpose**: Split documents into smaller chunks for embedding and vector storage

#### Usage Pattern:

##### RecursiveCharacterTextSplitter:
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,        # Target chunk size in characters
    chunk_overlap=200,      # Overlap between chunks (for context preservation)
    separators=["\n\n", "\n", ". ", " ", ""]  # Priority order for splitting
)

# Split text into chunks
chunks = splitter.split_text(text)
```

**How It Works:**
1. Tries to split on `"\n\n"` (paragraphs) first
2. If chunks still too large, splits on `"\n"` (lines)
3. Then on `". "` (sentences)
4. Then on `" "` (words)
5. Finally character-by-character if needed

**Why Recursive?**
- Preserves text structure (paragraphs, sentences)
- Avoids splitting mid-sentence when possible
- Maintains semantic coherence within chunks

##### MarkdownHeaderTextSplitter:
```python
from langchain_text_splitters import MarkdownHeaderTextSplitter

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on
)

# Split markdown by headers
md_splits = splitter.split_text(markdown_text)

# Further split large sections with RecursiveCharacterTextSplitter
for split in md_splits:
    if len(split.page_content) > chunk_size:
        sub_chunks = recursive_splitter.split_text(split.page_content)
        chunks.extend(sub_chunks)
    else:
        chunks.append(split.page_content)
```

**How It Works:**
1. First splits markdown by headers (preserves document structure)
2. Each split maintains header hierarchy in metadata
3. Large sections are further split using RecursiveCharacterTextSplitter
4. Preserves section context and relationships

## Architecture Flow: How LangChain Fits In

### 1. **ETL Pipeline (Document Processing)**

```
Document → Chunker (LangChain Text Splitters) → Embedder → Vector DB
```

**Step-by-Step:**
1. **Extract**: Documents loaded from filesystem
2. **Transform - Chunking**: 
   - Uses `RecursiveCharacterTextSplitter` or `MarkdownHeaderTextSplitter`
   - Splits documents into chunks (1000 chars, 200 overlap)
   - Preserves metadata (source, content_type, chunk_index)
3. **Transform - Embedding**: Chunks embedded using OpenAI embeddings
4. **Load**: Stored in PostgreSQL with pgvector extension

**Code Location**: `etl_pipeline/transformers/chunker.py`

### 2. **Agent Execution (LLM Interactions)**

```
State → Agent → RAG/MCP Tools → LangChain ChatOpenAI → Response → Updated State
```

**Step-by-Step for Each Agent:**

#### SystemArchitectAgent Example:
1. **Input**: `DocumentState` with `project_brief`
2. **RAG Retrieval**: Query vector DB for architectural patterns
3. **Prompt Building**: Combine brief + RAG context + system instructions
4. **LangChain Invocation**:
   ```python
   messages = [
       SystemMessage(content=system_instructions),
       HumanMessage(content=prompt)
   ]
   response = self.llm.invoke(messages)
   ```
5. **Output**: HLD content stored in `state.hld_draft`

#### APIDataAgent Example:
1. **Input**: `DocumentState` with `hld_draft`
2. **MCP Tools**: Query schema standards
3. **RAG Retrieval**: Query for API design patterns
4. **LangChain Invocation**: Same pattern as above
5. **Output**: LLD content stored in `state.lld_draft`

### 3. **Message Structure Pattern**

Every agent follows this pattern:

```python
def _initialize_llm(self):
    """Initialize ChatOpenAI with config"""
    return ChatOpenAI(
        model=self.get_config_value('model', 'gpt-4o-mini'),
        temperature=self.get_config_value('temperature', 0.7),
        max_tokens=self.get_config_value('max_tokens', 6000),
        api_key=api_key
    )

def perform_action(self, state: DocumentState) -> AgentOutput:
    # 1. Prepare context (RAG, MCP, etc.)
    context = self.rag_tool.retrieve_context(...)
    
    # 2. Build prompt
    prompt = self._build_prompt(state, context)
    
    # 3. Create messages
    messages = [
        SystemMessage(content=system_instructions),
        HumanMessage(content=prompt)
    ]
    
    # 4. Invoke LLM
    response = self.llm.invoke(messages)
    
    # 5. Process response
    content = response.content
    return AgentOutput(content=content, ...)
```

## Key Design Decisions

### 1. **Why LangChain Instead of Direct OpenAI API?**

- **Standardization**: Consistent interface across different LLM providers
- **Message Handling**: Built-in `SystemMessage`/`HumanMessage` for proper chat formatting
- **Extensibility**: Easy to swap models or add features (streaming, callbacks, etc.)
- **Tooling**: Integration with text splitters, document loaders, etc.
- **Future-Proof**: Can switch to other providers (Anthropic, Cohere) with minimal changes

### 2. **Why Separate SystemMessage and HumanMessage?**

- **Role Separation**: System defines "who" the AI is, Human defines "what" to do
- **Token Efficiency**: System messages can be cached/reused
- **Clarity**: Clear distinction between instructions and task
- **Best Practice**: Follows OpenAI's recommended chat format

### 3. **Why RecursiveCharacterTextSplitter?**

- **Semantic Preservation**: Keeps related content together (paragraphs, sentences)
- **Configurable**: Adjustable chunk size and overlap
- **Smart Splitting**: Tries multiple separators before character-by-character
- **Proven**: Industry-standard approach for RAG chunking

### 4. **Temperature Settings by Agent**

- **SystemArchitectAgent**: `0.7` - Balanced creativity for design
- **APIDataAgent**: `0.7` - Balanced for API design
- **DatabaseDesignerAgent**: `0.5` - Lower for precise schemas
- **WriterFormatterAgent**: `0.5` - Lower for consistent formatting
- **ReviewerAgent**: `0.3` - Lowest for consistent, objective reviews

## Integration Points

### 1. **LangChain + RAG Tool**

```python
# RAG Tool retrieves context
context = self.rag_tool.retrieve_context(query, top_k=25)

# Format for prompt
formatted_context = self.rag_tool.format_context_for_prompt(context)

# Include in LangChain prompt
prompt = f"""Project Brief: {brief}
Relevant Patterns: {formatted_context}
Generate HLD...
"""
```

### 2. **LangChain + MCP Tools**

```python
# MCP Tools query standards
schema_standards = self.mcp_tools.query_schema_standards()
standards_text = self.mcp_tools.format_for_llm(schema_standards)

# Include in LangChain prompt
prompt = f"""HLD: {hld_draft}
Schema Standards: {standards_text}
Generate LLD...
"""
```

### 3. **LangChain + State Management**

```python
# Read from state
hld_draft = state.hld_draft

# Generate with LangChain
response = self.llm.invoke(messages)
lld_content = response.content

# Write to state (via AgentOutput)
return AgentOutput(
    content=lld_content,
    ...
)
# Orchestrator updates state.hld_draft = output.content
```

## Error Handling

### LangChain-Specific Error Handling:

```python
try:
    response = self.llm.invoke(messages)
    content = response.content
except Exception as e:
    self.logger.error(
        "LLM generation failed",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True
    )
    raise RuntimeError(f"Failed to generate content: {str(e)}") from e
```

**Common Errors:**
- **API Key Missing**: `ValueError` if `OPENAI_API_KEY` not found
- **Token Limit Exceeded**: `OpenAIError` if prompt + max_tokens > model limit
- **Rate Limiting**: `RateLimitError` if too many requests
- **Network Issues**: Connection errors

## Configuration

### Environment Variables:
```bash
OPENAI_API_KEY=sk-...  # Required for all agents
```

### Agent Config (per agent):
```python
config = {
    'model': 'gpt-4o-mini',      # Model name
    'temperature': 0.7,           # Creativity
    'max_tokens': 6000,          # Output limit
    'api_key': 'sk-...'          # Optional (falls back to env)
}
```

### Chunker Config:
```python
chunker_config = {
    'chunk_size': 1000,          # Target chunk size
    'chunk_overlap': 200,        # Overlap between chunks
    'strategy': 'recursive_character'  # or 'markdown'
}
```

## Performance Considerations

### 1. **Token Limits**
- **Input**: Prompt length + system message
- **Output**: Limited by `max_tokens` parameter
- **Total**: Model context window (e.g., 8192 for gpt-4o-mini)
- **Strategy**: Truncate long content, prioritize important sections

### 2. **Chunking Strategy**
- **Chunk Size**: 1000 chars balances context vs. granularity
- **Overlap**: 200 chars preserves context across boundaries
- **Separators**: Priority order minimizes mid-sentence splits

### 3. **Model Selection**
- **gpt-4o-mini**: Chosen for cost-effectiveness and quality
- **Temperature**: Lower for precision tasks, higher for creativity
- **Max Tokens**: Set based on expected output length

## Future Extensibility

### Potential LangChain Features to Add:

1. **Streaming Responses**:
   ```python
   for chunk in self.llm.stream(messages):
       print(chunk.content, end="")
   ```

2. **Callbacks**:
   ```python
   from langchain.callbacks import StdOutCallbackHandler
   handler = StdOutCallbackHandler()
   response = self.llm.invoke(messages, callbacks=[handler])
   ```

3. **Multiple Providers**:
   ```python
   from langchain_anthropic import ChatAnthropic
   # Easy to swap providers
   ```

4. **LangChain Tools**:
   ```python
   from langchain.tools import Tool
   # Convert RAG/MCP tools to LangChain Tools
   ```

## Summary

LangChain serves as the **LLM orchestration layer** in this project:

1. **ChatOpenAI**: Standardized interface for all LLM calls
2. **Message Types**: Structured conversation format (SystemMessage/HumanMessage)
3. **Text Splitters**: Document chunking for RAG pipeline
4. **Integration**: Works seamlessly with RAG, MCP, and state management
5. **Consistency**: Uniform pattern across all agents

The architecture separates concerns:
- **LangChain**: LLM interaction and text processing
- **RAG Tool**: Vector search and context retrieval
- **MCP Tools**: Structured standards queries
- **LangGraph**: Workflow orchestration
- **Agents**: Business logic and prompt engineering

This modular design makes it easy to:
- Swap LLM providers
- Adjust chunking strategies
- Modify agent behavior
- Add new capabilities

