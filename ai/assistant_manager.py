#!/usr/bin/env python3
"""
Translation Assistant Manager
Manages OpenAI assistants for Chinese novel translation pipeline with versioning
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from openai import OpenAI
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TranslationAssistantManager:
    """Manages translation assistants with local persistence and versioning"""

    def __init__(self, storage_dir=".assistants", api_key=None):
        """
        Initialize the manager.

        Args:
            storage_dir: Directory for storing assistant configurations
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        logger.info(f"TranslationAssistantManager initialized with storage: {self.storage_dir}")

    def create_assistant(
        self,
        name: str,
        instructions: str,
        description: str,
        schema: Optional[Dict] = None,
        model: str = "gpt-4.1-nano",
        version: str = "v1",
        temperature: float = 0.7,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create new translation assistant and store config locally.

        Args:
            name: Assistant name (e.g., "structuring", "translation", "footnoting")
            instructions: Full instructions text or path to .md file
            description: Human-readable description
            schema: JSON schema for structured output (optional)
            model: OpenAI model to use
            version: Version tag (e.g., "v1", "v2")
            temperature: Model temperature (0.0-2.0)
            metadata: Additional metadata to store

        Returns:
            dict: Assistant configuration
        """
        # Load instructions from file if it's a path
        if isinstance(instructions, (str, Path)) and str(instructions).endswith('.md'):
            instructions_path = Path(instructions)
            if instructions_path.exists():
                with open(instructions_path, 'r', encoding='utf-8') as f:
                    instructions = f.read()
                logger.info(f"Loaded instructions from {instructions_path}")
            else:
                raise FileNotFoundError(f"Instructions file not found: {instructions_path}")

        # Create assistant via OpenAI API
        assistant_params = {
            "name": f"{name}_{version}",
            "instructions": instructions,
            "model": model,
            "description": description,
            "temperature": temperature
        }

        # Add JSON response format if schema provided
        if schema:
            assistant_params["response_format"] = {"type": "json_object"}

        logger.info(f"Creating assistant {name}_{version} with model {model}...")
        assistant = self.client.beta.assistants.create(**assistant_params)

        # Save configuration locally
        config = {
            "assistant_id": assistant.id,
            "name": name,
            "version": version,
            "description": description,
            "instructions": instructions,
            "schema": schema,
            "model": model,
            "temperature": temperature,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self._save_config(f"{name}_{version}", config)
        logger.info(f"✓ Created assistant: {name}_{version} (ID: {assistant.id})")

        return config

    def get_assistant(self, name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """
        Get assistant configuration by name.

        Args:
            name: Assistant name
            version: Version tag or "latest"

        Returns:
            dict: Assistant configuration or None
        """
        if version == "latest":
            # Find latest version
            versions = self._get_versions(name)
            if not versions:
                logger.warning(f"No versions found for assistant: {name}")
                return None
            version = versions[-1]
            logger.debug(f"Using latest version: {version}")

        path = self.storage_dir / f"{name}_{version}.json"

        if not path.exists():
            logger.warning(f"Assistant config not found: {name}_{version}")
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_assistants(self, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all stored assistants.

        Args:
            name_filter: Filter by name prefix (optional)

        Returns:
            list: List of assistant configurations
        """
        assistants = []

        for path in self.storage_dir.glob("*.json"):
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if name_filter is None or config["name"].startswith(name_filter):
                    assistants.append(config)

        return sorted(assistants, key=lambda x: (x["name"], x["version"]))

    def get_assistant_id(self, name: str, version: str = "latest") -> Optional[str]:
        """
        Get assistant ID by name and version.

        Args:
            name: Assistant name
            version: Version tag or "latest"

        Returns:
            str: Assistant ID or None
        """
        config = self.get_assistant(name, version)
        return config["assistant_id"] if config else None

    def compare_versions(self, name: str, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two versions of an assistant.

        Args:
            name: Assistant name
            version1: First version
            version2: Second version

        Returns:
            dict: Comparison details
        """
        config1 = self.get_assistant(name, version1)
        config2 = self.get_assistant(name, version2)

        if not config1 or not config2:
            return {"error": "Version not found"}

        return {
            "name": name,
            "versions": {
                version1: {
                    "id": config1["assistant_id"],
                    "model": config1["model"],
                    "temperature": config1.get("temperature", "N/A"),
                    "created": config1["created_at"]
                },
                version2: {
                    "id": config2["assistant_id"],
                    "model": config2["model"],
                    "temperature": config2.get("temperature", "N/A"),
                    "created": config2["created_at"]
                }
            },
            "changes": {
                "instructions_changed": config1["instructions"] != config2["instructions"],
                "schema_changed": config1.get("schema") != config2.get("schema"),
                "model_changed": config1["model"] != config2["model"],
                "temperature_changed": config1.get("temperature") != config2.get("temperature")
            }
        }

    def export_assistant(self, name: str, version: str, output_file: str) -> str:
        """
        Export assistant config to file for sharing.

        Args:
            name: Assistant name
            version: Version tag
            output_file: Output file path

        Returns:
            str: Output file path
        """
        config = self.get_assistant(name, version)
        if not config:
            raise ValueError(f"Assistant {name}_{version} not found")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {name}_{version} to {output_file}")
        return str(output_path)

    def import_assistant(self, config_file: str, create_new: bool = True) -> Dict[str, Any]:
        """
        Import assistant config from file.

        Args:
            config_file: Path to JSON config
            create_new: If True, create new assistant via API; if False, just save config locally

        Returns:
            dict: Imported configuration
        """
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if create_new:
            # Create new assistant via API
            new_config = self.create_assistant(
                name=config["name"],
                instructions=config["instructions"],
                description=config["description"],
                schema=config.get("schema"),
                model=config["model"],
                version=config["version"],
                temperature=config.get("temperature", 0.7),
                metadata=config.get("metadata")
            )
            return new_config
        else:
            # Just save config locally (reuse existing assistant_id)
            self._save_config(f"{config['name']}_{config['version']}", config)
            logger.info(f"Imported {config['name']}_{config['version']} (local only)")
            return config

    def delete_assistant(self, name: str, version: str, delete_remote: bool = False):
        """
        Delete assistant configuration.

        Args:
            name: Assistant name
            version: Version tag
            delete_remote: If True, also delete from OpenAI
        """
        config = self.get_assistant(name, version)

        if delete_remote and config:
            try:
                self.client.beta.assistants.delete(config["assistant_id"])
                logger.info(f"Deleted remote assistant: {config['assistant_id']}")
            except Exception as e:
                logger.warning(f"Could not delete remote assistant: {e}")

        # Delete local config
        path = self.storage_dir / f"{name}_{version}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Deleted local config: {name}_{version}")

    def update_assistant(
        self,
        name: str,
        version: str,
        instructions: Optional[str] = None,
        description: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update an existing assistant.

        Args:
            name: Assistant name
            version: Version tag
            instructions: New instructions (optional)
            description: New description (optional)
            model: New model (optional)
            temperature: New temperature (optional)

        Returns:
            dict: Updated configuration
        """
        config = self.get_assistant(name, version)
        if not config:
            raise ValueError(f"Assistant {name}_{version} not found")

        # Prepare update parameters
        update_params = {}
        if instructions is not None:
            if isinstance(instructions, (str, Path)) and str(instructions).endswith('.md'):
                with open(instructions, 'r', encoding='utf-8') as f:
                    instructions = f.read()
            update_params["instructions"] = instructions
            config["instructions"] = instructions

        if description is not None:
            update_params["description"] = description
            config["description"] = description

        if model is not None:
            update_params["model"] = model
            config["model"] = model

        if temperature is not None:
            update_params["temperature"] = temperature
            config["temperature"] = temperature

        # Update via API
        if update_params:
            logger.info(f"Updating assistant {name}_{version}...")
            self.client.beta.assistants.update(
                assistant_id=config["assistant_id"],
                **update_params
            )

        # Update local config
        config["updated_at"] = datetime.now().isoformat()
        self._save_config(f"{name}_{version}", config)

        logger.info(f"✓ Updated assistant: {name}_{version}")
        return config

    def _save_config(self, key: str, config: Dict[str, Any]):
        """Save configuration to local storage"""
        path = self.storage_dir / f"{key}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _get_versions(self, name: str) -> List[str]:
        """Get all versions for a given assistant name"""
        versions = []
        for path in self.storage_dir.glob(f"{name}_*.json"):
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                versions.append(config["version"])
        # Sort versions (v1, v2, v3, etc.)
        return sorted(versions, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """CLI interface for assistant management"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Translation Assistant Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all assistants")
    list_parser.add_argument("--filter", help="Filter by name prefix")

    # Info command
    info_parser = subparsers.add_parser("info", help="Show assistant details")
    info_parser.add_argument("name", help="Assistant name")
    info_parser.add_argument("version", nargs="?", default="latest", help="Version (default: latest)")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two versions")
    compare_parser.add_argument("name", help="Assistant name")
    compare_parser.add_argument("version1", help="First version")
    compare_parser.add_argument("version2", help="Second version")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export assistant config")
    export_parser.add_argument("name", help="Assistant name")
    export_parser.add_argument("version", help="Version")
    export_parser.add_argument("output", help="Output file path")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import assistant config")
    import_parser.add_argument("config_file", help="Config file path")
    import_parser.add_argument("--create-new", action="store_true", help="Create new assistant via API")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete assistant")
    delete_parser.add_argument("name", help="Assistant name")
    delete_parser.add_argument("version", help="Version")
    delete_parser.add_argument("--remote", action="store_true", help="Also delete from OpenAI")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = TranslationAssistantManager()

    if args.command == "list":
        assistants = manager.list_assistants(args.filter)
        if not assistants:
            print("No assistants found")
            return

        print(f"\n{'Name':<20} {'Version':<10} {'Model':<15} {'ID':<30}")
        print("=" * 85)
        for a in assistants:
            print(f"{a['name']:<20} {a['version']:<10} {a['model']:<15} {a['assistant_id']:<30}")
        print(f"\nTotal: {len(assistants)} assistants\n")

    elif args.command == "info":
        config = manager.get_assistant(args.name, args.version)
        if config:
            print(json.dumps(config, indent=2, ensure_ascii=False))
        else:
            print(f"Assistant {args.name}_{args.version} not found")

    elif args.command == "compare":
        comparison = manager.compare_versions(args.name, args.version1, args.version2)
        print(json.dumps(comparison, indent=2, ensure_ascii=False))

    elif args.command == "export":
        try:
            output_path = manager.export_assistant(args.name, args.version, args.output)
            print(f"✓ Exported to {output_path}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "import":
        try:
            config = manager.import_assistant(args.config_file, args.create_new)
            print(f"✓ Imported {config['name']}_{config['version']}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "delete":
        try:
            manager.delete_assistant(args.name, args.version, args.remote)
            print(f"✓ Deleted {args.name}_{args.version}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
