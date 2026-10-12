# Contributing

This repository doesn't take contributions. The artifacts are meant to be taken into your
own project and changed there; that is how to use them, and nothing needs to come back here.

## Adapting an artifact

Copy what you need (see [Install](README.md#install)), then make it fit your project.

- **`unit-check`.** The `description` in `SKILL.md`'s frontmatter decides when the agent
  loads the skill, so rewrite it in your project's terms: the file formats and sources you
  read. The tests are in `tests/unit-check/` here, outside the skill folder. If you copy
  them, change the `SCRIPT` path at the top of the test file to where you put the skill.
  If you change the checker, confirm that the tests feeding it wrong units still fail.
- **`scidata-mcp`.** Write an adapter for your data source and keep the server as it is.
  [`mcp/README.md`](mcp/README.md#make-it-yours) covers how, and its conformance suite
  checks your version through the protocol, whatever language you write it in.
- **Cynicχl.** Edit the prompt for the failures common in your field, and make the same edit
  in all three copies (`cynic-kyle.md`, `cynic-kyle.toml`, and the skill's
  `references/prompt.md`): `tests/cynic-kyle/` fails if they differ. Run the
  [demos](agents/cynic-kyle/demos/) before and after. If the edited agent misses the flaw in
  demo 1, or invents problems in demo 2, the edit made it worse.
- **`AGENTS.md`.** Fill the slots and delete what doesn't apply, as
  [`agents-md/README.md`](agents-md/README.md#using-the-template) describes.

## Reporting a problem

Open an issue on GitHub. Say what you ran, which tool and version, what you expected, and
what happened. For the skill or the subagent, include what you asked the agent and what it
did, since a model's behavior varies from run to run.

Issues are read until the repository is archived after April 2027; fixes aren't promised.
