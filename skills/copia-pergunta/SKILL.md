---
name: "copia-pergunta"
description: "Quando o usuário fizer uma pergunta sobre espiritismo que pode já existir em O Livro dos Espíritos (ex.: \"o que é espírito?\"), acha a pergunta equivalente de Kardec e mostra a pergunta e a resposta do Espírito, com a citação."
---

# copia-pergunta

Uma busca semântica (`rapido`) lista os itens do livro mais parecidos com a do usuário (perguntas, comentários de Kardec, notas, textos de Kardec e parágrafos da Introdução); **você mesmo** escolhe o(s) que respondem. A resposta é a transcrição do(s) item(ns) e, só quando o caso pede, uma análise curta. Não use agentes (H1–H8), nem lotes: a lista é curta e ler direto é mais rápido, mais barato e mais confiável.

## Passo 0 — Preparação (só se `/home/claude/codificacao-espirita/modelo_onnx/bge_m3_model.onnx_data` não existir)
```bash
cd /home/claude
[ -d codificacao-espirita ] || git clone --depth 1 https://github.com/paulofgbritto/codificacao-espirita
cd codificacao-espirita
[ -f dados/livro_dos_espiritos.json ] || (cd dados && unzip -oq livro_dos_espiritos.zip)
pip install --break-system-packages -q onnxruntime onnxruntime-extensions rank_bm25 numpy
mkdir -p /home/claude/_modelo && cd /home/claude/_modelo
curl -sSL -o onnx.zip https://github.com/yuniko-software/bge-m3-onnx/releases/latest/download/onnx.zip
unzip -oq onnx.zip
mkdir -p /home/claude/codificacao-espirita/modelo_onnx
mv bge_m3_* /home/claude/codificacao-espirita/modelo_onnx/ && rm -f onnx.zip
```
Timeout de 600000 ms (o modelo tem 1,3 GB). O índice já vem no repositório; nunca baixe nada pelo conector do Google Drive. Não abra os Haiku.

## Passo 1 — Buscar (uma chamada, duas buscas)
Escreva a pergunta do usuário também em versão geral, trocando o caso específico pelo assunto de fundo ("chocolate faz mal?" → "alimentos fazem mal ao corpo"). Rode as duas na mesma chamada:
```bash
cd /home/claude/codificacao-espirita && python3 candidatos.py rapido "PERGUNTA DO USUÁRIO" 30 2>/dev/null; echo ======; python3 candidatos.py rapido "VERSÃO GERAL" 15 2>/dev/null
```
A saída lista os itens com o id entre colchetes e o tipo entre parênteses quando não é pergunta: pergunta (`890`, `888.a`), `(Kardec, comentário)` (`K163`), `(nota)` (`N4`), `(Kardec)` (`59`, `Ke1`) e `(Introdução)` (`I8`). Mostra também um trecho da resposta das 3 primeiras perguntas de cada busca. A segunda busca existe porque o livro quase sempre trata o assunto geral, não o caso específico.

## Passo 2 — Escolher e classificar
Escolha os itens que respondem ao que o usuário quis dizer. Palavras diferentes não importam; sentido diferente importa.
- Quando uma pergunta dos Espíritos e um texto de Kardec (comentário, nota, Introdução) respondem igualmente bem, transcreva a pergunta; use o texto de Kardec quando for ele que responde (definições, explicações de termos, método, objeções).
- A ordem é imperfeita: termos comuns ("lei de Deus") puxam perguntas genéricas, e a certa pode estar na posição 10–30. Leia as duas listas inteiras.
- "espírito" (minúscula, princípio inteligente) é diferente de "Espírito(s)" (seres); não são equivalentes entre si.
- Em dúvida entre duas, leia as respostas com `python3 candidatos.py resposta ID` e fique com a que responde mais diretamente.
- Se as listas não tiverem nada, tente `rapido "PERGUNTA" 60`.

Depois classifique o caso:
- **A. Direta**: um item do livro equivale à pergunta do usuário → transcreva só ele.
- **B. Vários respondem**: mais de um item responde à pergunta do usuário → transcreva todos.
- **C. Só transcrever basta**: a resposta precisa de mais de um item do livro, mas a transcrição deles já responde 100% → transcreva todas, sem análise.
- **D. Precisa de contexto**: o livro trata o assunto geral e não o caso do usuário (ex.: "chocolate faz mal?" → perguntas sobre alimentação), ou as perguntas só respondem em parte, e é preciso pressupor ou articular → transcrição com cabeçalho e análise curta (Passo 4).
- **E. Nada serve** (nem como contexto): diga numa frase que o livro não tem pergunta equivalente e ofereça a skill `perguntas-livro-espiritos`.

## Passo 3 — Responder (casos A, B e C)
```bash
cd /home/claude/codificacao-espirita && python3 candidatos.py resposta ID [ID ...]
```
O script devolve cada item no formato final (tudo entre aspas, recuo, `[x] — pergunta` em fonte normal, quebra de linha, `— resposta` em itálico, e embaixo apenas `Livro dos Espíritos`). Texto de Kardec (comentário, nota, Introdução) sai como `[I8] — Kardec, Introdução: texto`, sem itálico. **Copie a saída exatamente como veio**, sem nada antes nem depois.

## Passo 4 — Responder com análise (caso D)
Gere as transcrições (de 2 a 3 itens, nunca mais) com `python3 candidatos.py resposta ID ID [ID]` e monte a resposta nesta ordem, em texto corrido, sem títulos, sem numeração e sem separadores:
1. **Cabeçalho curto** (2 a 3 frases): diz o que o livro trata e o que não trata do caso do usuário, antecipa a ideia central e introduz as citações ("Observe estas passagens:").
2. **Os itens**, copiados exatamente da saída do script (cada uma com seu rodapé `Livro dos Espíritos`).
3. **Análise curta** (um parágrafo de 3 a 5 frases): cruza o que os Espíritos respondem com o caso do usuário, citando os ids entre colchetes (`[722, 723]`).

Regras da análise:
- Estilo sóbrio, à maneira de Kardec: parta de um princípio curto, apoie-o no fato e encadeie com "Ora,", "pois", "segue-se que". Sem teatro: o conteúdo vem antes do estilo.
- Separe o que o livro diz do que é dedução sua, e diga com todas as letras o que o livro não trata.
- Não acrescente doutrina que não esteja nas respostas lidas; não invente fatos sobre o assunto (saúde, ciência) como se fossem do livro.
- Sem aspas ao usar expressões do livro: incorpore ao texto.

## Regras
- Casos A, B e C: a resposta ao usuário é **somente** a saída do script. Nenhuma frase antes ou depois.
- Caso D: somente cabeçalho, itens e análise, como acima. Nada de comentários sobre o processo: a busca, a lista, os ids descartados, comandos, branches ou qualquer passo interno.
- Não reescreva nem resuma as respostas dos Espíritos: elas vão sempre transcritas.
- Caso E: a única fala permitida é a frase do Passo 2.