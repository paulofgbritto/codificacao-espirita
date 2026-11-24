# agenda-semanal

Planejamento de rotina em camadas para qualquer pessoa.

## Skills

- **base-agenda:** anota tudo o que você fala sobre a sua rotina na "Agenda — Base", em 6 camadas (permanente → anual → período → foco → temporário → semana). Também guarda as regras de notificação por dia.
- **montar-agenda:** monta a semana (ou replaneja a partir de um imprevisto), sem mexer no que já passou. Encaixa metas semanais, mensais, anuais e com prazo nos horários livres e agenda os avisos como mensagens do próprio Claude na conversa do planejamento.

## Regras

- **Exceção:** a camada mais variável vence enquanto for válida.
- **Disputa de horário:** vence a maior prioridade; em empate, a camada mais fixa.

## Princípios (protegidos)

Num projeto do Claude, o documento "Princípios do Projeto" guarda a ideia, a história e as regras fundamentais. As skills leem esse documento e só o alteram quando o usuário pede diretamente e permite explicitamente. Ele não leva dados pessoais.

## Contexto central

O doc "Agenda — Contexto" faz o papel de memória das conversas. Toda conversa lê esse doc ao começar e, ao terminar, atualiza só o que mudou, removendo o que ficou obsoleto. Assim as conversas podem ser apagadas sem perder nada.

Dica: nas instruções do projeto, escreva "Sempre leia o doc 'Agenda — Contexto' no Claude Docs antes de responder", para que toda conversa do projeto o leia, mesmo quando nenhuma skill for acionada.

## Requisitos

- Um lugar persistente para os dois docs ("Agenda — Base" e "Agenda — Plano da semana"). Recomendado: Claude Docs.
- Ferramentas de agendamento disponíveis (send_later para os avisos).
- Opcional: uma tarefa agendada no domingo à noite rodando a `montar-agenda`, em modo "aprovar automaticamente".
