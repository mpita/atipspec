"""JUnit XML reports: the interchange format every test framework can emit,
read here to bind acceptance criteria to the tests that actually ran.

Only `testcase` elements are used: an id built from classname and name, and a
status derived from the child elements (failure, error, skipped)."""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ElementTree

from .errors import AtipSpecError

MAX_REPORT_BYTES = 16_000_000


def read_report(path: Path) -> list[dict]:
    """Test cases of one JUnit XML file: [{id, name, classname, status}]."""
    if not path.is_file():
        raise AtipSpecError(f"test report not found: {path}")
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise AtipSpecError(f"test report larger than {MAX_REPORT_BYTES} bytes: {path}")
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise AtipSpecError(f"test report is not valid XML: {path}: {exc}") from exc
    cases = []
    for case in root.iter("testcase"):
        name = (case.get("name") or "").strip()
        classname = (case.get("classname") or "").strip()
        if not name:
            continue
        tags = {child.tag for child in case}
        status = "failed" if tags & {"failure", "error"} else "skipped" if "skipped" in tags else "passed"
        cases.append({"id": f"{classname}.{name}" if classname else name, "name": name,
                      "classname": classname, "status": status})
    return cases


def matches(proof: str, case: dict) -> bool:
    """Whether a Proof entry names this test case: the full id, the bare name,
    a dotted suffix, `Class::name`, or `path/to/file.py::name`."""
    proof = proof.strip()
    name, classname, ident = case["name"], case["classname"], case["id"]
    if proof in (name, ident, f"{classname}::{name}"):
        return True
    if ident.endswith("." + proof):
        return True
    if "::" in proof and classname:
        module, _, rest = proof.partition("::")
        module = module.removesuffix(".py").replace("/", ".").replace("\\", ".")
        candidate = f"{module}.{rest.replace('::', '.')}"
        return candidate == ident or ident.endswith("." + candidate)
    return False


def recorded_cases(data: dict) -> list[dict]:
    """The test cases an evidence record carries, in the shape `matches` expects."""
    cases = []
    for case in data.get("tests") or []:
        if not isinstance(case, dict):
            continue
        ident = str(case.get("id", ""))
        name = str(case.get("name") or ident.rsplit(".", 1)[-1])
        classname = str(case.get("classname") if case.get("classname") is not None
                        else (ident[: -len(name) - 1] if ident.endswith("." + name) else ""))
        cases.append({"id": ident, "name": name, "classname": classname, "status": case.get("status")})
    return cases


def find(proof: str, cases: list[dict]) -> dict | None:
    for case in cases:
        if matches(proof, case):
            return case
    return None
