"""Configuration loader with YAML merging and environment variable substitution."""
import os
import re
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def substitute_env_vars(value: Any) -> Any:
    """Recursively substitute environment variables in config values.
    
    Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.
    
    Args:
        value: Config value (can be dict, list, or string)
    
    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, dict):
        return {k: substitute_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [substitute_env_vars(item) for item in value]
    elif isinstance(value, str):
        # Pattern: ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replace(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) else None
            return os.getenv(var_name, default) if default is not None else os.getenv(var_name, match.group(0))
        
        return re.sub(pattern, replace, value)
    else:
        return value


def load_config(config_path: str, base_config_path: str = None) -> Dict[str, Any]:
    """Load and merge configuration files.
    
    Loads base config (if provided) and merges with environment-specific config.
    Environment variables are substituted in the final config.
    
    Args:
        config_path: Path to environment-specific config file (e.g., local.yaml, prod.yaml)
        base_config_path: Optional path to base config file (e.g., base.yaml)
    
    Returns:
        Merged configuration dictionary with environment variables substituted
    """
    config = {}
    
    # Load base config first if provided
    if base_config_path and Path(base_config_path).exists():
        with open(base_config_path, 'r') as f:
            base_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, base_config)
    
    # Load environment-specific config
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            env_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, env_config)
    else:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Substitute environment variables
    config = substitute_env_vars(config)
    
    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries.
    
    Values from override take precedence over base.
    Nested dictionaries are merged recursively.
    
    Args:
        base: Base dictionary
        override: Override dictionary
    
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_config_path(env: str = None) -> str:
    """Get config file path based on environment.
    
    Args:
        env: Environment name (local, prod, etc.). If None, uses ETL_ENV env var or defaults to 'local'
    
    Returns:
        Path to config file
    """
    if env is None:
        env = os.getenv('ETL_ENV', 'local')
    
    config_dir = Path(__file__).parent.parent / 'config'
    config_file = config_dir / f'{env}.yaml'
    
    if not config_file.exists():
        # Fallback to base.yaml if env-specific config doesn't exist
        base_file = config_dir / 'base.yaml'
        if base_file.exists():
            return str(base_file)
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    return str(config_file)

