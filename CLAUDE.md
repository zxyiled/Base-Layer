@AGENTS.md

## Claude Code

Las reglas del proyecto están en `AGENTS.md` (importado arriba). Esto es lo propio de Claude Code.

### Documentación con Codex

- Si el plugin `codex-plugin-cc` está disponible, delega la documentación al cerrar cada módulo con el subagente `codex:codex-rescue` (equivalente a `/codex:rescue --wait`): `Cierre del módulo <N>: actualiza docs/ según AGENTS.md (rol de documentación). No uses git.` Pásale el resultado de las pruebas y qué se implementó, y espera a que termine.
- Si no puedes invocarlo por tu cuenta, pídele a la persona que ejecute el comando. No actives el review gate del plugin.
- Revisa los cambios de Codex con `git diff --stat`: solo deben tocar `docs/` y `README.md`. Si Codex no logra escribir en `docs/`, repórtalo antes de seguir.
- Si el plugin no está instalado en tu entorno, aplica la regla de `AGENTS.md`: actualizas tú los docs de tu módulo.

### Commits

- Los haces tú, en la rama del módulo, con el formato de `AGENTS.md`. Puedes pedirle el borrador del mensaje al subagente `commit-reviewer` (en `.claude/agents/`), que no ejecuta el commit; en un repositorio nuevo no hay historial que imitar, así que el formato lo fija `AGENTS.md`.

### Skills y subagentes locales

- `api-design` (en `.claude/skills/`): úsala como apoyo para las convenciones REST; si algo choca con `AGENTS.md`, prevalece `AGENTS.md`. Sus ejemplos están en otros lenguajes: aplica las convenciones a Flask.
- `ui-ux-pro-max` y `frontend-slides` (en `.agents/skills/`): sigue la sección "Rol: Frontend y diapositivas" de `AGENTS.md`.
- `.claude/`, `.codex/` y `.agents/` son configuración local y no se versionan. Si algo de lo anterior no existe en tu entorno, ignóralo.