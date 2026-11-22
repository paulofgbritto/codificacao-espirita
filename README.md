# Banco de dados — O Livro dos Espíritos

Banco local e API de consulta para *O Livro dos Espíritos* (Kardec, trad. Guillon Ribeiro, FEB).
Só Python 3.8+, sem internet e sem IA: consultas não gastam tokens. A lista completa de comandos está em `python codificacao_db.py ajuda`.

## Arquivos e instalação

| Arquivo | O que é |
|---|---|
| `codificacao_db.py` | API (linha de comando, módulo Python e modo interativo) |
| `consultar_lista.py` | Recebe uma lista de ids e junta tudo em um arquivo de texto |
| `extrair_livro_dos_espiritos.py` | Gera o banco a partir do PDF (opcional) |
| `dados/livro_dos_espiritos.zip` | O banco; descompacte em `dados/` → `dados/livro_dos_espiritos.json` |

Teste: `python codificacao_db.py stats`

## Conteúdo e identificadores

1019 perguntas + 197 subperguntas, 29 capítulos, 161 seções, 495 páginas, 120 temas, Índice geral (668 assuntos), 191 comentários de Kardec, 19 itens numerados escritos por Kardec, 2 textos de Kardec sem número, 25 notas de rodapé, Introdução, Prolegômenos e Conclusão.

| Id | O que é |
|---|---|
| `919` / `919.a` | pergunta / subpergunta (aceita também `919a`, `"919 a"`) |
| `K919.a` | comentário de Kardec após a pergunta 919.a (só texto de Kardec; remissões soltas como "(540)" ficam no campo `referencia`, e avisos "N.E.:" no campo `nota_editora`) |
| `N4` | nota de rodapé 4 |
| `872` (tipo kardec) | item numerado escrito por Kardec, sem pergunta: 59, 100–113, 222, 257, 455, 872 (campo `texto`) |
| `Ke1`, `Ke2` | texto de Kardec sem número (início de seção), com `antes_de` = pergunta seguinte |
| `180-182` | faixa (inclui subperguntas) |

Listas aceitam `|`, `,` ou `;` como separador.

## Comandos principais

`python codificacao_db.py <comando> [args] [opções]`

| Para | Comando |
|---|---|
| Perguntas e anotações | `pergunta 919a` · `perguntas "180-182 \| K181 \| N4"` · `anotacoes "K919.a, N4, Ke1"` · `vizinhas 928` |
| Estrutura | `capitulo 3.12` · `capitulos` · `parte 3` · `secao "si mesmo"` |
| Páginas | `pagina 120` · `pagina 120-125` · `buscar_paginas "anjo guardião"` |
| Temas e Índice | `tema Trabalho` · `temas` · `indice vocação` |
| Busca no texto | `buscar "orgulho egoísmo" --modo todas\|qualquer\|frase\|regex --em comentario --parte 3` |
| Kardec | `kardec "900-919" --expandir` · `notas_kardec` · `remissoes 1000` · `citada_por 919` · `assinadas "São Luís"` |
| Listas | `ordenar "919.a\|N4\|K919.a"` (tira repetidos, ordem do livro) · `exportar capitulos` |
| Outros | `texto introd.VI` · `nota 4` · `caminho perguntas/928/resposta` · `chaves capitulos` |

Opções de saída: `--ids` (só números, o mais barato), `--formato curto|json`, `--campos pergunta,resposta`, `--expandir`, `--sem-subs`.
Sem argumentos, abre o modo interativo (`sair` para fechar). A busca ignora acentos e maiúsculas.

## consultar_lista.py

Transforma a lista da skill em arquivos de texto prontos, para a IA ler tudo de uma vez (e manter em cache), em vez de consultar pergunta por pergunta.
Faz split, strip, consulta cada id na API, remove repetidos, ordena como no livro e grava. Listas grandes saem em partes de até 60 mil caracteres (~18 mil tokens, abaixo do limite de uma leitura), sem cortar itens; cada caminho é impresso numa linha.

```
python consultar_lista.py "180 | 181 | K181 | 182.b | N4"          → imprime o(s) caminho(s) na pasta temporária
python consultar_lista.py "180, 181, 200-202" -o consulta.txt       → grava onde você escolher
echo "180|K181" | python consultar_lista.py                         → lê da entrada padrão
```

| Opção | Efeito |
|---|---|
| `-o arquivo` | arquivo de saída (padrão: pasta temporária, `consulta_le_*.txt`) |
| `--completo` | inclui também o comentário de Kardec e as notas de cada pergunta |
| `--manter-ordem` | mantém a ordem recebida, sem reordenar |
| `--max-caracteres N` | tamanho de cada parte (padrão 60000; `0` = um arquivo só) |

Cada item sai como `[180] p.127 Parte…, Cap…` + `P:` + `R:` (+ `Referência:`/`N.E.:` quando houver); anotações saem como `[K919.a]` ou `[N4]`.
`NENHUMA` é ignorado; ids inexistentes aparecem no fim, em "Não encontrados".

## Em Python

```python
from codificacao_db import LivroDosEspiritos
le = LivroDosEspiritos()
le["928"]; le.perguntas("180-182"); le.anotacao("K919.a"); le.ordenar("1|N4|K132")
le.capitulo("3.12"); le.pagina(120); le.tema("Trabalho"); le.indice("vocação")
le.buscar("orgulho", parte=3); le.kardec("900-919"); le.obter("perguntas/919.a/resposta")
```
Erros de consulta lançam `ErroConsulta`.

## Uso por IA

A IA precisa rodar onde os arquivos estão (Claude Code no PC, ou uma sessão com os arquivos). O Drive só guarda; não executa.
Mais econômico: achar números com `--ids` → montar o arquivo com `consultar_lista.py` → ler o arquivo uma vez.

## Regerar e limitações

- Regerar: `pip install pypdf` e `python extrair_livro_dos_espiritos.py "Livro-dos-Espiritos.pdf"` (valida e avisa se faltar pergunta).
- Só cobre *O Livro dos Espíritos*; os outros 4 livros ainda não.
- Perguntas 14 e 246: aspas perdidas no PDF; divisão resposta/comentário estimada.
- Temas são por capítulo.

## Busca semântica (sem IA na nuvem, sem tokens)

`busca.py` encontra as perguntas, comentários de Kardec (`K163`) e notas (`N4`) mais prováveis para uma situação, combinando busca por significado (BAAI/bge-m3), BM25 e um reranker (BAAI/bge-reranker-v2-m3) que dá a nota final de 0 a 100%. Tudo roda no seu computador.

Instalação (uma vez; os modelos baixam sozinhos, cerca de 4,5 GB no total):

```
pip install -r requirements.txt
cd dados && tar -xf livro_dos_espiritos.zip && cd ..     (ou descompacte o zip pelo Windows)
python busca.py indexar
```

Uso rápido: `python pergunte.py` (digite a situação e veja pergunta e resposta de cada item).

Comandos de `busca.py`:

| Comando | O que faz |
|---|---|
| `buscar "situação"` | itens mais prováveis (`-n 20`, `--min 40`, `--ordem livro`, `--candidatos 60`) |
| `buscar "..." --duvida "..." --duvida "..."` | busca cada dúvida separada; o item fica com a maior nota |
| `ranking "situação"` | todos os itens do livro, do mais ao menos provável |
| `nota "situação" --ids "163, K165, N4"` | nota de itens específicos |
| `interativo` | várias consultas seguidas, sem recarregar os modelos |

Opções comuns: `--formato ids` (padrão, `163 | K163`), `ids-nota`, `linhas`, `completo`, `json`; `--tipos pergunta,comentario,nota,kardec,texto_kardec`; `--sem-reranker` (mais rápido, nota só relativa); `--reranker <modelo>`. Para trocar o modelo de vetores: `python busca.py indexar --modelo <modelo>`.
