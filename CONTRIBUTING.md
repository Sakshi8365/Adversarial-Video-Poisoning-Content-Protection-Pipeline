# Contributing

Thanks for considering contributing to this project! Brief guidelines to make contributions fast and smooth.

1. Report issues
   - Search existing issues before opening a new one.
   - Provide reproducible steps, logs, and environment details.

2. Development workflow
   - Fork the repo and create feature branches from `main`.
   - Use descriptive commit messages (e.g., `feat(worker): add ffmpeg remux fallback`).
   - Keep changes small and focused; open a PR per logical change.

3. Tests
   - Add or update tests in `tests/` for any behavioral change.
   - Run `pytest` locally and ensure all tests pass before creating a PR.

4. Code style
   - Python: follow PEP8 (use `black`/`ruff` where helpful).
   - Keep function and variable names descriptive.

5. Documentation
   - Update `README.md` or add docs under `docs/` for user-facing changes.

6. Review checklist (quick)
   - [ ] Code builds and tests pass locally
   - [ ] Documentation updated (if applicable)
   - [ ] No secrets committed

If you need help or want to propose a large change, open an issue to discuss first.

Thank you — maintainers will review PRs as promptly as possible.
