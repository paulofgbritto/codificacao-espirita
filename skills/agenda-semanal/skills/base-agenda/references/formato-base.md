# Formato da base ("Agenda — Base")

Use exatamente esta estrutura. Cada item fica numa linha, com campos separados por ` | `.

```markdown
# Agenda — Base
atualizado em: AAAA-MM-DD
fuso: America/Sao_Paulo
avisos: notificações do Claude (tarefas agendadas)
armazenamento do plano: doc "Agenda — Plano da semana"

## Regras de resolução
- Exceção: a camada mais variável vence enquanto válida (campo `substitui`).
- Disputa de horário: a maior prioridade vence; em empate, a camada mais fixa.

## 1. Permanente
- P-01 | restrição | dormir 23:00–07:00 todos os dias
- P-02 | meta | academia | 3 vezes / semanal | bloco 1h | prioridade alta | preferir manhã
- P-03 | restrição | dia com saída 17:30 → não agendar nada depois
- P-04 | notificação | segunda | avisar sim | 07:00 | conteúdo: plano da tarde
- P-05 | notificação | dia com saída 17:30 | avisar não
- P-06 | compromisso | nutricionista | a cada 15 dias, sábado 09:00 (próxima: 2026-11-21)

## 2. Anual
- A-01 | meta | simulado completo | 1 vez / mensal | bloco 5h | prioridade alta | válido 2027-01-01→2027-11-30

## 3. Período
- S-01 | compromisso | aula | seg–sex 07:00–12:00 | válido 2026-08-01→2026-12-15
- S-02 | compromisso | aula | qua 13:00–17:30 | válido 2026-08-01→2026-12-15

## 4. Foco
- F-01 | foco | matemática prioridade alta | válido 2026-11-01→2026-11-30

## 5. Temporário
- T-01 | exceção | sem aula de física | substitui S-01 (ter 08:00–09:40) | válido 2026-11-16→2026-11-29
- T-02 | meta | trabalho de geografia | 4 horas / até 2026-11-20 | bloco 1h | prioridade alta | válido 2026-11-15→2026-11-20

## 6. Semana
- W-01 | compromisso | prova de química | 2026-11-19 10:00–12:00 | semana 2026-W47

## Arquivo
- (itens vencidos, com a data em que saíram)
```

## Campos

- **ID:** prefixo da camada (`P`, `A`, `S`, `F`, `T`, `W`) + número sequencial. Nunca reutilize um ID.
- **tipo:** `compromisso` · `meta` · `restrição` · `notificação` · `foco` · `exceção`
- **meta:** `quantidade unidade / período`, em que a unidade é `vezes` ou `horas` e o período é `semanal` (padrão), `mensal`, `semestral`, `anual` ou `até AAAA-MM-DD` (tarefa com prazo). Depois vêm `bloco <duração>`, `prioridade alta|média|baixa` e preferências opcionais (`preferir manhã`, `não seguidos`, `mínimo 1 dia de intervalo`).
- **Repetição:** texto livre ("a cada 15 dias", "toda 1ª segunda do mês"). Quando houver ciclo, inclua uma data-âncora (`próxima: …`).
- **válido:** `início→fim` em datas ISO. Sem `válido` significa que vale para sempre na camada.
- **substitui:** ID (e, se for parcial, o trecho) do item mais fixo que a exceção suspende.

O conteúdo de exemplo acima é só ilustração. A base real começa vazia, com as seções e as regras de resolução.
