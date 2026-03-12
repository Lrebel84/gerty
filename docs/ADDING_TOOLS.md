# Adding a New Tool or Skill

When you add a new tool to Gerty, update these files so it appears in the Skills UI and docs:

1. **`gerty/main.py`** – Register the tool with `executor.register(YourTool())`
2. **`gerty/llm/router.py`** – Add intent keywords and routing (if needed)
3. **`gerty/tools/skills_registry.py`** – Add entry to `SKILLS` list
4. **`frontend/src/skills.ts`** – Add the same entry (UI uses this for instant load)
5. **`COMMANDS.md`** – Add full examples and usage

The Skills overlay in the app reads from `frontend/src/skills.ts`. Keep it in sync with `skills_registry.py`.
