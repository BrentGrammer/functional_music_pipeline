# System Instructions

- Do not be verbose. Communicate the most important information in as concise a manner as possible.

## Usage of MCP tooling

### Exa MCP

If Exa is installed and available: Use Exa only when the task depends on current external information: library/API docs, migration guides, recent errors, package behavior, or official examples.

Before using Exa, inspect the local project first for dependency versions and relevant files such as package.json, lockfiles, pyproject.toml, go.mod, README, and local docs. Match Exa results to the installed version whenever possible.

Prefer official documentation, release notes, changelogs, and upstream GitHub issues. Avoid random blogs unless official sources are insufficient.

Do not use Exa for local codebase questions, file search, refactoring, or understanding project structure. Use local files, grep/search, tests, and language-server/code tools for that.

If current web docs conflict with this project’s pinned dependency versions or local docs, prioritize the project’s pinned versions and local docs.

After using Exa, briefly state what source/version you relied on, then make the smallest safe code change.

### Serena MCP

Use Serena for local codebase understanding, symbol navigation, finding references, and planning refactors.

Use Serena before broad manual searching when the task asks things like:

- where is this implemented?
- how does this feature work?
- find related code
- trace this flow
- refactor safely
- find references or definitions

Do not use Serena for simple one-file edits when the relevant file is already known.
