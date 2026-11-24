"""Pré-seleção para a skill perguntas-livro-espiritos (parte 1).

Em vez de cada agente ler o livro inteiro (8 blocos, ~200 mil tokens), a busca local
(embeddings + BM25, sem IA na nuvem) separa os itens mais prováveis para CADA consulta
(situação e cada dúvida) e grava um arquivo único, na ordem do livro, com a estimativa
de tokens de cada item. Um só agente lê esse arquivo e dá as notas.

    python3 situacao.py pool "SITUAÇÃO" saida.txt --duvida "D1" --duvida "D2" [-k 40]
    python3 situacao.py conferir saida.txt "[['873', 95, 80], ['K873', 40, 35]]" [--min 30]
    python3 situacao.py matriz "<respostas dos agentes, coladas uma após a outra>" [--min 30]
        junta as matrizes dos agentes, tira duplicatas (fica a maior nota), põe na ordem
        do livro e corrige os tokens pelo banco. Saída: [['id', tokens, nota], ...]

Tokens: estimativa (caracteres / 3,5), não a contagem exata do modelo.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))


def tokens_aprox(texto):
    return max(1, round(len(texto) / 3.5))


def _texto(it):
    p = re.sub(r"[ \t]+", " ", it["pergunta"]).strip()
    r = re.sub(r"[ \t]+", " ", it["resposta"]).strip()
    return f"P: {p}\nR: {r}" if p else r


def pool(situacao, saida, duvidas, k):
    import busca
    b = busca.Buscador(usar_reranker=False)
    consultas = [situacao] + [d for d in duvidas if d.strip()]
    fus = b._rrf(b._denso(consultas), b._bm25(consultas))          # consultas x itens
    escolhidos = set()
    for linha in fus:                                               # top-k de CADA consulta
        escolhidos.update(np.argsort(-linha)[:k].tolist())
    ordem = sorted(escolhidos)                                      # ordem do livro
    blocos, tok = [], {}
    for i in ordem:
        it = b.itens[i]
        txt = _texto(it)
        t = tokens_aprox(txt)
        tok[it["id"]] = t
        blocos.append(f"[{it['id']}] (tokens: {t})\n{txt}\n")
    Path(saida).write_text("\n".join(blocos), encoding="utf-8")
    Path(str(saida) + ".tok.json").write_text(json.dumps(tok), encoding="utf-8")
    total = sum(tok.values())
    print(f"{len(ordem)} itens, ~{total} tokens -> {saida}")


def conferir(saida, matriz, minimo):
    tok = json.loads(Path(str(saida) + ".tok.json").read_text(encoding="utf-8"))
    try:
        m = ast.literal_eval(matriz.strip())
    except Exception as e:
        sys.exit(f"INVALIDO: não é uma matriz Python ({e})")
    if not isinstance(m, list):
        sys.exit("INVALIDO: não é uma lista")
    ok, erros = [], []
    for linha in m:
        if not (isinstance(linha, (list, tuple)) and len(linha) == 3):
            erros.append(f"formato {linha!r}")
            continue
        i, t, p = str(linha[0]), linha[1], linha[2]
        if i not in tok:
            erros.append(f"id fora do arquivo: {i}")
            continue
        if p < minimo:
            continue
        ok.append([i, tok[i], p])                     # tokens sempre os do arquivo
    if erros:
        print("AVISOS: " + "; ".join(erros), file=sys.stderr)
    ordem = list(tok)                                 # o arquivo já está na ordem do livro
    ok.sort(key=lambda x: ordem.index(x[0]))
    print(repr(ok))


def matriz(texto, minimo):
    from busca import carregar_itens
    from codificacao_db import LivroDosEspiritos
    itens = carregar_itens(LivroDosEspiritos())
    pos = {it["id"]: k for k, it in enumerate(itens)}
    melhor, invalidos = {}, []
    for bloco in re.findall(r"\[\s*\[.*?\]\s*\]", texto, re.S):
        for linha in ast.literal_eval(bloco):
            i, nota = str(linha[0]).strip(), float(linha[-1])
            if i not in pos:
                invalidos.append(i)
                continue
            melhor[i] = max(nota, melhor.get(i, 0))
    if invalidos:
        print("AVISO: ids inexistentes ignorados: " + ", ".join(invalidos), file=sys.stderr)
    res = [[i, tokens_aprox(_texto(itens[pos[i]])), int(round(n))]
           for i, n in melhor.items() if n >= minimo]
    res.sort(key=lambda x: pos[x[0]])
    print(repr(res))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pool")
    a.add_argument("situacao"); a.add_argument("saida")
    a.add_argument("--duvida", action="append", default=[])
    a.add_argument("-k", type=int, default=40)
    c = sub.add_parser("conferir")
    c.add_argument("saida"); c.add_argument("matriz")
    c.add_argument("--min", type=float, default=30)
    m = sub.add_parser("matriz")
    m.add_argument("texto"); m.add_argument("--min", type=float, default=30)
    x = ap.parse_args()
    if x.cmd == "matriz":
        matriz(x.texto, x.min)
    elif x.cmd == "pool":
        pool(x.situacao, x.saida, x.duvida, x.k)
    else:
        conferir(x.saida, x.matriz, x.min)
