"""Install reviewable adoption examples without enabling remote integrations."""
from pathlib import Path

from .project import resource_root
from .errors import AtipSpecError


def scaffold(out: Path):
    if any(path.is_symlink() for path in (out, *out.parents)):
        raise AtipSpecError("Enterprise examples destination must not be a symlink")
    files = [(out / source.name, source.read_bytes()) for source in sorted((resource_root() / "enterprise").iterdir()) if source.is_file()]
    if any(path.exists() for path, _ in files):
        raise AtipSpecError("Enterprise examples already exist; use a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    for path, data in files:
        path.write_bytes(data)
    return [path for path, _ in files]
