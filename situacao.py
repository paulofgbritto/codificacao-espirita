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
        O Evangelho segundo o Espiritismo: ids capítulo:item ('5:4', '0:4.3', 'N13') são
        reconhecidos sozinhos; para uma matriz só de notas N#, use --evangelho.
        O Livro dos Médiuns, O Céu e o Inferno e A Gênese (obras_db.py): sempre com
        --livro mediuns | ceu | genese (os ids desses livros não se distinguem sozinhos).

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


def matriz_evangelho(texto, minimo):
    from evangelho_db import Evangelho, tokens_aprox as tok_ev
    ev = Evangelho()
    melhor, invalidos = {}, []
    for bloco in re.findall(r"\[\s*\[.*?\]\s*\]", texto, re.S):
        for linha in ast.literal_eval(bloco):
            i, nota = str(linha[0]).strip(), float(linha[-1])
            try:
                i = ev.ordenar(i)[0]            # normaliza (V:4 -> 5:4) e confere se existe
            except Exception:
                invalidos.append(i)
                continue
            melhor[i] = max(nota, melhor.get(i, 0))
    if invalidos:
        print("AVISO: ids inexistentes ignorados: " + ", ".join(invalidos), file=sys.stderr)
    ids = [i for i in ev.ordenar(", ".join(melhor)) if melhor[i] >= minimo] if melhor else []
    res = [[i, tok_ev(ev.N[i]["texto"]) if i.startswith("N") else ev.item(i)["tokens"], int(round(melhor[i]))]
           for i in ids]
    print(repr(res))


def matriz_obra(texto, minimo, livro):
    from obras_db import Obra, tokens_aprox as tok_ob
    ob = Obra(livro)
    melhor, invalidos = {}, []
    for bloco in re.findall(r"\[\s*\[.*?\]\s*\]", texto, re.S):
        for linha in ast.literal_eval(bloco):
            i, nota = str(linha[0]).strip(), float(linha[-1])
            try:
                ids = ob.ordenar(i)             # normaliza (VII:3 -> 7:3; E2:1 dividido -> suas comunicações)
            except Exception:
                ids = []
            if not ids:
                invalidos.append(i)
                continue
            for j in ids:
                melhor[j] = max(nota, melhor.get(j, 0))
    if invalidos:
        print("AVISO: ids inexistentes ignorados: " + ", ".join(invalidos), file=sys.stderr)
    ids = [i for i in ob.ordenar(", ".join(melhor)) if melhor[i] >= minimo] if melhor else []
    res = [[i, tok_ob(ob.N[i]["texto"]) if i.startswith("N") else tok_ob(ob.I[i]["texto"]), int(round(melhor[i]))]
           for i in ids]
    print(repr(res))


def eh_evangelho(texto):
    return bool(re.search(r"\[\s*['\"]\d{1,2}:\d", texto))


def matriz(texto, minimo, evangelho=False, livro=None):
    if livro in ("mediuns", "ceu", "genese"):
        return matriz_obra(texto, minimo, livro)
    if evangelho or livro == "evangelho" or eh_evangelho(texto):
        return matriz_evangelho(texto, minimo)
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
    m.add_argument("--evangelho", action="store_true", help="O Evangelho segundo o Espiritismo")
    m.add_argument("--livro", choices=["espiritos", "evangelho", "mediuns", "ceu", "genese"],
                   help="livro da matriz (obrigatório para mediuns, ceu e genese)")
    x = ap.parse_args()
    if x.cmd == "matriz":
        matriz(x.texto, x.min, x.evangelho, x.livro)
    elif x.cmd == "pool":
        pool(x.situacao, x.saida, x.duvida, x.k)
    else:
        conferir(x.saida, x.matriz, x.min)
