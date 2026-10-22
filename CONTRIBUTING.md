# Contributing

Use this freely: the code is under the MIT No Attribution licence, so you do not need to credit anyone.

**Please improve it here rather than in your own copy.** One shared version stays tested on more projects, gets the fixes everyone finds, and saves you maintaining a fork. Forks are fine for trying things out; send what works back with a pull request.

## Ways to help

- **Found a bug or an odd number?** Open an issue with the "Bug report" template: what you ran, what you expected, the exact error text.
- **Have an idea?** Open an issue with the "Suggestion" template, or start a Discussion.
- **Got it working on a new project?** Tell us in Discussions what you set `SYSTEM_ATTRIBUTE` and `VIEWER_MODELS` to and what surprised you. That is how the guide gets better.
- **Fixed or built something?** Fork, make the change on a branch, open a pull request.

## Before opening a pull request

1. Run the tests: `py -m unittest discover tests` (all must pass). Add a test for new logic.
2. Keep it read only: no create, update or delete calls against Forma.
3. Standard library Python only (no new `pip` packages), so it keeps working on locked-down corporate PCs.
4. Update the docs you touched: `GETTING_STARTED.md` for anything a new user does, `docs/` for how it works, and `skill/` if the Claude skill should know.
5. **Never include secrets or project data**: no `.env`, tokens, client IDs or secrets, real project or account IDs, customer names, or files from `data/` and `dashboard/`. Use "Demo project A" style names in examples.

## Style

- Small, readable functions over clever code; the people using this are technical specialists, not full-time developers.
- British spelling in docs and UI text.
- One topic per pull request, with a short description of what changed and how you tested it.

## Reviews

Pull requests are reviewed by the maintainers when time allows. This is a side project, not an official Autodesk product, so there are no response-time promises.
