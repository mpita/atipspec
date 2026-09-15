## Rules, every phase

- The spec is the truth and the contract is the law. If the code cannot meet a
  criterion, say so; spec.md changes only with the user's agreement. If a plan
  needs something the contract forbids, stop: it needs a decision, never a
  workaround.
- Never write into evidence/ or review.md. Never mark tasks done; commits do.
  Never set ready, accepted, verified or delivered by hand, and never run
  `atipspec accept`: the person runs it, `check` and `deliver` decide.
- Keep template headings and ID formats (REQ-001, AC-001, T1, F1, DEC-001);
  the CLI parses them. Write the content in the configured language, using
  the glossary's words.
- Ask the user only what changes the spec or the contract. Record the rest as
  open questions.
- Report real command output. If something did not run, say so. If a phase
  command refuses, tell the user what it asks for and stop; never work around it.
- End the phase with: delivery, `atipspec status <slug>`, what you produced,
  what `check` says, and the next action.
