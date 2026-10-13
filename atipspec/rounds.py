"""Review rounds of the guided flow, counted by the CLI.

`review_rounds` in config.yaml is how many reviews a delivery gets per
approved agreement, the first included: with 3, a first review and two of
corrected candidates. `atipspec review` counts a review whenever it writes a
packet for another candidate than the last packet's, whatever review.md says:
the reviewer writes that file, and the CLI cannot tell its verdicts from ones
edited afterwards. Regenerating a packet for the same candidate counts
nothing. Once the reviews are used and the candidate changed again, `review`
refuses, `check` reports it, and the human decides. `check` takes only a
review of the last packet counted, so a review written without `review`
counts no less. A new approved agreement (the guided proposal, or a legacy
spec) starts the count again; in a legacy delivery, a fix created before 0.3.0
included, that agreement leaves config.yaml out, so nothing approves the limit
itself.

The CLI writes review-rounds.json; the fingerprint leaves it out, so
writing it never makes evidence or a review stale. `accept <slug> proposal`
starts it for a guided delivery created since 0.3.0, so from then on a missing
file was deleted: `review` refuses and `check` reports it, and the human
decides. Without it in such a delivery approved under a trust policy, whose
count starts at the first packet, the review.md in the folder names the last
packet: the count starts again with that review as the first. In a delivery
created before 0.3.0 it starts at the next packet: a review.md written before
names a tree of the earlier fingerprint, never this candidate.
"""
from __future__ import annotations

import json

from .delivery import parse_review
from .errors import AtipSpecError
from .specs import load_spec
from .trust import SUBJECT_VERSION, read_regular, subject

FILE = "review-rounds.json"


def agreement(project, slug: str, version: int = SUBJECT_VERSION) -> str:
    """The approved agreement the count belongs to: the guided proposal's
    subject, or the spec's for legacy deliveries."""
    return subject(project, slug, "plan" if load_spec(project, slug).meta.get("schema") == 2 else "spec",
                   version=version)


def read(project, slug: str) -> dict:
    """The count for the current agreement; a new agreement starts at zero."""
    path = project.delivery_dir(slug) / FILE
    data = None
    if path.exists():
        try:
            data = json.loads(read_regular(path))
            if (not isinstance(data, dict) or data.get("schema") != 1 or data.get("delivery") != slug
                    or type(data.get("rounds")) is not int or data["rounds"] < 0):
                raise ValueError("invalid review rounds schema")
        except (ValueError, TypeError) as exc:
            raise AtipSpecError(f"Invalid {project.rel(path)}: {exc}") from exc
    # A count written without `subject_version` names its agreement with version 1.
    version = data.get("subject_version", 1) if data else SUBJECT_VERSION
    if data is None or version not in (1, SUBJECT_VERSION) or data.get("agreement") != agreement(project, slug, version):
        data = {"schema": 1, "delivery": slug, "agreement": agreement(project, slug), "subject_version": SUBJECT_VERSION,
                "rounds": 0, "packet_tree": None}
    return data


def used_up(project, slug: str, data: dict, tree: str | None) -> str | None:
    """Why the candidate `tree` may not be reviewed again: the agreement
    `data` counts for has used its reviews and `tree` is not the last
    packet's candidate. The text names the decision that falls to the human;
    None while it may be reviewed."""
    limit = int(project.policy("review_rounds"))
    if data["rounds"] < limit or not data["packet_tree"] or project.same_candidate(data["packet_tree"], tree):
        return None
    if load_spec(project, slug).meta.get("schema") == 2:
        change, raised = "the proposal", "the proposal is then approved again"
    else:
        change, raised = "the spec", "no approval covers it in a legacy delivery: raise it only on their word"
    return (f"review {data['rounds']} of {limit} was the last, and the candidate changed after it: stop and present "
            f"`atipspec check {slug}` to the user, with the findings that remain. They decide: change {change}, "
            f"raise review_rounds in .atipspec/config.yaml ({raised}) or stop the delivery")


def _write(project, slug: str, data: dict) -> None:
    path = project.delivery_dir(slug) / FILE
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AtipSpecError("Refusing a symlinked review rounds path")
    temporary = path.with_suffix(".json.tmp")
    if temporary.is_symlink():
        raise AtipSpecError("Refusing a symlinked review rounds temporary path")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def start(project, slug: str) -> None:
    """Begin the count where `accept <slug> proposal` records the agreement, so
    that a missing count shows; approving the same agreement again keeps it."""
    _write(project, slug, read(project, slug))


def missing(project, slug: str) -> str | None:
    """Why the count of a guided delivery is missing where `accept <slug>
    proposal` started it; None when it is there or was never started."""
    from .accept import read_record
    from .specs import baseline_sections
    if ((project.delivery_dir(slug) / FILE).exists() or read_record(project, slug, "proposal") is None
            or load_spec(project, slug).meta.get("schema") != 2 or not baseline_sections(project, slug)):
        return None
    return (f"the review round count is missing: `atipspec accept {slug} proposal` started "
            f"{project.rel(project.delivery_dir(slug) / FILE)} and only the CLI writes it; stop and present "
            f"`atipspec check {slug}` to the user. They decide: restore the file from git, or approve the proposal "
            "again, which starts a new count")


def open_round(project, slug: str, tree: str | None) -> tuple[int, int]:
    """Count the review a new packet for `tree` opens: (review, review_rounds).
    Raises PhaseRefused, counting nothing, when the reviews of this agreement
    are used up."""
    from .phases import PhaseRefused
    lost = missing(project, slug)
    if lost:
        raise PhaseRefused(lost)
    from .specs import baseline_sections
    data = read(project, slug)
    review_path = project.delivery_dir(slug) / "review.md"
    if (review_path.is_file() and not (project.delivery_dir(slug) / FILE).exists()
            and baseline_sections(project, slug)):
        # Without the record, the review in the folder names the last packet, the first counted.
        reviewed = parse_review(review_path.read_text(encoding="utf-8")).tree
        if reviewed:
            data["rounds"], data["packet_tree"] = 1, reviewed
    refusal = used_up(project, slug, data, tree)
    if refusal:
        raise PhaseRefused(refusal)
    if data["rounds"] == 0 or data["packet_tree"] != tree:
        data["rounds"] += 1
    data["packet_tree"] = tree
    _write(project, slug, data)
    return data["rounds"], int(project.policy("review_rounds"))


def describe(project, slug: str) -> str | None:
    """One line for `status <slug>`, or None before the first packet."""
    if not (project.delivery_dir(slug) / FILE).exists():
        return None
    data = read(project, slug)
    if data["packet_tree"] is None:
        return None
    return f"review {data['rounds']} of {int(project.policy('review_rounds'))}"
