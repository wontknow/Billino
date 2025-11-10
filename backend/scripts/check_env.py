#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import Dict, List, Tuple

BACKEND_ENV_REQUIRED = {
    "ENV": {
        "description": "Environment mode (development/production)",
        "allowed_values": ["development", "production"],
        "default": "development",
    },
    "LOG_LEVEL": {
        "description": "Logging level (DEBUG/INFO/WARNING/ERROR)",
        "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "default": "DEBUG",
    },
    "ALLOWED_ORIGINS": {
        "description": "Comma-separated CORS origins",
        "allowed_values": None,
        "default": "http://localhost:3000",
    },
}


def load_env_file(env_path: Path) -> Dict[str, str]:
    env_vars = {}
    if not env_path.exists():
        return env_vars
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


def validate_env_vars(
    env_vars: Dict[str, str], required: Dict[str, Dict], env_file: str
) -> Tuple[bool, List[str]]:
    issues = []
    for key, config in required.items():
        if key not in env_vars:
            issues.append(
                f"Missing {key} in {env_file}\nDescription: {config['description']}\nDefault: {config['default']}"
            )
            continue
        value = env_vars[key]
        allowed = config.get("allowed_values")
        if not value:
            issues.append(f"Variable {key} in {env_file} is empty")

        if allowed and value not in allowed:
            issues.append(
                f"Invalid value for {key} in {env_file}\nCurrent: {value}\nAllowed: {', '.join(allowed)}"
            )
        return len(issues) == 0, issues


def check_backend(repo_root: Path) -> bool:
    env_file = repo_root / ".env"
    if not env_file.exists():
        print(f"No .env file found at {env_file}")
        return False
    env_vars = load_env_file(env_file)
    is_valid, issues = validate_env_vars(env_vars, BACKEND_ENV_REQUIRED, ".env")
    if is_valid:
        print("All required variables are set correctly")
        return True
    for issue in issues:
        print(issue)
    return False


def main():
    repo_root = Path(__file__).parent.parent
    backend_ok = check_backend(repo_root)
    sys.exit(0 if backend_ok else 1)


if __name__ == "__main__":
    main()
