---
description: Kinderbuch-Pipeline — nach Rohdaten-Handoff kindgerechtes Ersatzwort, Erklärung und Quelle (nur aus dem übergebenen Block).
mode: subagent
prompt: "{file:../../scripts/AGENT_PROMPT.md}"
permission:
  bash:
    "*": deny
  edit: deny
  webfetch: deny
  task:
    "*": deny
---
