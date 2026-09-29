# Security

**Please do not open a public issue for a vulnerability.** Report it privately
through GitHub: the repository's **Security** tab → **Report a vulnerability**.
You should hear back within a week.

Worth knowing about what this project handles:

- It reads people's CVs. A CV, `profile.yaml`, and anything under `jobhunt/`
  or `runs/` must never be committed - `.gitignore`, a pre-commit hook and a CI
  job each refuse it. A way around all three is a security issue.
- It has no server and no API key. Skills run locally, inside the user's own
  coding agent.
- `install.sh` is piped to `sh` by people who will not read it first, so a bug
  in it that deletes or writes outside the skill folders is a security issue.
