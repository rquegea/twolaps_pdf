<!-- plan actualizado por asistente -->
# Plan Días 6–14 (agentes, gating, previews y reporting)

## Convenciones rápidas

- **Esquemas Pydantic**: `src/analytics/schemas.py` (salida por agente)
- **Agentes**: `src/analytics/agents/<agent_name>_agent.py`
- **Prompts**: `config/prompts/agent_prompts.yaml`
- **Gating**: validación Pydantic + mínimos por agente
- **Preview**: `main.py` → `preview-agents`
- **Orquestación**: `src/analytics/orchestrator.py`
- **Reporting**: `src/reporting/chart_generator.py` y `src/reporting/pdf_generator.py`

---

## Estado por día
- Día 6 — CampaignAnalysis: COMPLETO
- Día 7 — ChannelAnalysis: COMPLETO
- Día 8 — ESGAnalysis: COMPLETO
- Día 9 — PackagingAnalysis: COMPLETO
- Día 10 — Pricing/Perceptual: COMPLETO
- Día 11 — Customer Journey: COMPLETO
- Día 12 — Scenario Planning: COMPLETO
- Día 13 — Strategic: COMPLETO
- Día 14 — Synthesis/Executive: COMPLETO

## To-dos
- [x] Implementar CampaignAnalysis (prompt, esquema, agente, gating y preview)
- [x] Implementar ChannelAnalysis (prompt, esquema, agente, gating y preview)
- [x] Implementar ESGAnalysis (prompt, esquema, agente, gating y preview)
- [x] Implementar PackagingAnalysis (prompt, esquema, agente, gating y preview)
- [x] Implementar Pricing/Perceptual (cálculo, esquema, gráfico y preview)
- [x] Implementar CustomerJourney (prompt, esquema, agente, gating y preview)
- [x] Implementar ScenarioPlanning (prompt, esquema, agente, gating y preview)
- [x] Implementar Strategic (prompt, esquema, agente, gating y preview)
- [x] Implementar Synthesis/Executive (prompts, esquemas, agentes, gating, preview)
- [x] Añadir stats de evidencias/confianza en previews de todos los agentes
- [ ] Actualizar orden y dependencias en orchestrator
- [ ] Mapear nuevas secciones y gráficos en PDF y templates
- [ ] Registrar gating/retries y métricas coste/latencia

