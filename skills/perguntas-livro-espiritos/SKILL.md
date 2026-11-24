---
name: "perguntas-livro-espiritos"
description: "Dada uma situação de vida, os 8 agentes Haiku fixos (H1–H8, um por bloco de O Livro dos Espíritos) dão nota por dúvida a cada pergunta e anotação de Kardec e devolvem as de 30%+ numa matriz [id, tokens, nota]; o principal consolida."
---

# Perguntas do Livro dos Espíritos relevantes para uma situação

## Entrada
O usuário descreve uma situação qualquer da vida (ex.: "briguei com meu pai", "perdi o emprego", "estou com medo da morte").

Identificadores do banco: `[919.a]` pergunta/subpergunta (P: pergunta, R: resposta dos Espíritos); `[K919.a]` comentário de Kardec após aquela pergunta; `[N4]` nota de rodapé (de Kardec ou da Editora). O banco e os scripts ficam no GitHub público `paulofgbritto/codificacao-espirita`; nunca baixe nada pelo conector do Google Drive.

## Passo 1: sessão pronta?
Se `/home/claude/haikus.json` não existe, rode antes a skill `espiritismo-init` (prepara o banco e abre H1–H8, cada um já com seu bloco lido). Pegue os 8 ids nesse arquivo. Não abra agentes novos.

## Passo 2: quebrar a situação em dúvidas
O modelo principal escreve de 3 a 5 dúvidas concretas que a situação levanta (D1, D2, ...), cobrindo cada aspecto: o que aconteceu, as pessoas envolvidas, os sentimentos do usuário e a dúvida de fundo (justiça divina, livre-arbítrio etc.). Uma linha por dúvida. Não mostre as dúvidas ao usuário, a menos que ele peça.

## Passo 3: mandar a tarefa aos 8
Num único bloco, 8 chamadas de SendMessage (`to`: id de H1 ... H8), todas com a mesma mensagem (substitua {SITUAÇÃO} e {DÚVIDAS}):

```
Tarefa perguntas. Use o SEU bloco, que você já leu (não releia o arquivo).
Situação do usuário: {SITUAÇÃO}

Dúvidas da situação (avalie cada uma separadamente):
{DÚVIDAS}

Analise CADA item do seu bloco individualmente, um por um, comparando-o só com as dúvidas (não com os outros itens). Para cada item, dê uma nota de 0% a 100% para CADA dúvida e use a MAIOR delas como nota do item:
- 100% = o item é quase idêntico àquela dúvida e a responde com extrema clareza.
- 50% = o item cobre metade daquela dúvida de forma geral, sem ser específico nem detalhado.
- 0% = o item não tem nada a ver com aquela dúvida.
- Use valores intermediários conforme esses pontos de referência.
- Um item que responde muito bem a UMA dúvida tem nota alta, mesmo que não fale das outras.
- Para uma pergunta, avalie a pergunta E a resposta dos Espíritos juntas.
- Dê nota separada para cada comentário de Kardec [K...] e cada nota [N...], pelo próprio texto, mesmo que a pergunta ligada tenha nota baixa.
Faça as notas internamente; não as escreva na resposta.

Formato da resposta: SOMENTE uma lista Python (matriz) com os itens de nota 30% ou mais. Cada item é uma lista de 3 elementos: ['id', tokens, nota], onde id é exatamente como aparece nos colchetes, tokens é o número escrito em (tokens: N) logo após o id e nota é a porcentagem (número inteiro).
Exemplo: [['180', 95, 75], ['K181', 40, 30], ['N4', 22, 45]]
Se nenhum chegar a 30%, responda apenas: []
```

## Passo 4: consolidar
1. Cole as 8 respostas, uma após a outra, e consolide pelo banco, sem ler textos:
   `cd /home/claude/codificacao-espirita && python3 situacao.py matriz "<as 8 respostas juntas>"`
   (junta as matrizes, tira duplicatas ficando com a maior nota, põe na ordem do livro, corrige os tokens pelo banco e descarta ids inexistentes, avisando).
2. Corte pelo limite de tokens (padrão 20000; use outro se o usuário pedir), ficando com os itens de maior nota:
   `python3 selecionar.py "<matriz do passo 1>" 20000`
   (maior nota primeiro, até o primeiro item que não couber; saída na ordem do livro).
3. Responda ao usuário SOMENTE com a matriz que o `selecionar.py` imprimiu, exatamente como veio.
4. Sem comentários, títulos ou explicações sobre o processo, a menos que o usuário peça.
5. Para ler o conteúdo depois (se pedido), use a skill `pergunta-livro-espiritos-2`.

## Regras
- O modelo principal (Sonnet ou Opus) não filtra nem reavalia as listas dos agentes; apenas escreve as dúvidas e consolida.
- Se um Hn responder fora do formato, reenvie a mensagem só a ele. Se ele não for encontrado, reabra só aquele Hn como manda o `espiritismo-init` e atualize o haikus.json.
- O capítulo P2C05 (bloco 2) é um único texto longo de Kardec, o item [222]: entra inteiro ou não entra.
- Não troque os 8 agentes por uma pré-seleção pela busca (`situacao.py pool`): no teste, ela deixou de fora cerca de 40% dos itens com nota 60%+.
- Os blocos montados antes de 24/11/2026 não têm `(tokens: N)`: nesse caso o agente pode pôr 0, e o Passo 4 preenche pelo banco.