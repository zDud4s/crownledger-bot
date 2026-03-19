from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from app.update_installer import launch_updated_app, wait_for_directory_update


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--launch-path", required=True)
    parser.add_argument("--python-exe")
    parser.add_argument("--wait-seconds", type=float, default=2.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    time.sleep(max(0.0, args.wait_seconds))
    wait_for_directory_update(args.source_dir, args.target_dir)
    launch_updated_app(args.launch_path, python_exe=args.python_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
