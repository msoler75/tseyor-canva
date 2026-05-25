Ejecuta una tarea de principio a fin con especificacion previa.

## Antes de empezar
Lee PROYECTO_BASE.md si existe para contexto del proyecto.

## Flujo

### Fase 1: Especificacion
Usa skills/tarea-spec.md para entrevistarme hasta que los requisitos esten claros.
Haz una por una, no todas de golpe. Espera mi respuesta antes de continuar.

Cuando aprobemos el spec, guardalo en tareas/<session-id>.<task-id>.md. El session-id es el identificador unico de la sesion actual de opencode. El task-id es un slug corto descriptivo de la tarea. Asi puedes volver a esta sesion despues con opencode --session <session-id>.

Actualiza el estado del agente en agentes/<nombre-agente>.md si existe:
- Pon "ultima_tarea" con la descripcion de la tarea
- Pon "session_id" con el id de esta sesion

### Fase 2: Worktree
Crea un worktree aislado:
```bash
git branch tarea/<nombre-corto>
git worktree add ../tseyor-canva-<nombre-corto> tarea/<nombre-corto>
```

### Fase 3: Implementacion
Ejecuta la implementacion dentro del worktree. Usa el spec como guia.
Un cambio por vez. Despues de cada cambio, verifica que compile/typecheck.

### Fase 4: Revision
Muestrame el diff: `git diff main --stat` y `git diff main`
Preguntame si apruebo los cambios.

### Fase 5: Merge
Si apruebo:
```bash
git checkout main
git merge tarea/<nombre-corto>
git branch -d tarea/<nombre-corto>
git worktree remove ../tseyor-canva-<nombre-corto>
```

## Reglas
- No empieces a codificar sin mi aprobacion del spec
- Si encuentras algo no cubierto en el spec, preguntame
- Despues del merge, resumeme los cambios hechos
- Actualiza agentes/<nombre-agente>.md si existe reflejando que la tarea termino
