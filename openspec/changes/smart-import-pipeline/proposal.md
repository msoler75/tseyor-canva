# Proposal: Smart Import Calibration Pipeline

## Intent

Crear una infraestructura **independiente de la app actual** que permita:
1. Procesar un dataset de 7 imágenes mediante el pipeline de "importación inteligente" (visión IA → SceneGraph → compilador → .tc)
2. Renderizar los .tc resultantes a imágenes sin pasar por la UI
3. Evaluar automáticamente con un modelo juez de alta gama la calidad de cada importación
4. Iterar prompts/parámetros hasta calibrar el pipeline

El objetivo final es tener un pipeline validado y perfectamente calibrado antes de incorporarlo a la app Tseyor Canva.

## Scope

### In Scope
- Script autónomo que carga .env, llama a OpenRouter con modelo visión y genera SceneGraph
- Schema SceneGraph + validador JSON
- Compilador SceneGraph → .tc v2 (determinista, sin IA)
- Headless renderer: .tc → screenshot usando la app desde CLI (Puppeteer/Playwright)
- Evaluador automático: modelo juez compara original vs render y devuelve score estructurado
- Dataset fixture de 7 imágenes representativas
- Dashboard de resultados: tabla comparativa por modelo/imagen con scores y costes

### Out of Scope
- Integración del pipeline en la UI de Tseyor Canva (futuro)
- Extracción/inpainting de fotos con oclusión (futuro, rama avanzada)
- Segmentación semántica / background removal
- UI web de benchmark
- CI/CD del pipeline de calibración

## Capabilities

### New Capabilities
- `smart-import-pipeline`: Pipeline autónomo que transforma imagen → SceneGraph → .tc mediante modelos OpenRouter
- `tc-headless-renderer`: Renderizado de archivos .tc a imágenes PNG sin interfaz gráfica
- `import-quality-evaluator`: Evaluación automática de calidad de importación usando modelo juez multimodal
- `benchmark-dataset`: Dataset de 7 imágenes fixture + métricas de referencia
- `calibration-dashboard`: Generación de reporte comparativo multi-modelo con scores y costes

### Modified Capabilities
- Ninguna (infraestructura independiente, no toca la app existente)

## Approach

```
dataset/ (7 imágenes)
  │
  ▼
run_pipeline.py
  ├── Prompt A (modelo visión) → SceneGraph JSON
  ├── Validador SceneGraph
  ├── Compilador determinista → .tc
  └── openrouter.log (coste, latencia)
  │
  ▼
tc_render.js (headless)
  └── .tc → editor import → screenshot PNG
  │
  ▼
evaluate.py (modelo juez)
  └── original vs render → score.json
  │
  ▼
report.py
  └── tabla comparativa multi-modelo
```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/smart-import/pipeline.py` | New | Orquestador del pipeline completo |
| `scripts/smart-import/scene_schema.json` | New | Schema SceneGraph v1 |
| `scripts/smart-import/scene_validator.py` | New | Validador JSON SceneGraph |
| `scripts/smart-import/compiler.py` | New | Compilador SceneGraph → .tc |
| `scripts/smart-import/tc_render.js` | New | Render headless .tc → PNG |
| `scripts/smart-import/evaluate.py` | New | Evaluador juez multimodal |
| `scripts/smart-import/report.py` | New | Generador de reporte |
| `scripts/smart-import/.env.example` | New | Template de configuración |
| `scripts/smart-import/dataset/` | New | 7 imágenes fixture |
| `scripts/smart-import/output/` | New | Resultados del pipeline |
| `scripts/smart-import/requirements.txt` | New | Dependencias Python |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Modelo visión no devuelve JSON válido | Medium | Validador con reparación + retry |
| Coste excesivo en calibración | Medium | Cachear scene.json para re-compilar sin re-analizar |
| Render headless no fiel al editor real | Medium | Usar el mismo Vite build + Playwright real |
| Modelo juez introduce sesgo | Low | Evaluar contra jueces distintos y comparar |

## Rollback Plan

Todo el pipeline es independiente: scripts en `scripts/smart-import/`, no tocan la app. Rollback = borrar el directorio.

## Dependencies

- Python 3.11+ (scripts pipeline)
- Node 22 (tc_render, para usar la app build)
- Playwright (render headless)
- openai Python SDK (para OpenRouter)
- Cuenta OpenRouter con API key en .env
- La app debe tener `npm run build` funcional

## Success Criteria

- [ ] 7 imágenes del dataset generan .tc válidos (importables en la app)
- [ ] Render headless produce screenshots visualmente comparables al original
- [ ] Evaluador juez devuelve scores estructurados con justificación
- [ ] Reporte final muestra scores, costes y latencia por modelo
- [ ] Pipeline completo corre en <5 minutos para 7 imágenes (modo económico)
