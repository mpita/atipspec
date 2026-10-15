"""Run the test modules in parallel processes, for runners where each test is slow.

On Windows every git and Python process costs a lot more to start than on
Linux, so the suite in one process does not fit in the CI job. Each module
runs in its own process; the output of a module that fails is printed whole.
"""
import argparse
import concurrent.futures
import locale
from pathlib import Path
import subprocess
import sys
import time


def run(root: Path, module: str) -> tuple[str, int, str, float]:
    start = time.monotonic()
    result = subprocess.run([sys.executable, "-m", "unittest", "-v", module], cwd=root, capture_output=True,
                            encoding=locale.getpreferredencoding(False), errors="replace")
    return module, result.returncode, result.stdout + result.stderr, time.monotonic() - start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=4, help="test modules run at the same time")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    modules = sorted(f"tests.{path.stem}" for path in (root / "tests").glob("test_*.py"))
    failed = []
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        for future in concurrent.futures.as_completed([pool.submit(run, root, module) for module in modules]):
            module, code, output, seconds = future.result()
            print(f"== {module}: {'ok' if code == 0 else 'FAILED'} in {seconds:.0f} s", flush=True)
            if code:
                failed.append(module)
                print(output, flush=True)
    print(f"{len(modules) - len(failed)} of {len(modules)} test modules passed"
          + (f"; failed: {', '.join(sorted(failed))}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
