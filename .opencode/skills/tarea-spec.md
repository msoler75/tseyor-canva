# Metodología de especificación para tareas

Úsala cuando necesites definir requisitos antes de implementar. No avances de fase sin validación humana.

## Fases

### Fase 1: Spec
Antes de escribir código, haz preguntas hasta tener claros todos los requisitos:

1. **Objetivo** — ¿Qué hay que hacer y por qué? ¿Quién es el usuario? ¿Cómo sabemos que está terminado?
2. **Alcance** — ¿Qué archivos o módulos se modifican? ¿Hay dependencias con otras tareas?
3. **Restricciones** — ¿Algo que NO se deba hacer o tocar? ¿Estilo/convenciones del proyecto?
4. **Dudas** — Pregunta todo lo que no esté claro. No asumas nada.

Al empezar, lista siempre tus supuestos:
```markdown
SUPUESTOS:
1. ...
2. ...
→ Confírmalos o corrígeme antes de seguir.
```

### Fase 2: Plan técnico
Con el spec validado:
1. Componentes a modificar y dependencias
2. Orden de implementación
3. Riesgos

### Fase 3: Implementación
Ejecuta el plan en el worktree creado. Un cambio por vez, validando cada paso.

### Fase 4: Verificación
- ¿Tests pasan?
- ¿Cumple los criterios de éxito del spec?
- ¿Sin regresiones?
