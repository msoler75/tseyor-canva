Crea un agente especializado que hereda el conocimiento base del proyecto.

## Flujo

### Paso 1: Comprobar PROYECTO_BASE.md

Lee `PROYECTO_BASE.md` si existe. Contiene el conocimiento base del proyecto y un `session_id`.

**Si NO existe:**
- Preguntame que areas/funcionalidades cubre el proyecto
- Explora a fondo: estructura de carpetas, archivos clave, documentacion, tests, dependencias, package.json, convenciones
- Genera `PROYECTO_BASE.md` con este formato:

```markdown
# PROYECTO_BASE.md — <nombre-proyecto>

## session_id
<s-id-de-esta-sesion>

## Estructura del proyecto
<arbol de directorios>

## Stack tecnologico
<lenguajes, frameworks, librerias principales>

## Arquitectura
<patrones, estructura de modulos, flujo de datos>

## Convenciones
<naming, estilos, estructura de componentes, etc>

## Areas funcionales
<lista de modulos/areas que componen la app>

## Documentacion relevante
<enlaces a docs, archivos de especificacion, etc>

## Para cada area:
- Archivos principales
- Responsabilidades
- Dependencias con otras areas
```

- Guarda tu `session_id` actual en el campo `session_id`

### Paso 2: Crear el agente

Preguntame:
- Nombre del agente (ej: "pagos", "dashboard", "login")
- Que area o funcionalidad cubre (debe coincidir con alguna del PROYECTO_BASE.md)
- Si hay detalles adicionales que deba saber
- Modelo (o dejar default)

Genera `.opencode/agents/<nombre>.md`:

```yaml
---
description: Experto en <area>
mode: primary
---
Eres un agente especializado en <area> del proyecto.

Lee PROYECTO_BASE.md para contexto completo del proyecto.

## Tu area: <area>
<descripcion>

## Archivos que te pertenecen
<patrones de archivos>

## Reglas
- Trabaja SOLO en los archivos de tu area
- Si un cambio requiere tocar archivos fuera, detente y avisame
- Para contexto global, lee PROYECTO_BASE.md
- Sigue las convenciones del proyecto
```

### Paso 3: Fork desde la base (opcional, best-effort)

Si existe un `session_id` en `PROYECTO_BASE.md`, intenta:

```bash
opencode run --session <session-id> --fork --agent <nombre> "Eres experto en <area>. Usa PROYECTO_BASE.md como contexto."
```

Si el fork falla o no es posible, no pasa nada. El agente recien creado ya tiene `PROYECTO_BASE.md` como referencia.

### Paso 4: Registrar estado del agente

Crea `agentes/<nombre>.md` con el estado inicial:

```markdown
# Agente: <nombre>

## Area
<area que cubre>

## Estado
activo

## Creado
<fecha>

## Session ID
<session-id actual>

## Ultima tarea
<descripcion o "ninguna">

## Archivos que custodia
<lista de patrones>

## Notas
<informacion relevante>
```

### Paso 5: Cierre

Informame:
- El agente <nombre> esta creado en `.opencode/agents/<nombre>.md`
- Su estado esta en `agentes/<nombre>.md`
- Puedo cambiar a ese agente con Tab
- El agente debe leer PROYECTO_BASE.md al iniciar para contexto del proyecto
- El conocimiento base compartido esta en PROYECTO_BASE.md
