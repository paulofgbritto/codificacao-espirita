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
| `extrair_evangelho.py` | Gera o banco de *O Evangelho segundo o Espiritismo* a partir do PDF ou do texto |
| `dados/evangelho.zip` | Banco do Evangelho; descompacte em `dados/` → `dados/evangelho.json` |
| `obras_db.py` | API de *O Livro dos Médiuns*, *O Céu e o Inferno* e *A Gênese* (um livro por vez: `mediuns`, `ceu`, `genese`) |
| `extrair_obras.py` | Gera os bancos desses três livros a partir do PDF ou do texto, com validação |
| `dados/livro_dos_mediuns.zip`, `dados/ceu_e_inferno.zip`, `dados/genese.zip` | Bancos dos três livros; descompacte em `dados/` |

Teste: `python codificacao_db.py stats`

## Conteúdo e identificadores

1019 perguntas + 197 subperguntas, 29 capítulos, 161 seções, 495 páginas, 120 temas, Índice geral (668 assuntos), 191 comentários de Kardec, 19 itens numerados escritos por Kardec, 2 textos de Kardec sem número, 25 notas de rodapé, Introdução (dividida em 125 parágrafos, ids I1 a I125), Prolegômenos e Conclusão.

| Id | O que é |
|---|---|
| `919` / `919.a` | pergunta / subpergunta (aceita também `919a`, `"919 a"`) |
| `K919.a` | comentário de Kardec após a pergunta 919.a (só texto de Kardec; remissões soltas como "(540)" ficam no campo `referencia`, e avisos "N.E.:" no campo `nota_editora`) |
| `N4` | nota de rodapé 4 |
| `872` (tipo kardec) | item numerado escrito por Kardec, sem pergunta: 59, 100–113, 222, 257, 455, 872 (campo `texto`) |
| `Ke1`, `Ke2` | texto de Kardec sem número (início de seção), com `antes_de` = pergunta seguinte |
| `180-182` | faixa (inclui subperguntas) |

Listas aceitam `|`, `,` ou `;` como separador.

## O Evangelho segundo o Espiritismo

Banco separado em `dados/evangelho.json`, com API própria (`evangelho_db.py`, mesmo estilo de `codificacao_db.py`). 28 capítulos, 478 itens numerados, Prefácio, Introdução (partes I a IV e os 21 pontos do resumo da doutrina de Sócrates e Platão), 29 notas de rodapé. Cada item guarda capítulo, seção (subtítulo do livro), se é das Instruções dos Espíritos, autor e local/data da comunicação, texto em parágrafos, nota de Kardec (“Nota –”), notas de rodapé e páginas.

| Id | O que é |
|---|---|
| `5:4` | capítulo V, item 4 (capítulo:item, como se cita o livro) |
| `0:0` | Prefácio (O Espírito de Verdade) |
| `0:1` a `0:4` | Introdução, partes I a IV |
| `0:4.1` a `0:4.21` | Introdução IV, pontos I a XXI de Sócrates e Platão |
| `N4` | nota de rodapé 4 do Evangelho |

Listas e faixas: `"5:4-8, 5:20-6:3, 12:9 | N4"`; `V` ou `cap 5` numa lista = capítulo inteiro. Aceita também `V:4`, `V.4` e `"cap. V, item 4"`.

`python evangelho_db.py <comando> [args] [opções]` (lista completa: `python evangelho_db.py ajuda`)

| Para | Comando |
|---|---|
| Itens | `item 5:4` · `itens "5:4-8, N4"` · `vizinhos 5:4` · `aleatorio` |
| Estrutura | `capitulo 5` (ou `V`, `aflitos`) · `capitulos` · `secao "aflições"` · `secoes 12` · `prefacio` · `introducao` · `socrates` |
| Espíritos | `instrucoes 12` · `autor Fénelon` · `autores` · `local "Paris, 1862"` |
| Bíblia | `evangelho "Mateus, 5:17"` (entende faixas como `3:1 a 12`) · `grupo doentes` (preces do cap. XXVIII) |
| Busca | `buscar "perdão inimigos"` · `--modo frase` · `--capitulo 12` · `--instrucoes` · `--autor Agostinho` |
| Notas e páginas | `nota 4` · `notas` · `notas_kardec` · `pagina 120` |
| Outros | `ordenar "10:6, N4, 5:4"` · `exportar pasta` · `caminho itens/5:4/autor` · `stats` |

Opções: `--ids`, `--formato texto|json|ids|curto`, `--expandir`, `--campos texto,secao,autor,...`. Cada item sai com o rodapé de citação (`Evangelho segundo o Espiritismo, cap. BEM-AVENTURADOS OS AFLITOS, item 4`: nome do capítulo em caixa alta).

Blocos para os agentes: `python montar_blocos.py --evangelho [pasta]` gera 7 blocos de ~25 a 34 mil tokens, sempre com capítulos inteiros (Prefácio e Introdução + I–II, III–VI, VII–XI, XII–XV, XVI–XX, XXI–XXVII, XXVIII).

Gerar o banco de novo: `python3 extrair_evangelho.py O-evangelho-segundo-o-espiritismo.pdf -o dados/evangelho.json`

## O Livro dos Médiuns, O Céu e o Inferno e A Gênese

Três bancos no mesmo esquema do Evangelho (`meta`, `partes`, `capitulos`, `ordem`, `itens`, `notas`), com uma API comum: `python obras_db.py <livro> <comando> [args]`, em que `<livro>` é `mediuns` (`lm`), `ceu` (`ci`) ou `genese` (`ag`). A unidade é sempre a divisão numerada do próprio livro; cada unidade guarda parte, capítulo, seção, autor e local/data (comunicação assinada), parágrafos, notas, páginas e o rodapé de citação, com o nome do capítulo em caixa alta.

| Livro | Conteúdo |
|---|---|
| O Livro dos Médiuns (FEB, Guillon Ribeiro) | Introdução (11 parágrafos), 2 partes, 36 capítulos, 350 itens, Regulamento (preâmbulo + 29 artigos), 34 dissertações, 24 verbetes, 25 notas; ~234 mil tokens |
| O Céu e o Inferno (FEB, Manuel Quintão) | Primeira Parte (Doutrina, 11 capítulos) e Segunda Parte (Exemplos, 8 capítulos, 66 exemplos), 289 unidades, 70 notas; ~205 mil tokens |
| A Gênese (FEB, Guillon Ribeiro) | Introdução (12 parágrafos), 3 partes, 18 capítulos, 646 itens, 192 notas; ~200 mil tokens |

| Livro | Id | O que é | Citação |
|---|---|---|---|
| Médiuns | `159` | item 159 (1 a 350 no livro inteiro) | `Livro dos Médiuns, cap. DOS MÉDIUNS, item 159` |
| Médiuns | `I3` | Introdução, parágrafo 3 | `Livro dos Médiuns, INTRODUÇÃO` |
| Médiuns | `R5` (`R0`) | Regulamento, art. 5º (preâmbulo) | `…, cap. REGULAMENTO DA SOCIEDADE PARISIENSE DE ESTUDOS ESPÍRITAS, art. 5º` |
| Médiuns | `D12` (`D0`) | Dissertação XII (abertura do capítulo) | `Livro dos Médiuns, cap. DISSERTAÇÕES ESPÍRITAS, item XII` |
| Médiuns | `V3` | 3º verbete do Vocabulário espírita | `Livro dos Médiuns, cap. VOCABULÁRIO ESPÍRITA, Erraticidade` |
| Céu e Inferno | `7:3` (`7:0`) | Primeira Parte, cap. VII, item 3 (texto antes do item 1) | `Céu e Inferno, cap. O PORVIR E O NADA, item 3` |
| Céu e Inferno | `7:12` | Código penal da vida futura, 12º | `Céu e Inferno, cap. AS PENAS FUTURAS SEGUNDO O ESPIRITISMO, Código penal da vida futura, 12º` |
| Céu e Inferno | `E1:3` | Segunda Parte, cap. I (O passamento), item 3 | `Céu e Inferno, cap. O PASSAMENTO, item 3` |
| Céu e Inferno | `E2:1` / `E2:1.2` | Segunda Parte, cap. II, exemplo 1 / sua comunicação II | `Céu e Inferno, cap. ESPÍRITOS FELIZES, Sanson, II` |
| Gênese | `6:12` (`6:0`) | cap. VI, item 12 | `A Gênese, cap. URANOGRAFIA GERAL, item 12` |
| Gênese | `I3` | Introdução, parágrafo 3 | `A Gênese, INTRODUÇÃO` |
| os três | `N4` | nota de rodapé (as da Nota Explicativa e do Índice ficam de fora) | |

Nos exemplos do Céu e Inferno com comunicações numeradas pelo livro (I, II…), cada comunicação é uma unidade (`E2:1.1`, `E2:1.2`…); numa lista, o id do exemplo (`E2:1`) vale por todas. Listas e faixas: `"159-162, R5 | N4"`, `"6:3-8"`, `"E2:1-4"`; capítulo inteiro numa lista: `cap 14`, `XIV`, `2.14` (parte.capítulo) ou, no Céu e Inferno, `E4`.

| Para | Comando (`python obras_db.py <livro> …`) |
|---|---|
| Itens | `item 159` · `itens "159-162, R5, N4"` · `vizinhos 159` · `aleatorio` |
| Estrutura | `capitulo 14` (ou `XIV`, `2.14`, parte do título) · `capitulos` · `partes` · `secao "obsessão"` · `secoes 14` |
| Espíritos | `autor "São Luís"` · `autores` · `local Paris` |
| Busca | `buscar "obsessão orgulho"` · `--modo frase` · `--capitulo 23` · `--autor Erasto` |
| Notas e páginas | `nota 4` · `notas` · `pagina 120` |
| Próprios | `mediuns introducao \| regulamento \| dissertacoes \| vocabulario [termo]` · `ceu exemplo Sanson \| exemplos E5 \| codigo_penal` · `genese introducao \| grupo fluidos` |
| Outros | `ordenar "R5, 159, N4"` · `exportar pasta` · `caminho itens/159/texto` · `stats` |

Blocos para os agentes: `python montar_blocos.py --mediuns|--ceu|--genese [pasta]` gera 8 blocos de ~16 a 36 mil tokens por livro, sempre com capítulos inteiros (partição que minimiza o maior bloco). Gerar os bancos de novo: `python3 extrair_obras.py mediuns|ceu|genese <PDF ou texto>`; o extrator confere o sumário do livro, a numeração de cada capítulo e a cobertura palavra por palavra.

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
| Introdução | `anotacao I8` (parágrafo 8) · ids I1 a I125 em ordem, usados também nas matrizes e na busca (`--tipos introducao`) |
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
| `--max-caracteres N` | tamanho de cada parte (padrão 45000; `0` = um arquivo só) |
| `--evangelho` | O Evangelho segundo o Espiritismo (automático com ids `capítulo:item`) |
| `--livro mediuns\|ceu\|genese` (ou `--mediuns`, `--ceu`, `--genese`) | os outros três livros; obrigatório, porque os ids deles não se distinguem sozinhos. O mesmo `--livro` vale para `situacao.py matriz` |

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


### Modelo via ONNX (sem HuggingFace)

Se o HuggingFace estiver bloqueado (ex.: algumas nuvens), o bge-m3 pode vir do GitHub:

```
pip install onnxruntime onnxruntime-extensions numpy rank_bm25
# baixe o onnx.zip de https://github.com/yuniko-software/bge-m3-onnx/releases (1,3 GB)
# e extraia os 3 arquivos .onnx em  modelo_onnx/   (ou defina BGE_M3_ONNX=/pasta)
python busca.py indexar --modelo onnx
```

Sem o reranker (que só existe no HuggingFace) as notas são relativas (o melhor = 100%), não absolutas.
Medido numa nuvem com 2 CPUs: índice em ~17 min, abrir em 2,5 s, consulta com 4 dúvidas em ~0,8 s.
