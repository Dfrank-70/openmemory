from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from tqdm import tqdm

from src.config.settings import get_logger, get_settings, slugify
from src.ingestors.register_project import register_project
from src.processing.digest_generator import generate_daily_digest, regenerate_index
from src.storage.rehydrate import rehydrate_index


def _load_projects(config_path: Path) -> list[dict]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return payload.get("projects", [])


def bootstrap_all(config_path: str, force: bool = False) -> dict[str, int]:
    settings = get_settings()
    logger = get_logger("bootstrap")
    projects = _load_projects(Path(config_path).expanduser().resolve())
    mapped = 0
    hooks = 0
    errors = 0
    for project in tqdm(projects, desc="Bootstrapping projects"):
        try:
            name = project["name"]
            scope = project.get("scope", "work")
            target_path = settings.project_dir(scope) / f"{slugify(name)}.md"
            if target_path.exists() and not force:
                continue
            register_project(name=name, repo_path=project["path"], scope=scope)
            mapped += 1
            hooks += 1
        except Exception as exc:
            errors += 1
            logger.warning("bootstrap_project_failed name=%s error=%s", project.get("name"), exc)
    generate_daily_digest()
    regenerate_index()
    rehydrate_index()
    return {"mapped": mapped, "hooks": hooks, "errors": errors}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap multiple existing projects")
    parser.add_argument("--config", default="projects.yaml")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = bootstrap_all(config_path=args.config, force=args.force)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
