# Sistema de Agentes — Guía de uso

## Estructura

```
PROYECTO_BASE.md          Conocimiento compartido del proyecto
agentes/<nombre>.md       Estado vivo de cada agente
tareas/<session-id>.<task>.md  Specs de tareas realizadas
.opencode/agents/<nombre>.md   Definición del agente
.opencode/commands/       Comandos disponibles
```

## Comandos

- `$crear-agente`: Crea agente especializado (explora proyecto, define área y archivos)
- `$tarea "descripción"`: Ejecuta tarea spec-driven con worktree aislado
- `$estado`: Muestra estado de todos los agentes

## Flujo

1. `$crear-agente` → genera PROYECTO_BASE.md + primer agente
2. `$tarea "algo"` → especifica, implementa, mergea
3. `$estado` para seguimiento
