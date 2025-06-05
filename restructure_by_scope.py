
"""
Restructures CredData files into scope-based folders (/src/, /test/, etc.)
"""
import os
import shutil
from pathlib import Path

# From CredSweeper's ml_config.json
SCOPES = [
    "/src/",
    "/test/",
    "/conf/",
    "/script/",
    "/dist-packages/",
    "/site-packages/",
    "/example/",
    "/record/",
    "/tool/",
    "/usr/",
    "/assets/"
]

def get_scope(file_path: str) -> str:
    """Detect scope from path using POSIX formatting and exact substring matches."""
    posix_path = Path(file_path).as_posix().lower()
    for scope in SCOPES:
        if scope in posix_path:  
            return scope.strip("/")  
    return "other"

def restructure_dataset(input_dir: Path, output_dir: Path):
    """Reorganize files into scope-based folders."""
    for file_path in input_dir.glob("**/*"):
        if not file_path.is_file():
            continue

        
        project_name = file_path.relative_to(input_dir).parts[0]
        
        
        scope = get_scope(str(file_path))
        target_path = output_dir / project_name / scope / file_path.name

        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_path)  

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Raw dataset directory (e.g., ./raw_data)")
    parser.add_argument("--output", type=Path, required=True, help="Processed output directory (e.g., ./scoped_data)")
    args = parser.parse_args()
    restructure_dataset(args.input, args.output)
    