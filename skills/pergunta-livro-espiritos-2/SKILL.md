---
name: "pergunta-livro-espiritos-2"
description: "Parte 2 de perguntas-livro-espiritos: recebe a matriz [['id', tokens, nota], ...] da parte 1, lê os textos e o estilo de Kardec e responde à situação em blocos, com as perguntas transcritas e análise cruzada."
---

# Parte 2: responder à situação com os textos de O Livro dos Espíritos

## Entrada
- A matriz da parte 1 (skill perguntas-livro-espiritos), já cortada pelo limite de tokens: `[['180', 95, 75], ['K181', 40, 30], ['N4', 22, 45]]` (id, tokens, relevância %). Passe-a como veio, sem converter. Uma lista simples de ids (`180 | 181 | K181`) também é aceita.
  - `919.a` = pergunta e resposta dos Espíritos; `K919.a` = comentário de Kardec; `N4` = nota de rodapé.
- A situação do usuário, com todos os detalhes que ele contou (nomes, lugares, frases ditas, sentimentos). Se não vier junto, use a situação já descrita na conversa.
- Se não houver matriz na conversa, rode antes a parte 1.

## Passo 1: código pronto?
O código vem do GitHub público `paulofgbritto/codificacao-espirita` (a skill `espiritismo-init` já deixa tudo pronto). Se `/home/claude/codificacao-espirita/dados/livro_dos_espiritos.json` ou `/home/claude/codificacao-espirita/docs/estilo_kardec.md` não existir:
```
cd /home/claude && [ -d codificacao-espirita ] || git clone --depth 1 https://github.com/paulofgbritto/codificacao-espirita
cd codificacao-espirita && git pull -q origin main; cd dados && unzip -oq livro_dos_espiritos.zip
```
Nunca baixe pelo conector do Google Drive. Esta parte não usa agentes.

## Passo 2: gerar os textos
```
cd /home/claude/codificacao-espirita && python3 consultar_lista.py "<matriz>"
```
O comando imprime um caminho por linha. Listas grandes saem divididas em partes de até 45 mil caracteres, sem cortar itens, porque uma leitura aceita no máximo ~25 mil tokens. Os textos vêm na ordem do livro, sem repetidos, e o cabeçalho de cada item mostra a relevância dada pela parte 1. Não use `--completo`: ele acrescenta comentários e notas que a parte 1 já avaliou e deixou de fora. Se aparecer "Não encontrados" no fim, ignore esses ids.

## Passo 3: ler (uma vez, fica em cache)
- No mesmo bloco de chamadas paralelas, leia com UMA chamada Read cada: os arquivos impressos no Passo 2 e `/home/claude/codificacao-espirita/docs/estilo_kardec.md` (análise da linguagem de Kardec).
- Se uma leitura vier truncada, gere de novo com `--max-caracteres 35000` em vez de ler por pedaços.
- Não releia nada depois. Para perguntas seguintes sobre a mesma situação, responda a partir do que já foi lido; só gere novo arquivo se a matriz mudar (e só com os ids novos).

## Passo 4: responder — estrutura

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

### Proibições
- Não comente o processo (arquivos, comandos, matriz, partes, tokens, grupos).
- Em português.