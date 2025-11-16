#!/usr/bin/env python3
"""
Environment Credentials Loader

Loads credentials from env_creds.yml and sets them as environment variables.
This ensures API keys and other sensitive data are properly loaded from the YAML file.

Usage:
    from utils.load_env_creds import load_env_credentials

    # Load all credentials into environment
    load_env_credentials()

    # Or load specific keys only
    load_env_credentials(keys=['OPENAI_API_KEY'])

    # Then access via os.getenv
    import os
    api_key = os.getenv('OPENAI_API_KEY')
"""

import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def find_env_creds_file() -> Optional[Path]:
    """
    Find env_creds.yml file by checking:
    1. Project root directory
    2. Parent directory
    3. Home directory

    Returns:
        Path to env_creds.yml if found, None otherwise
    """
    # Start from this file's directory
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    # Search locations in order of priority
    search_paths = [
        project_root / 'env_creds.yml',  # Project root
        project_root.parent / 'env_creds.yml',  # Parent of project
        Path.home() / 'Dev' / 'pycharm' / 'env.yml',  # Home directory (from comment in env_creds.yml)
    ]

    for path in search_paths:
        if path.exists():
            logger.info(f"Found env_creds file at: {path}")
            return path

    return None


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML file and return contents as dictionary.

    Args:
        file_path: Path to YAML file

    Returns:
        Dictionary of YAML contents

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Credentials file not found: {file_path}")

    with open(file_path, 'r') as f:
        try:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid YAML format in {file_path}: expected dictionary, got {type(data)}")
            return data
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse {file_path}: {e}")


def load_env_credentials(
    file_path: Optional[Path] = None,
    keys: Optional[List[str]] = None,
    required_keys: Optional[List[str]] = None,
    override: bool = False
) -> Dict[str, str]:
    """
    Load credentials from env_creds.yml and set as environment variables.

    Args:
        file_path: Path to env_creds.yml. If None, will search common locations.
        keys: List of specific keys to load. If None, loads all keys.
        required_keys: List of keys that must be present. Raises error if missing.
        override: If True, override existing environment variables. Default: False.

    Returns:
        Dictionary of loaded credentials

    Raises:
        FileNotFoundError: If env_creds.yml not found
        KeyError: If required_keys are missing

    Example:
        >>> load_env_credentials(required_keys=['OPENAI_API_KEY'])
        >>> import os
        >>> api_key = os.getenv('OPENAI_API_KEY')
    """
    # Find credentials file
    if file_path is None:
        file_path = find_env_creds_file()
        if file_path is None:
            raise FileNotFoundError(
                "Could not find env_creds.yml. Searched:\n"
                "  - Project root\n"
                "  - Parent directory\n"
                "  - ~/Dev/pycharm/env.yml\n"
                "Please create env_creds.yml with your credentials."
            )

    # Load YAML file
    creds = load_yaml_file(file_path)

    # Filter to specific keys if requested
    if keys is not None:
        creds = {k: v for k, v in creds.items() if k in keys}

    # Check for required keys
    if required_keys:
        missing = [k for k in required_keys if k not in creds]
        if missing:
            raise KeyError(
                f"Required keys missing from {file_path}: {', '.join(missing)}\n"
                f"Available keys: {', '.join(creds.keys())}"
            )

    # Set environment variables
    loaded = {}
    for key, value in creds.items():
        # Skip non-credential keys (like symlink_base_dir, symlinks, etc.)
        if key.startswith('symlink') or not isinstance(value, str):
            continue

        # Check if already set
        existing = os.getenv(key)
        if existing and not override:
            logger.debug(f"Skipping {key}: already set in environment")
            loaded[key] = existing
            continue

        # Set environment variable
        os.environ[key] = value
        loaded[key] = value
        logger.debug(f"Loaded {key} from {file_path}")

    logger.info(f"Loaded {len(loaded)} credentials from {file_path}")
    return loaded


def get_openai_api_key() -> str:
    """
    Get OpenAI API key, loading from env_creds.yml if not already set.

    Returns:
        OpenAI API key

    Raises:
        RuntimeError: If OPENAI_API_KEY not found
    """
    # Try to get from environment first
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        return api_key

    # Load from env_creds.yml
    try:
        creds = load_env_credentials(required_keys=['OPENAI_API_KEY'])
        api_key = creds.get('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is empty in env_creds.yml")
        return api_key
    except (FileNotFoundError, KeyError) as e:
        raise RuntimeError(
            f"OPENAI_API_KEY not found: {e}\n"
            "Please set OPENAI_API_KEY environment variable or add it to env_creds.yml"
        )


def verify_openai_key(api_key: Optional[str] = None) -> bool:
    """
    Verify OpenAI API key works by making a test API call.

    Args:
        api_key: API key to verify. If None, uses key from environment.

    Returns:
        True if key is valid, False otherwise
    """
    try:
        from openai import OpenAI

        if api_key is None:
            api_key = get_openai_api_key()

        client = OpenAI(api_key=api_key)

        # Make a minimal test call
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )

        logger.info("✓ OpenAI API key verified successfully")
        return True

    except Exception as e:
        logger.error(f"✗ OpenAI API key verification failed: {e}")
        return False


if __name__ == "__main__":
    # Test the loader
    logging.basicConfig(level=logging.INFO)

    print("Testing env_creds.yml loader...")
    print()

    try:
        # Load credentials
        creds = load_env_credentials()
        print(f"✓ Loaded {len(creds)} credentials")
        print(f"  Keys: {', '.join(creds.keys())}")
        print()

        # Test OpenAI key
        if 'OPENAI_API_KEY' in creds:
            print("Testing OpenAI API key...")
            api_key = get_openai_api_key()
            print(f"  Key starts with: {api_key[:15]}...")
            print(f"  Key length: {len(api_key)}")
            print()

            print("Verifying key with API call...")
            if verify_openai_key(api_key):
                print("✓ All tests passed!")
            else:
                print("✗ API key verification failed")
        else:
            print("⚠ OPENAI_API_KEY not found in credentials")

    except Exception as e:
        print(f"✗ Error: {e}")
        import sys
        sys.exit(1)
