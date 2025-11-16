# Translation Assistant Manager - Systematic Approach

**Purpose**: Manage OpenAI assistants for multi-stage Chinese novel translation with versioning, reusability, and systematic testing.

---

## Problem Statement

**Current Approach (Trial & Error)**:
- Assistant IDs hardcoded in `translate_novel.py`
- No versioning of instructions or schemas
- Difficult to A/B test different translation approaches
- Hard to share configurations across projects
- No easy way to rollback to previous assistant versions

**Improved Approach (Systematic Management)**:
- Store assistant definitions locally as JSON
- Version control instructions and schemas
- Easy testing and comparison
- Reusable across projects
- Simple rollback and experimentation

---

## Architecture for Translation

```
novel_structure/
├── .assistants/                           # Local assistant storage
│   ├── translate_v1.json                  # Stage 1: Translation
│   ├── translate_v2.json                  # Stage 1: Updated version
│   ├── markdown_formatter_v1.json         # Stage 2: Markdown
│   └── cleanup_v1.json                    # Stage 3: Cleanup
│
├── assistant_configs/                     # Configuration templates
│   ├── instructions/
│   │   ├── translation_v2.md             # Your current instructions
│   │   ├── translation_v3.md             # Next iteration
│   │   ├── markdown_formatter.md
│   │   └── cleanup.md
│   │
│   └── schemas/
│       ├── translation_schema.json
│       └── markdown_schema.json
│
├── translation_assistant_manager.py       # New manager class
└── translate_novel.py                     # Updated pipeline (uses manager)
```

---

## Implementation Plan

### Step 1: Create Translation Assistant Manager

**File**: `translation_assistant_manager.py`

```python
#!/usr/bin/env python3
"""
Translation Assistant Manager
Manages OpenAI assistants for Chinese novel translation pipeline
"""

import os
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI


class TranslationAssistantManager:
    """Manages translation assistants with local persistence"""

    def __init__(self, storage_dir=".assistants", api_key=None):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def create_assistant(self, name, instructions, description,
                        schema=None, model="gpt-4.1-nano", version="v1"):
        """
        Create new translation assistant and store config locally.

        Args:
            name: Assistant name (e.g., "translate", "markdown", "cleanup")
            instructions: Full instructions text or path to .md file
            description: Human-readable description
            schema: JSON schema for structured output (optional)
            model: OpenAI model to use
            version: Version tag (e.g., "v1", "v2")

        Returns:
            dict: Assistant configuration
        """
        # Load instructions from file if it's a path
        if isinstance(instructions, str) and instructions.endswith('.md'):
            with open(instructions, 'r', encoding='utf-8') as f:
                instructions = f.read()

        # Create assistant via OpenAI API
        assistant_params = {
            "name": f"{name}_{version}",
            "instructions": instructions,
            "model": model,
            "description": description
        }

        # Add JSON response format if schema provided
        if schema:
            assistant_params["response_format"] = {"type": "json_object"}

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
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self._save_config(f"{name}_{version}", config)

        return config

    def get_assistant(self, name, version="latest"):
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
                return None
            version = versions[-1]

        path = self.storage_dir / f"{name}_{version}.json"

        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_assistants(self, name_filter=None):
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

    def compare_versions(self, name, version1, version2):
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
                "v1": {"id": config1["assistant_id"], "model": config1["model"]},
                "v2": {"id": config2["assistant_id"], "model": config2["model"]}
            },
            "instructions_changed": config1["instructions"] != config2["instructions"],
            "schema_changed": config1.get("schema") != config2.get("schema"),
            "model_changed": config1["model"] != config2["model"]
        }

    def export_assistant(self, name, version, output_file):
        """Export assistant config to file for sharing"""
        config = self.get_assistant(name, version)
        if not config:
            raise ValueError(f"Assistant {name}_{version} not found")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return output_file

    def import_assistant(self, config_file, create_new=True):
        """
        Import assistant config from file.

        Args:
            config_file: Path to JSON config
            create_new: If True, create new assistant via API

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
                version=config["version"]
            )
            return new_config
        else:
            # Just save config locally (reuse existing assistant_id)
            self._save_config(f"{config['name']}_{config['version']}", config)
            return config

    def delete_assistant(self, name, version, delete_remote=False):
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
            except Exception as e:
                print(f"Warning: Could not delete remote assistant: {e}")

        # Delete local config
        path = self.storage_dir / f"{name}_{version}.json"
        if path.exists():
            path.unlink()

    def _save_config(self, key, config):
        """Save configuration to local storage"""
        path = self.storage_dir / f"{key}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _get_versions(self, name):
        """Get all versions for a given assistant name"""
        versions = []
        for path in self.storage_dir.glob(f"{name}_*.json"):
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                versions.append(config["version"])
        return sorted(versions)


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python translation_assistant_manager.py list")
        print("  python translation_assistant_manager.py info <name> [version]")
        print("  python translation_assistant_manager.py compare <name> <v1> <v2>")
        print("  python translation_assistant_manager.py export <name> <version> <file>")
        print("  python translation_assistant_manager.py import <file>")
        sys.exit(1)

    manager = TranslationAssistantManager()
    command = sys.argv[1]

    if command == "list":
        assistants = manager.list_assistants()
        for a in assistants:
            print(f"{a['name']}_{a['version']}: {a['description']}")
            print(f"  ID: {a['assistant_id']}")
            print(f"  Model: {a['model']}")
            print()

    elif command == "info":
        name = sys.argv[2]
        version = sys.argv[3] if len(sys.argv) > 3 else "latest"
        config = manager.get_assistant(name, version)
        if config:
            print(json.dumps(config, indent=2, ensure_ascii=False))
        else:
            print(f"Assistant {name}_{version} not found")

    elif command == "compare":
        name = sys.argv[2]
        v1 = sys.argv[3]
        v2 = sys.argv[4]
        comparison = manager.compare_versions(name, v1, v2)
        print(json.dumps(comparison, indent=2))

    elif command == "export":
        name = sys.argv[2]
        version = sys.argv[3]
        output = sys.argv[4]
        manager.export_assistant(name, version, output)
        print(f"Exported to {output}")

    elif command == "import":
        config_file = sys.argv[2]
        config = manager.import_assistant(config_file, create_new=False)
        print(f"Imported {config['name']}_{config['version']}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
```

---

### Step 2: Create Assistant Configurations

**Directory structure**:
```
assistant_configs/
├── instructions/
│   ├── translation_v2.md      (your existing file)
│   ├── markdown_formatter.md  (create this)
│   └── cleanup.md              (create this)
└── schemas/
    ├── translation_schema.json
    └── markdown_schema.json
```

**Example: `assistant_configs/schemas/translation_schema.json`**

```json
{
  "type": "object",
  "description": "Translation output with footnotes",
  "properties": {
    "annotated_content_text": {
      "type": "string",
      "description": "Translated English text with inline footnote markers [1], [2], etc."
    },
    "content_footnotes": {
      "type": "array",
      "description": "Array of footnotes for this content block",
      "items": {
        "type": "object",
        "properties": {
          "footnote_key": {"type": "integer"},
          "footnote_ideogram": {"type": "string"},
          "footnote_pinyin": {"type": "string"},
          "footnote_text": {"type": "string"},
          "footnote_person_flag": {"type": "integer"}
        },
        "required": ["footnote_key", "footnote_ideogram", "footnote_pinyin", "footnote_text", "footnote_person_flag"]
      }
    }
  },
  "required": ["annotated_content_text", "content_footnotes"]
}
```

---

### Step 3: Setup Script

**File**: `setup_translation_assistants.py`

```python
#!/usr/bin/env python3
"""
Setup script for creating/updating translation assistants
Run this to initialize or update your translation pipeline assistants
"""

from translation_assistant_manager import TranslationAssistantManager
import json

def load_schema(schema_path):
    """Load JSON schema from file"""
    with open(schema_path, 'r') as f:
        return json.load(f)

def main():
    manager = TranslationAssistantManager()

    # Stage 1: Translation + Annotation
    print("Creating Translation Assistant (v2)...")
    translate_config = manager.create_assistant(
        name="translate",
        instructions="assistant_configs/instructions/translation_v2.md",
        description="Stage 1: Chinese to English translation with Pinyin footnotes",
        schema=load_schema("assistant_configs/schemas/translation_schema.json"),
        model="gpt-4o",  # Use GPT-4 for translation quality
        version="v2"
    )
    print(f"  Created: {translate_config['assistant_id']}")

    # Stage 2: Markdown Formatting
    print("\nCreating Markdown Formatter (v1)...")
    markdown_config = manager.create_assistant(
        name="markdown",
        instructions="assistant_configs/instructions/markdown_formatter.md",
        description="Stage 2: Format translated text as Chicago-style markdown",
        schema=load_schema("assistant_configs/schemas/markdown_schema.json"),
        model="gpt-4.1-nano",  # Cheaper for formatting
        version="v1"
    )
    print(f"  Created: {markdown_config['assistant_id']}")

    # Stage 3: Cleanup
    print("\nCreating Cleanup Assistant (v1)...")
    cleanup_config = manager.create_assistant(
        name="cleanup",
        instructions="assistant_configs/instructions/cleanup.md",
        description="Stage 3: Final grammar and punctuation cleanup",
        model="gpt-4.1-nano",
        version="v1"
    )
    print(f"  Created: {cleanup_config['assistant_id']}")

    print("\n" + "="*60)
    print("Translation pipeline assistants created!")
    print("="*60)
    print("\nSummary:")
    print(f"  translate_v2: {translate_config['assistant_id']}")
    print(f"  markdown_v1:  {markdown_config['assistant_id']}")
    print(f"  cleanup_v1:   {cleanup_config['assistant_id']}")
    print("\nNext steps:")
    print("  1. Update translate_novel.py to use these assistant IDs")
    print("  2. Or use the manager to load assistants dynamically")
    print("  3. Run: python translation_assistant_manager.py list")

if __name__ == "__main__":
    main()
```

---

### Step 4: Update translate_novel.py

**Replace hardcoded IDs with manager**:

```python
# OLD APPROACH (lines 38-40 in translate_novel.py):
ASSISTANT_TRANSLATE = "asst_GUQIoTYjiHPYpJi2x2GT813g"
ASSISTANT_MARKDOWN = "asst_PBHY0gzD5pGB0uWUnZFsjBLD"
ASSISTANT_CLEANUP = "asst_f32tcEkaOvkJOfSJ8ds0MzQm"

# NEW APPROACH:
from translation_assistant_manager import TranslationAssistantManager

# Initialize assistant manager
assistant_mgr = TranslationAssistantManager()

# Load assistants dynamically (uses latest versions)
translate_config = assistant_mgr.get_assistant("translate")
markdown_config = assistant_mgr.get_assistant("markdown")
cleanup_config = assistant_mgr.get_assistant("cleanup")

ASSISTANT_TRANSLATE = translate_config["assistant_id"]
ASSISTANT_MARKDOWN = markdown_config["assistant_id"]
ASSISTANT_CLEANUP = cleanup_config["assistant_id"]
```

---

## Workflow Examples

### Example 1: Create New Translation Assistant Version

```bash
# Step 1: Edit instructions
nano assistant_configs/instructions/translation_v3.md

# Step 2: Create new assistant
python setup_translation_assistants.py

# Step 3: Test with small sample
python translate_novel.py --input sample.json --output test_v3.json

# Step 4: Compare with previous version
python translation_assistant_manager.py compare translate v2 v3
```

### Example 2: A/B Testing Different Approaches

```python
# test_ab_comparison.py
from translation_assistant_manager import TranslationAssistantManager

manager = TranslationAssistantManager()

# Load both versions
v2_config = manager.get_assistant("translate", "v2")
v3_config = manager.get_assistant("translate", "v3")

# Test same content with both
test_content = "帝乙游於御園，領眾文武玩賞牡丹。"

result_v2 = process_with_assistant(v2_config["assistant_id"], test_content)
result_v3 = process_with_assistant(v3_config["assistant_id"], test_content)

print("Version 2:")
print(result_v2)
print("\nVersion 3:")
print(result_v3)
```

### Example 3: Rollback to Previous Version

```python
# If new version isn't working well, rollback
manager = TranslationAssistantManager()

# Update translate_novel.py to use v2 instead of latest
old_config = manager.get_assistant("translate", "v2")
print(f"Rollback to: {old_config['assistant_id']}")
```

### Example 4: Share Configuration with Team

```bash
# Export your working configuration
python translation_assistant_manager.py export translate v2 translate_v2_config.json

# Share translate_v2_config.json with team
# Team member imports (without creating new assistant):
python translation_assistant_manager.py import translate_v2_config.json
```

---

## Best Practices for Translation Assistants

### 1. Versioning Strategy

```
v1 - Initial version
v2 - Current instructions (assistant_instructions_translation_v2.md)
v3 - Experimental changes
v4 - Production-ready improvements
```

### 2. Testing Before Deployment

Always test new versions on sample content:

```python
# test_assistant_version.py
import json
from openai import OpenAI

def test_assistant(assistant_id, test_cases):
    """Test assistant with sample inputs"""
    client = OpenAI()
    results = []

    for i, test_input in enumerate(test_cases):
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_input
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            results.append({
                "input": test_input,
                "output": response,
                "success": True
            })
        else:
            results.append({
                "input": test_input,
                "error": run.last_error,
                "success": False
            })

    return results

# Usage
test_cases = [
    "帝乙游於御園，領眾文武玩賞牡丹。",
    "紂王乃帝乙之三子也。",
    "子牙出世人中仙，終日垂絲釣人主"
]

manager = TranslationAssistantManager()
config = manager.get_assistant("translate", "v3")
results = test_assistant(config["assistant_id"], test_cases)

print(json.dumps(results, indent=2, ensure_ascii=False))
```

### 3. Document Changes in Metadata

When creating new versions, document what changed:

```python
config = manager.create_assistant(
    name="translate",
    instructions="assistant_configs/instructions/translation_v3.md",
    description="Stage 1: Translation with improved dialogue formatting (v3 changes: better line breaks)",
    version="v3"
)
```

### 4. Backup Before Major Changes

```bash
# Backup current working assistants
python translation_assistant_manager.py export translate v2 backups/translate_v2_$(date +%Y%m%d).json
python translation_assistant_manager.py export markdown v1 backups/markdown_v1_$(date +%Y%m%d).json
python translation_assistant_manager.py export cleanup v1 backups/cleanup_v1_$(date +%Y%m%d).json
```

---

## Migration from Current Setup

### Step 1: Initialize Manager with Current Assistants

```python
# migrate_existing_assistants.py
from translation_assistant_manager import TranslationAssistantManager

manager = TranslationAssistantManager()

# Import your existing assistant configurations
# (without creating new ones, just store locally)
existing_assistants = [
    {
        "assistant_id": "asst_GUQIoTYjiHPYpJi2x2GT813g",
        "name": "translate",
        "version": "v2",
        "description": "Current translation assistant",
        "instructions": open("assistant_instructions_translation_v2.md").read(),
        "model": "gpt-4o"
    },
    # Add others...
]

for config in existing_assistants:
    manager._save_config(
        f"{config['name']}_{config['version']}",
        {**config, "created_at": "2025-10-19", "updated_at": "2025-10-19"}
    )

print("Migration complete!")
```

### Step 2: Update Your Workflow

Before:
```bash
# Edit assistant_instructions_translation_v2.md
# Manually update assistant via OpenAI Dashboard
# Update ASSISTANT_TRANSLATE ID in translate_novel.py
# Run translation
```

After:
```bash
# Edit assistant_configs/instructions/translation_v3.md
python setup_translation_assistants.py  # Creates v3
python translate_novel.py --assistant-version v3  # Test
python translation_assistant_manager.py compare translate v2 v3  # Compare
# If good: update default version in translate_novel.py
```

---

## Summary: Key Improvements

| Aspect | Old Approach | New Approach |
|--------|-------------|--------------|
| **Versioning** | Manual, no history | Automatic, version tags |
| **Testing** | Trial and error on full book | Test samples before deployment |
| **Rollback** | Difficult, need to recreate | Simple, just use old version |
| **Collaboration** | Share IDs manually | Export/import JSON configs |
| **Documentation** | External notes | Built into config metadata |
| **Comparison** | Manual diff of instructions | Built-in comparison tool |

**Next Steps**:
1. Create `translation_assistant_manager.py`
2. Run `setup_translation_assistants.py` to initialize
3. Update `translate_novel.py` to use manager
4. Create test suite for validation
5. Start using versioned workflow
