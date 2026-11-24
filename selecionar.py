"""Escolhe, de uma matriz [['id', tokens, nota], ...], os itens de maior nota até um limite de tokens.

    python3 selecionar.py "<matriz>" 15000
    python3 selecionar.py "<matriz>" 15000 --pular     # pula o que não cabe e continua

Ordem de escolha: maior nota primeiro; em empate, o de menos tokens. Por padrão, a seleção
termina no primeiro item que estourar o limite: tudo o que entra tem nota maior ou igual a tudo
o que fica de fora. Com --pular, um item que não cabe é pulado e a busca continua (enche mais o
limite, mas pode deixar de fora um item de nota alta e pôr outros de nota baixa no lugar).
Saída (stdout): a matriz escolhida, na ordem do livro. Resumo (stderr): itens, tokens, nota mínima.
"""
import argparse
import ast
import sys


def selecionar(matriz, limite, pular=False):
    ordem = {linha[0]: k for k, linha in enumerate(matriz)}      # a matriz já vem na ordem do livro
    escolhidos, total = [], 0
    for linha in sorted(matriz, key=lambda x: (-x[2], x[1])):
        if total + linha[1] > limite:
            if pular:
                continue
            break
        escolhidos.append(linha)
        total += linha[1]
    escolhidos.sort(key=lambda x: ordem[x[0]])
    return escolhidos, total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matriz", help="matriz Python [['id', tokens, nota], ...]")
    ap.add_argument("limite", type=int, help="número máximo de tokens")
    ap.add_argument("--pular", action="store_true", help="pula o item que não cabe e continua")
    a = ap.parse_args()
    try:
        m = [[str(x[0]), int(x[1]), float(x[2])] for x in ast.literal_eval(a.matriz.strip())]
    except Exception as e:
        sys.exit(f"Matriz inválida: {e}")
    sel, total = selecionar(m, a.limite, a.pular)
    print(repr([[i, t, int(n) if n == int(n) else n] for i, t, n in sel]))
    minima = min((x[2] for x in sel), default=0)
    print(f"{len(sel)} de {len(m)} itens, {total} de {a.limite} tokens, nota mínima {minima:g}%",
          file=sys.stderr)
