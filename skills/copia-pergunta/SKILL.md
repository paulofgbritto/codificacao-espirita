---
name: "copia-pergunta"
description: "Quando o usuário fizer uma pergunta sobre espiritismo que pode já existir em O Livro dos Espíritos (ex.: \"o que é espírito?\"), acha a pergunta equivalente de Kardec e mostra a pergunta e a resposta do Espírito, com a citação."
---

# copia-pergunta

Uma busca semântica (`rapido`) lista as perguntas do livro mais parecidas com a do usuário; **você mesmo** escolhe a equivalente. Não use agentes (H1–H8), nem lotes: a lista é curta e ler direto é mais rápido, mais barato e mais confiável.

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
A saída lista as perguntas com o id entre colchetes (ex.: `890`, `888.a`) e um trecho da resposta das 3 primeiras de cada busca. A segunda busca existe porque o livro quase sempre trata o assunto geral, não o caso específico.

## Passo 2 — Escolher
Escolha a pergunta de Kardec que seja **pragmaticamente igual** à do usuário: mesmo objetivo, e a resposta dos Espíritos responde ao que ele quis dizer. Palavras diferentes não importam; sentido diferente importa.
- A ordem é imperfeita: termos comuns ("lei de Deus") puxam perguntas genéricas, e a certa pode estar na posição 10–30. Leia as duas listas inteiras.
- "espírito" (minúscula, princípio inteligente) é diferente de "Espírito(s)" (seres); não são equivalentes entre si.
- Em dúvida entre duas, leia as respostas com `python3 candidatos.py resposta ID` e fique com a que responde mais diretamente.
- Se a lista não tiver a equivalente, tente `rapido "PERGUNTA" 60`. Se ainda assim não houver, diga numa frase que o livro não tem uma pergunta equivalente e ofereça a skill `perguntas-livro-espiritos`.

## Passo 3 — Responder
```bash
cd /home/claude/codificacao-espirita && python3 candidatos.py resposta ID
```
O script devolve o texto no formato final (tudo entre aspas, recuo, `[x] — pergunta` em fonte normal, quebra de linha, `— resposta` em itálico, e embaixo apenas `Livro dos Espíritos`). **Copie a saída exatamente como veio**, sem nada antes nem depois.

## Regras
- A resposta ao usuário é **somente** a saída do Passo 3. Nenhuma frase antes ou depois: sem comentários sobre o processo, sem explicar a busca, a lista, os ids, comandos, branches ou qualquer passo interno.
- Não reescreva, resuma nem comente a resposta.
- Se não houver equivalente, a única fala permitida é a frase do Passo 2.