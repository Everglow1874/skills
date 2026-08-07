#!/usr/bin/env python3
"""
Package a skill into a .skill file for distribution.

This script takes a skill directory and creates a compressed .skill file
that can be easily shared and installed.
"""

import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Any


def create_skill_package(skill_dir: Path, output_path: Path = None) -> Path:
    """
    Create a .skill package from a skill directory.
    
    Args:
        skill_dir: Path to the skill directory
        output_path: Optional output path for the .skill file
    
    Returns:
        Path to the created .skill file
    """
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
    
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")
    
    # Determine output path
    if output_path is None:
        output_path = skill_dir.parent / f"{skill_dir.name}.skill"
    
    # Create the .skill file (which is a ZIP file)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add SKILL.md first (required)
        zf.write(skill_md_path, "SKILL.md")
        
        # Add all other files in the skill directory
        for item in skill_dir.rglob("*"):
            if item.is_file() and item != skill_md_path:
                # Calculate relative path from skill directory
                rel_path = item.relative_to(skill_dir)
                zf.write(item, rel_path)
    
    return output_path


def validate_skill(skill_dir: Path) -> List[str]:
    """
    Validate a skill directory for common issues.
    
    Args:
        skill_dir: Path to the skill directory
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check for SKILL.md
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        errors.append("SKILL.md not found")
        return errors
    
    # Read and parse SKILL.md
    try:
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for YAML frontmatter
        if not content.startswith("---"):
            errors.append("SKILL.md must start with YAML frontmatter (---)")
        else:
            # Find the end of frontmatter
            end_idx = content.find("---", 3)
            if end_idx == -1:
                errors.append("YAML frontmatter not properly closed")
            else:
                frontmatter = content[3:end_idx].strip()
                
                # Check for required fields
                if "name:" not in frontmatter:
                    errors.append("YAML frontmatter must contain 'name' field")
                if "description:" not in frontmatter:
                    errors.append("YAML frontmatter must contain 'description' field")
        
        # Check for empty content
        if len(content.strip()) < 50:
            errors.append("SKILL.md content is too short")
    
    except Exception as e:
        errors.append(f"Error reading SKILL.md: {str(e)}")
    
    # Check directory structure
    required_dirs = ["scripts", "references", "assets", "agents"]
    for dir_name in required_dirs:
        dir_path = skill_dir / dir_name
        if dir_path.exists() and not any(dir_path.iterdir()):
            errors.append(f"Directory '{dir_name}' exists but is empty")
    
    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.package_skill <skill_dir> [--output <output_path>]")
        sys.exit(1)
    
    skill_dir = Path(sys.argv[1])
    output_path = None
    
    # Parse optional output path
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])
    
    # Validate skill
    print(f"Validating skill: {skill_dir}")
    errors = validate_skill(skill_dir)
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("Validation passed!")
    
    # Create package
    try:
        package_path = create_skill_package(skill_dir, output_path)
        print(f"Created skill package: {package_path}")
        print(f"Package size: {package_path.stat().st_size / 1024:.2f} KB")
    except Exception as e:
        print(f"Error creating package: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
