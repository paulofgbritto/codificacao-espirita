---
name: montar-agenda
description: Planeja ou replaneja a semana do usuário a partir da "Agenda — Base", encaixando metas nos horários livres, e agenda os avisos (mensagens agendadas na própria conversa) para cada dia. Use para "monte minha semana", "planeje a próxima semana", "tive um imprevisto", "fiquei preso no CEFET, reorganiza o resto da semana", "não fiz a academia hoje", "o que eu faço hoje", e também quando a tarefa agendada de domingo pedir o planejamento semanal. Aceita como entrada a data a partir da qual replanejar e o que mudou.
argument-hint: "[a partir de AAAA-MM-DD] [o que mudou]"
---

# Montar a agenda

Transforme a base em camadas num plano concreto e em avisos enviados pelo próprio Claude. A mesma skill serve para dois usos: o **planejamento completo** (domingo, para a semana seguinte inteira) e o **replanejamento** (no meio da semana, a partir de um imprevisto).

## Entradas

Leia de `$ARGUMENTS` ou da mensagem:
- **início:** a partir de quando replanejar. Padrão no domingo ou quando chamada pela tarefa agendada: próxima segunda 00:00. Padrão no meio da semana: agora, arredondado para o próximo horário cheio.
- **mudança:** o imprevisto ou a informação nova (opcional).
- **feito/não feito:** o que o usuário disser que cumpriu ou não cumpriu (opcional).

Se a mudança for algo que deve durar (não só hoje), registre-a primeiro na base, seguindo a skill `base-agenda`, e depois planeje.

## Passo 1: Carregar

0. Se houver projeto, leia o documento protegido **"Princípios do Projeto"** (nunca altere nesta skill; mudanças nele só pela regra da seção 0 da `base-agenda`). Depois leia o **"Agenda — Contexto"** e siga as decisões dele. Ao final da execução, aplique a regra de atualização do contexto descrita na seção 0 da skill `base-agenda`.
1. Leia a **"Agenda — Base"** (no mesmo armazenamento indicado na skill `base-agenda`). Se não existir, pare e rode a `base-agenda` para criá-la.
2. Leia o doc **"Agenda — Plano da semana"**, se existir (formato em `references/formato-plano.md`).
3. Monte a **foto ativa** da semana alvo: todos os itens válidos no período, aplicando as exceções (`substitui`), em que a camada mais variável vence.

## Passo 2: Congelar o passado

- Tudo antes de **início** fica como está. Não altere esses blocos nem os eventos deles.
- Blocos passados contam como **cumpridos**, exceto os que o usuário disse que não fez (marque-os `não feito`).

## Passo 3: Calcular o que falta

Para cada meta ativa, calcule quanto falta no **período dela**:
- **semanal:** quantidade − cumprido na semana.
- **mensal / semestral / anual:** quantidade − cumprido no período (use o registro de progresso do plano). Para saber quanto vai nesta semana, divida o restante pelas semanas que sobram no período, arredondando para cima. Se for o último trecho do período, agende tudo o que falta.
- **até uma data (prazo):** quantidade − cumprido. Distribua nos dias livres até o prazo e termine pelo menos um dia antes quando der. A prioridade sobe um nível quando faltar 2 dias ou menos.
- **Repetições irregulares** ("a cada 15 dias", "1ª segunda do mês"): interprete o texto e a data-âncora para saber se caem na semana alvo.

Blocos `não feito` voltam para o saldo da meta.

## Passo 4: Encontrar horários livres

Do **início** até o fim da semana (domingo 23:59), parta do tempo acordado e retire compromissos, restrições, dias "sem nada" e deslocamentos. Deixe pelo menos 15 min de folga entre blocos.

## Passo 5: Encaixar

1. Ordene as metas por prioridade. O foco do mês sobe um nível. Em empate, vence a camada mais fixa.
2. Distribua cada meta respeitando as preferências dela (turno, intervalo entre dias, não seguidos) e espalhe ao longo da semana em vez de concentrar.
3. Se não couber tudo, corte primeiro o de menor prioridade e informe o déficit. Nunca invada sono, restrições ou dias "sem nada".
4. Ao replanejar, mude o mínimo possível: mantenha os blocos futuros que não conflitam e realoque só o afetado.

## Passo 6: Salvar o plano

Atualize no lugar o doc "Agenda — Plano da semana", com os blocos, o status, o ID de cada aviso e o progresso por período.

## Passo 7: Agendar os avisos (mensagens na conversa)

Os avisos são **mensagens agendadas na própria conversa** que está planejando (`send_later`), e não tarefas separadas nem eventos de calendário. Elas não pedem aprovação. Como cada planejamento semanal roda numa conversa nova, o contexto não acumula. Carregue as ferramentas com ToolSearch (`send_later`, `delete_trigger`).

1. **Cancelar:** apague (`delete_trigger`) os avisos futuros, após **início**, que mudaram ou saíram do plano. Use os IDs gravados no plano. Nunca apague avisos que já dispararam.
2. **Criar:** para cada dia com `avisar sim` e para cada aviso extra, chame `send_later` com:
   - `at`: data e hora do aviso, no fuso da base
   - `name`: `Agenda: <dia> <horário>`
   - `initiation`: `human_request`
   - `message`: "Responda ao usuário apenas com este texto, sem mais nada: <texto do aviso>"

   Num replanejamento feito em outra conversa, os avisos novos ficam nessa conversa. Tudo bem.
3. **Texto do aviso:** **limite medido de ~149 caracteres, contando espaços** (o resto é cortado na notificação). Escreva no máximo ~140, com o mais importante primeiro e as atividades separadas por " · ". O detalhe fica no doc do plano. Exemplo:
   `Tarde: 14h Matemática (funções) · 16h Academia · 19h Jogo (pulo) · 21h Revisão`

   Dias com `avisar não` não recebem aviso.
4. Grave no plano os IDs devolvidos (`trigger_id`).
5. **Quando o aviso disparar,** responda exatamente com o texto pedido, sem comentários.

Se não houver ferramenta de agendamento, entregue o plano em texto e diga isso em uma linha.

## Passo 8: Responder

Seja curto:
- **Planejamento completo:** a semana em uma linha por dia, mais o déficit, se houver.
- **Replanejamento:** só o que mudou ("quinta: academia passou para 07:00; sexta: +1h de matemática").

## Tarefa agendada de domingo

Tudo roda em tarefas agendadas, que começam do zero e leem só os docs. Assim nenhuma conversa cresce e o usuário não precisa intervir. Para imprevistos, o usuário pode abrir qualquer conversa nova.

Na primeira vez que esta skill rodar, verifique se existe uma tarefa agendada **repetida** de planejamento semanal, com cron semanal (por exemplo `CRON_TZ=America/Sao_Paulo 0 20 * * 0`). Se não existir e houver ferramenta de agendamento, ofereça criá-la (domingo à noite) com o prompt: "Use a skill montar-agenda para planejar a próxima semana completa e agendar os avisos." Só crie se o usuário aceitar. Lembre-o de que essa tarefa precisa estar em "aprovar automaticamente", senão ela trava esperando aprovação.
