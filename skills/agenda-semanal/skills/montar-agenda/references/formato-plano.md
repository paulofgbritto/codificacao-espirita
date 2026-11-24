# Formato do plano ("Agenda — Plano da semana")

Um único doc, atualizado no lugar a cada planejamento. **Compactação obrigatória** a cada planejamento completo:
- Guarde o detalhe (blocos e avisos) **só da semana atual**.
- Guarde o resumo de progresso **só das semanas do mês atual** (uma linha por semana).
- Apague tudo o que for mais antigo. Mantenha só o progresso acumulado das metas mensais, semestrais e anuais ainda abertas (uma linha por meta).

```markdown
# Agenda — Plano da semana
semana: 2026-W47 (2026-11-16 → 2026-11-22)
planejado em: 2026-11-15 20:00 (completo)
replanejado em: 2026-11-18 13:10 (a partir de 2026-11-18 13:00 — "fiquei no CEFET até 16h")

## Blocos
| ID | dia | horário | atividade | origem | status |
|----|-----|---------|-----------|--------|--------|
| B-01 | seg 16/11 | 14:00–15:30 | Matemática (funções) | P-07 | feito |
| B-02 | seg 16/11 | 16:00–17:00 | Academia | P-02 | não feito |
| B-03 | qua 18/11 | 18:00–19:00 | Academia | P-02 | planejado |
| B-04 | qui 19/11 | 14:00–16:00 | Trabalho de geografia | T-02 | planejado |

## Avisos
| ID | quando | texto (resumo) | origem | status | tarefa |
|----|--------|----------------|--------|--------|--------|
| AV-01 | seg 16/11 07:00 | Tarde de segunda: … | P-04 | enviado | trg_abc |
| AV-02 | qui 19/11 07:00 | Tarde de quinta: … | P-04 | agendado | trg_def |

status: planejado · feito · não feito · cancelado

## Progresso por período
| meta | período | alvo | cumprido | falta |
|------|---------|------|----------|-------|
| P-02 Academia | semana W47 | 3 vezes | 0 | 3 |
| A-01 Simulado | nov/2026 | 1 vez | 0 | 1 |
| T-02 Trabalho geografia | até 20/11 | 4 horas | 0 | 4 |

## Déficit
- (metas que não couberam e por quê)

## Histórico
- W46: Academia 2/3 · Matemática 5h/6h · Simulado nov 0/1
```

## Regras

- O ID de bloco (`B-xx`, `AV-xx`) é único dentro da semana.
- A coluna `tarefa` guarda o ID (`trigger_id`) da mensagem agendada do aviso. É ela que permite cancelar e refazer o aviso num replanejamento.
- `origem` aponta o ID do item da base que gerou o bloco.
- O progresso de metas mensais, semestrais e anuais soma o Histórico com a semana atual dentro do período.
