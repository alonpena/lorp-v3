from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Wait for batch CSV to be ready, then run plot_batch_results.py once.")
    p.add_argument("--csv", default="pipeline_out/fsd_batch_results_with_stats.csv")
    p.add_argument("--out-dir", default="pipeline_out/plots")
    p.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds.")
    p.add_argument("--stable-checks", type=int, default=2, help="Consecutive unchanged size checks before running.")
    p.add_argument("--timeout", type=float, default=0.0, help="Seconds. 0 = wait forever.")
    p.add_argument("--gap-threshold", type=float, default=0.20)
    return p.parse_args()


def wait_until_ready(path: Path, interval: float, stable_checks: int, timeout: float) -> None:
    start = time.monotonic()
    last_size: int | None = None
    stable = 0

    print(f"watching: {path}")
    print(f"poll every {interval}s | stable checks={stable_checks} | timeout={'∞' if timeout == 0 else timeout}")

    while True:
        if timeout and time.monotonic() - start > timeout:
            raise TimeoutError(f"Timed out waiting for {path}")

        if not path.exists():
            print(f"waiting: file missing: {path}")
            time.sleep(interval)
            continue

        size = path.stat().st_size
        if size <= 0:
            print(f"waiting: file exists but empty: size={size}")
            last_size = size
            stable = 0
            time.sleep(interval)
            continue

        if last_size == size:
            stable += 1
            print(f"stable check {stable}/{stable_checks}: size={size}")
        else:
            stable = 0
            print(f"size changed: {last_size} -> {size}")

        last_size = size
        if stable >= stable_checks:
            print(f"ready: {path} size={size}")
            return

        time.sleep(interval)


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    wait_until_ready(csv_path, args.interval, args.stable_checks, args.timeout)

    cmd = [
        sys.executable,
        "plot_batch_results.py",
        "--csv", str(csv_path),
        "--out-dir", args.out_dir,
        "--gap-threshold", str(args.gap_threshold),
    ]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("done")


if __name__ == "__main__":
    main()
