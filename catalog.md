# Catalog

Each artifact here is a working instance of one or more patterns from the
[Scientific Agentic Engineering framework](https://vweeks.github.io/scientific-agentic-engineering/framework/).
The stage is the part of [the workflow](https://vweeks.github.io/scientific-agentic-engineering/framework/the-loop/)
where it does its work: frame, plan and critique, implement, or verify.

| Artifact | Kind | Stage | Pattern | Failure it helps catch |
|---|---|---|---|---|
| [`unit-check`](skills/unit-check/) | skill | implement, verify | [Ask the real thing](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#ask-the-real-thing), [Refuse to call complete](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#refuse-to-call-complete) | Code that converts or combines quantities using units it assumed instead of the units the data declares. |
| [`scidata-mcp`](mcp/) | MCP server template | implement, verify | [Ask the real thing](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#ask-the-real-thing) | An agent answering from memory about what a dataset contains: its units, its calendar, its values. |
| [Cynicχl](agents/cynic-kyle/) (`cynic-kyle`) | subagent | plan and critique, verify | [Fresh-eyes critique](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#fresh-eyes-critique) | A plan or result accepted because nothing in the session tried to break it. |
| [`AGENTS.md` template](agents-md/) | project instruction file | all stages | [Decide the gates in advance](https://vweeks.github.io/scientific-agentic-engineering/framework/patterns/#decide-the-gates-in-advance) and others; its README maps each section to its pattern | An agent filling gaps in a project's standing rules with plausible defaults. |

## Related collections

Other open collections in the same formats:

- [`anthropics/skills`](https://github.com/anthropics/skills): Anthropic's skills repository.
  The `unit-check` folder follows its layout.
- [Agent Skills](https://agentskills.io): the specification for the skill format.
- [`BootLoops-ai/skills`](https://github.com/BootLoops-ai/skills): skills and plugins for
  quantitative scientific work with AI agents.
