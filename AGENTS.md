# Repository Guidelines

## Project Structure & Module Organization

This repository is currently empty apart from Git metadata. When adding the application, keep the layout predictable:

- `src/` for production source code.
- `tests/` for automated tests.
- `assets/` for static files such as images, icons, fixtures, or seed data.
- `docs/` for design notes, API notes, and contributor-facing documentation.

Keep modules small and grouped by feature or domain. Avoid placing implementation files in the repository root unless they are project-level entry points.

## Build, Test, and Development Commands

No build system or package manager has been configured yet. Add commands to the relevant manifest when the stack is chosen, then document them here. Typical examples:

- `npm install` or equivalent: install dependencies.
- `npm run dev`: start a local development server.
- `npm test`: run the test suite.
- `npm run build`: create a production build.

Prefer script names that are standard for the chosen ecosystem, and ensure they work from the repository root.

## Coding Style & Naming Conventions

Follow the conventions of the language and framework introduced into the project. Until tooling is added, use these defaults:

- Use consistent indentation within each language: 2 spaces for JavaScript/TypeScript, JSON, YAML, and Markdown; 4 spaces for Python.
- Name files descriptively, for example `task-service.ts`, `TaskList.tsx`, or `test_task_service.py`.
- Keep configuration files in the root only when they apply to the whole project.

Add a formatter and linter early, and expose them through commands such as `npm run format` and `npm run lint`.

## Testing Guidelines

Place tests under `tests/` or beside source files if the chosen framework prefers colocated tests. Use clear names that describe behavior, such as `task-service.test.ts` or `test_task_creation.py`.

Every new feature should include tests for expected behavior and important edge cases. Bug fixes should include a regression test when practical.

## Commit & Pull Request Guidelines

There is no existing commit history, so no repository-specific convention has been established. Use concise, imperative commit messages, for example:

- `Add task creation model`
- `Fix due date validation`

Pull requests should include a short summary, testing notes, and links to related issues. Add screenshots or screen recordings for user interface changes.

## Security & Configuration Tips

Do not commit secrets, local credentials, or generated environment files. Store local configuration in ignored files such as `.env.local`, and document required variables in `.env.example` when configuration is introduced.
