# Sistema de Agentes - Guia de uso

## Estructura de archivos

```
PROYECTO_BASE.md          Conocimiento compartido del proyecto
agentes/<nombre>.md       Estado vivo de cada agente
tareas/<session-id>.<task>.md  Specs de tareas realizadas
.opencode/agents/<nombre>.md   Definicion del agente
.opencode/commands/       Comandos disponibles
```

## Comandos disponibles

### $crear-agente
Crea un agente especializado en un area del proyecto.

```
$crear-agente
```

**Que hace:**
1. Si no existe `PROYECTO_BASE.md`, explora el proyecto y lo genera
2. Te pregunta: nombre del agente, area que cubre, archivos que custodia
3. Crea `.opencode/agents/<nombre>.md` con las instrucciones del agente
4. Crea `agentes/<nombre>.md` con su estado inicial
5. Guarda el session_id para poder retomar la sesion

**Uso tipico:**
```
$crear-agente
→ Nombre: pagos
→ Area: modulo de pagos y facturacion
→ Archivos: src/payments/, src/billing/
→ ... listo, cambia con Tab al agente pagos
```

### $tarea
Ejecuta una tarea de principio a fin.

```
$tarea "descripcion de la tarea"
```

**Que hace:**
1. Lee `PROYECTO_BASE.md` para contexto del proyecto
2. Te entrevista para definir requisitos (spec-driven)
3. Guarda el spec en `tareas/<session-id>.<task>.md`
4. Actualiza `agentes/<nombre>.md` con la tarea en curso
5. Crea un worktree aislado con su propio branch
6. Implementa los cambios dentro del worktree
7. Te muestra el diff y pide aprobacion
8. Si apruebas, mergea a main y limpia el worktree

**Uso tipico:**
```
$tarea "anadir soporte para PayPal en pagos"
→ Te hago unas preguntas para definir requisitos...
→ [entrevista spec-driven]
→ Creo worktree, implemento, te muestro diff...
→ Apruebas? → merge a main
```

### $estado
Muestra el estado actual de todos los agentes.

```
$estado
```

**Que hace:**
- Lista todos los agentes registrados en `agentes/`
- Muestra su area, estado y ultima tarea

**Uso tipico:**
```
$estado
| Agente   | Area             | Estado  | Ultima tarea              |
|----------|------------------|---------|---------------------------|
| pagos    | Modulo pagos     | activo  | Implementar PayPal        |
| dashboard| Analytics        | inactivo| ninguna                   |
```

## Flujo de trabajo recomendado

### Primera sesion
```
1. $crear-agente
   → Se genera PROYECTO_BASE.md (estructura, stack, convenciones)
   → Creas tu primer agente
2. $tarea "primera tarea"
   → Especificas, implementas, mergeas
```

### Sesiones siguientes
```
1. Cambia con Tab al agente que quieras usar
2. $tarea "nueva tarea"
   → El agente ya tiene contexto via PROYECTO_BASE.md
3. $estado para ver como van todos los agentes
```

### Crear mas agentes
```
$crear-agente
→ Como PROYECTO_BASE.md ya existe, lo usa como base
→ Cada agente nuevo se especializa en su area
→ Todos comparten el mismo conocimiento base
```

## Notas
- Los agentes comparten `PROYECTO_BASE.md` como fuente unica de verdad del proyecto
- Cada agente tiene su propia sesion y contexto que crece con el uso
- Usa Tab para cambiar entre agentes
- Los archivos en `agentes/` y `tareas/` son markdown legible
