---
name: "perguntas-livro-espiritos"
description: "Dada uma situação de vida, os 8 agentes Haiku (H1–H8) dão nota por dúvida a cada item de O Livro dos Espíritos; o principal corta, lê os textos e o estilo de Kardec e responde em blocos, com as perguntas transcritas e análise cruzada."
---

# Responder a uma situação com O Livro dos Espíritos

## Silêncio até a análise (regra principal)
Do Passo 1 ao Passo 6 o modelo principal **não escreve nada para o usuário**: nem aviso de que vai começar, nem resumo de cada passo, nem as dúvidas, a matriz, os caminhos de arquivo ou os números. Só faz as chamadas de ferramenta, uma após a outra. A primeira e única coisa que o usuário lê é a resposta do Passo 7. Se um passo falhar e for preciso avisar algo, uma frase curta e só isso. Exceção: se o usuário pedir só a lista de perguntas relevantes, responda com a matriz do Passo 4, sem comentário.

## Entrada
A situação do usuário, com todos os detalhes que ele contou (nomes, lugares, frases ditas, sentimentos). Exemplos: "briguei com meu pai", "perdi o emprego", "estou com medo da morte".

Identificadores do banco: `[919.a]` pergunta/subpergunta (P: pergunta, R: resposta dos Espíritos); `[K919.a]` comentário de Kardec após aquela pergunta; `[N4]` nota de rodapé (de Kardec ou da Editora); `[I8]` parágrafo da Introdução do livro (I1 a I125, escrita por Kardec). O banco e os scripts ficam no GitHub público `paulofgbritto/codificacao-espirita`; nunca baixe nada pelo conector do Google Drive.

## Passo 1: sessão pronta?
Se `/home/claude/haikus.json` não existe, rode antes a skill `espiritismo-init` (prepara o banco e abre H1–H8, cada um já com seu bloco lido). Pegue os 8 ids nesse arquivo. Não abra agentes novos. Se `/home/claude/codificacao-espirita/dados/livro_dos_espiritos.json` ou `docs/estilo_kardec.md` não existir, o `espiritismo-init` também resolve.

## Passo 2: quebrar a situação em dúvidas
O modelo principal escreve de 3 a 5 dúvidas concretas que a situação levanta (D1, D2, ...), cobrindo cada aspecto: o que aconteceu, as pessoas envolvidas, os sentimentos do usuário e a dúvida de fundo (justiça divina, livre-arbítrio etc.). Uma linha por dúvida. Não mostre ao usuário.

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
- Dê nota separada para cada comentário de Kardec [K...], cada nota [N...] e cada parágrafo da Introdução [I...], pelo próprio texto, mesmo que a pergunta ligada tenha nota baixa.
Faça as notas internamente; não as escreva na resposta.

Formato da resposta: SOMENTE uma lista Python (matriz) com os itens de nota 30% ou mais. Cada item é uma lista de 3 elementos: ['id', tokens, nota], onde id é exatamente como aparece nos colchetes, tokens é o número escrito em (tokens: N) logo após o id e nota é a porcentagem (número inteiro).
Exemplo: [['180', 95, 75], ['K181', 40, 30], ['N4', 22, 45], ['I8', 60, 50]]
Se nenhum chegar a 30%, responda apenas: []
```

## Passo 4: consolidar e cortar
1. Cole as 8 respostas, uma após a outra, e consolide pelo banco, sem ler textos:
   `cd /home/claude/codificacao-espirita && python3 situacao.py matriz "<as 8 respostas juntas>"`
   (junta as matrizes, tira duplicatas ficando com a maior nota, põe na ordem do livro, corrige os tokens pelo banco e descarta ids inexistentes, avisando).
2. Corte pelo limite de tokens (padrão 20000; use outro se o usuário pedir), ficando com os itens de maior nota:
   `python3 selecionar.py "<matriz do passo 1>" 20000`
   (maior nota primeiro, até o primeiro item que não couber; saída na ordem do livro).
3. Se um Hn responder fora do formato, reenvie a mensagem só a ele. Se ele não for encontrado, reabra só aquele Hn como manda o `espiritismo-init` e atualize o haikus.json. O modelo principal não filtra nem reavalia as listas dos agentes.

## Passo 5: gerar os textos
```
cd /home/claude/codificacao-espirita && python3 consultar_lista.py "<matriz do selecionar.py>"
```
O comando imprime um caminho por linha. Listas grandes saem divididas em partes de até 45 mil caracteres, sem cortar itens, porque uma leitura aceita no máximo ~25 mil tokens. Os textos vêm na ordem do livro, sem repetidos, e o cabeçalho de cada item mostra a relevância dada pelos agentes. Não use `--completo`: ele acrescenta comentários e notas que os agentes já avaliaram e deixaram de fora. Se aparecer "Não encontrados" no fim, ignore esses ids.

## Passo 6: ler (uma vez, fica em cache)
- Por último, antes de escrever, no mesmo bloco de chamadas paralelas, leia com UMA chamada Read cada: os arquivos impressos no Passo 5 e `/home/claude/codificacao-espirita/docs/estilo_kardec.md` (análise da linguagem de Kardec).
- Se uma leitura vier truncada, gere de novo com `--max-caracteres 35000` em vez de ler por pedaços.
- Não releia nada depois. Para perguntas seguintes sobre a mesma situação, responda a partir do que já foi lido; só rode de novo os Passos 2 a 6 se o usuário trouxer fatos novos, e então gere arquivo só com os ids novos.
- Antes de escrever, considere válido apenas o que está nesses textos e na situação do usuário: não traga doutrina de outras fontes.

## Passo 7: responder — estrutura

A resposta é um texto único, organizado em **blocos numerados por tema** (`## 1. Título do tema`), seguido de um resumo final. Use todos os itens relevantes da matriz, dando mais peso aos de maior relevância.

### Cabeçalho do bloco
Logo abaixo do título, um cabeçalho **curto** (2 a 3 frases, denso): apresenta o tema, faz referência ao ponto da situação de que o bloco trata, já adianta a ideia espírita central e introduz as citações ("Observe estas passagens:", "Leia:"). Não reconte a história do usuário; uma referência basta.
- Exemplo bom: "Você passou por esse doloroso e imenso processo iniciado há anos, simplesmente por ser um homem gay. O livro não trata de pessoas gays explicitamente, mas mostra que o sexo é produto da organização do corpo físico, e que o Espírito não tem sexo. Observe estas perguntas do Livro dos Espíritos:"

### Dentro do bloco
Cada bloco tem um ou mais grupos. Cada grupo é:
1. (do 2º grupo em diante) uma ponte curta que introduz as próximas citações, em geral uma pergunta retórica no fim da análise anterior ("Mas como reconhecer, então, a simpatia verdadeira? Os Espíritos dão um critério:");
2. de 1 a 5 perguntas ou notas de Kardec, transcritas;
3. a sua análise.

Os grupos não são fechados: uma análise pode citar itens de outros grupos ou blocos, ou trechos de itens que não foram transcritos. Mas a análise de cada item transcrito termina no bloco em que ele aparece. Nunca nomeie os grupos (nada de "mini-análise") nem os separe visualmente; o texto corre contínuo.

Cada pergunta/nota transcrita é um parágrafo; cada análise é um parágrafo.

### Transcrição
- Copie **identicamente** do arquivo lido (só corrija artefatos de extração, como `preservar--nos` → `preservar-nos`).
- Pode destacar em **negrito** as partes importantes da pergunta, da resposta ou da nota.
- Formato de pergunta (citação em bloco; duas linhas e o rodapé):
```
> Pergunta de Kardec, em fonte normal  
> — *“Resposta dos Espíritos, em itálico, com **negrito** onde importa.”*  
> Livro dos Espíritos, item [180]
```
- Formato de parágrafo da Introdução (texto de Kardec, não dos Espíritos; igual ao de nota, com outro rodapé):
```
> Texto do parágrafo, com **negrito** onde importa.  
> Livro dos Espíritos, Introdução, item [I8]
```
- Formato de nota/comentário de Kardec (sem a linha de resposta):
```
> Texto de Kardec, com **negrito** onde importa.  
> Livro dos Espíritos, item [K181]
```

### A análise
- **Cruze os dois lados em cada raciocínio.** Cada frase de raciocínio usa a situação e o livro juntos. Não faça metade espiritismo e metade situação, um depois do outro.
- **Específico nos dois lados.** Na situação: nomes, lugares, frases ditas, detalhes do sentimento. No livro: detalhes das respostas dos Espíritos, do raciocínio de Kardec, a lógica do texto.
- **Só conexões que importam.** Use um elemento da situação apenas se ele se liga de forma significativa ao texto. Se não houver conexão real, não o mencione. Nada de repetir detalhes sem função.
- **Curto e denso.** Sem encheção de linguiça. Prefira a forma mais enxuta que diga o mesmo.
- **Citações:** ids entre colchetes; quando a frase apoia-se em vários itens, agrupe no fim: `[200, 201, 822.a]`.
- **Sem aspas** ao usar elementos do livro: incorpore trechos e expressões ao texto diretamente (ex.: os Espíritos afins se buscam reciprocamente por entre a multidão [386]). Aspas só para trechos longos citados literalmente ou para figuras de linguagem. Frases do próprio usuário podem ir entre aspas.

### Estilo de Kardec (do `docs/estilo_kardec.md`)
Ainda é o Claude falando, e as citações seguem como acima. Mas, no espaço da articulação, escreva parecido com Kardec:
- parta de um princípio curto e sóbrio; apoie-o num fato da situação ou da experiência comum; encadeie com "Ora,", "pois", "segue-se que", "com efeito", "ao passo que";
- perguntas retóricas ("Que se segue daí?", "Que ganharia você com…?");
- antecipe a objeção mais forte em discurso indireto ("Objetarão, talvez, que…", "Dir-se-á que…") e desmonte-a;
- comparações da vida comum, marcando onde deixam de valer ("com a diferença de que…");
- "nós" ao consolar; nunca "tu"; emoção rara e contida;
- **separe o que é certo do que é dedução**, e confesse o que o livro não diz;
- feche o texto com um resumo ordenado ("Reconheçamos, portanto, …") e uma sentença antitética curta.

**Não é teatro.** O conteúdo vem antes do estilo. Nunca force uma análise falsa ou exagerada só para soar como Kardec.

### Rigor moral e de conteúdo (prioridade máxima)
- A análise deve ser rigorosamente verdadeira em relação ao livro e à situação. Não acrescente doutrina que não esteja nos textos lidos; quando for dedução sua, diga que é dedução; se algo não for coberto, diga.
- Se o livro não trata diretamente do tema (ex.: orientação sexual), diga isso antes de deduzir dos princípios.
- Nunca use uma resposta para culpar, condenar ou rotular o usuário ou terceiros além do que o texto realmente sustenta (ex.: "punição passageira" em [939] é geral, não sentença sobre quem sofre). Aplique respostas de outro contexto (empreendimentos, doutrinas) com reserva explícita.
- Interprete a situação com exatidão: não invente motivos, não distorça o que alguém quis dizer; na dúvida, não afirme.
- Releia frases com alternativas ("X ou Y") para que não digam o contrário do pretendido (ex.: não escrever que o valor do amor "depende de ser afeição da alma ou encantamento do corpo").

### Resumo final
`## Em resumo`: uma frase de abertura ("Reconheçamos, portanto, o que o livro ensina sobre…"), uma lista curta com uma linha por bloco (com os ids), e uma sentença antitética de fecho.

## Regras
- A Introdução (I1 a I125) está no bloco 4, junto com o capítulo VIII da Parte 2; cada parágrafo é um item.
- O capítulo P2C05 (bloco 2) é um único texto longo de Kardec, o item [222]: entra inteiro ou não entra.
- Não troque os 8 agentes por uma pré-seleção pela busca (`situacao.py pool`): no teste, ela deixou de fora cerca de 40% dos itens com nota 60%+.
- Os blocos montados antes de 24/11/2026 não têm `(tokens: N)`: nesse caso o agente pode pôr 0, e o Passo 4 preenche pelo banco.
- Não comente o processo (arquivos, comandos, matriz, agentes, tokens, grupos) em nenhum momento. Em português.
