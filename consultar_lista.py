#!/usr/bin/env python3
"""consultar_lista.py — transforma uma lista de identificadores em um único arquivo de texto.

Recebe a lista devolvida pela skill (ex.: "180 | 181 | K181 | 182.b | N4" ou "180, 181, K181"),
separa (split), limpa (strip), consulta cada item na API local (codificacao_db.py) e junta
tudo em UM arquivo temporário, na ordem do livro e sem duplicatas. Assim uma IA lê o arquivo
de uma vez só (um bloco, que fica em cache) em vez de fazer uma consulta por pergunta.

Uso:
  python consultar_lista.py "180 | 181 | K181 | 182.b | N4"
  python consultar_lista.py "180, 181, 200-202" -o minha_consulta.txt
  echo "180|K181" | python consultar_lista.py            (lê da entrada padrão)
  python consultar_lista.py "180|181" --completo          (inclui comentários/notas de todas)
  python consultar_lista.py "180|181" --manter-ordem      (mantém a ordem recebida)

Saída: imprime o caminho do(s) arquivo(s) gerado(s), um por linha (padrão: pasta temporária).
Listas grandes são divididas em partes de até --max-caracteres (padrão 45000), sem cortar itens.
Aceita também a matriz da parte 1: "[['180', 95, 75], ['K181', 40, 30]]" (usa os ids e mostra a
relevância de cada item no cabeçalho dele). Separadores aceitos: | , ;   Faixas: 180-182.  Ids: 182.b (pergunta), K919.a (comentário
de Kardec), N4 (nota de rodapé). Identificadores inválidos são listados no fim do arquivo.
"""
import argparse
import os
import re
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codificacao_db import LivroDosEspiritos, ErroConsulta, ARQUIVO_PADRAO  # noqa: E402


def ler_matriz(lista):
    """Matriz da skill perguntas-livro-espiritos: [['180', 95, 75], ...] -> {'180': 75, ...}.
    Devolve None se a entrada não for uma matriz."""
    t = lista.strip()
    if not t.startswith("["):
        return None
    import ast
    try:
        m = ast.literal_eval(t)
    except (ValueError, SyntaxError):
        return None
    return {str(x[0]).strip(): (x[2] if len(x) > 2 else None) for x in m
            if isinstance(x, (list, tuple)) and x}


def separar(lista):
    """split + strip: '180 | 181 , K181' -> ['180', '181', 'K181']; aceita também a matriz."""
    m = ler_matriz(lista)
    if m is not None:
        return list(m)
    return [x.strip() for x in re.split(r"[|,;\n]+", lista) if x.strip() and x.strip().upper() != "NENHUMA"]


def bloco_pergunta(le, i, completo, pedidos=()):
    p = le.pergunta(i)  # já vem completa (título do capítulo, página, notas)
    linhas = [f"[{p['id']}]  p.{p['pagina']}  {p['capitulo_titulo']}"]
    if p.get("tipo") == "kardec":
        linhas.append(f"Kardec (texto numerado): {p['texto']}")
    else:
        linhas.append(f"P: {p['pergunta']}")
    if p.get("resposta"):
        linhas.append(f"R: {p['resposta']}")
    if p.get("assinatura"):
        linhas.append(f"Assinado: {p['assinatura']}")
    if p.get("referencia"):
        linhas.append(f"Referência: {p['referencia']}")
    if p.get("nota_editora"):
        linhas.append(f"N.E.: {p['nota_editora']}")
    if completo:
        if p.get("comentario") and f"K{p['id']}" not in pedidos:
            linhas.append(f"Kardec [K{p['id']}]: {p['comentario']}")
        for n in p.get("notas", []):
            nid = "N" + n[1:].split("]")[0]
            if nid not in pedidos:  # não repete o que já vem como item próprio
                linhas.append(f"Nota [{nid}]{n.split(']', 1)[1]}")
    return "\n".join(linhas)


def bloco_anotacao(le, ref):
    a = le.anotacao(ref)
    if a["tipo"] == "texto_kardec":
        return (f"[{a['id']}]  p.{a['pagina']}  Texto de Kardec sem número ({a['capitulo']}, "
                f"{a['secao'] or 'início do capítulo'}, antes da pergunta {a['antes_de']})\n{a['texto']}")
    if a["tipo"] == "comentario_kardec":
        return f"[{a['id']}]  p.{a['pagina']}  Comentário de Kardec à pergunta {a['pergunta']}\n{a['texto']}"
    lig = f" (ligada a: {', '.join(a['perguntas'])})" if a["perguntas"] else ""
    return f"[{a['id']}]  p.{a['pagina']}  Nota de rodapé — {a['autor']}{lig}\n{a['texto']}"


def montar(le, lista, completo=False, manter_ordem=False):
    notas = ler_matriz(lista) or {}
    itens, invalidos = [], []
    for x in separar(lista):
        try:
            itens += le.ordenar(x)          # normaliza e expande faixas (180-182)
        except (ErroConsulta, KeyError, ValueError):
            invalidos.append(x)
    if manter_ordem:
        itens = list(dict.fromkeys(itens))  # remove duplicatas, mantém a ordem recebida
    else:
        itens = le.ordenar(", ".join(itens)) if itens else []
    blocos = []
    for i in itens:
        try:
            b = bloco_anotacao(le, i) if i[:1] in "KN" else bloco_pergunta(le, i, completo, set(itens))
            if notas.get(i) is not None:            # relevância dada pela parte 1
                cab_item, _, resto = b.partition("\n")
                b = f"{cab_item}  relevância {notas[i]:g}%\n{resto}"
            blocos.append(b)
        except (ErroConsulta, KeyError, ValueError):
            invalidos.append(i)
    cab = (f"O Livro dos Espíritos — consulta de {len(blocos)} itens "
           f"({datetime.now():%d/%m/%Y %H:%M})\nIds: {' | '.join(itens)}")
    if invalidos:
        blocos.append("Não encontrados: " + " | ".join(invalidos))
    return cab, blocos, itens, invalidos


def dividir(cab, blocos, max_chars):
    """Divide os blocos em partes de até max_chars (sem cortar um item no meio)."""
    partes, atual = [], []
    for b in blocos:
        if atual and len("\n\n".join(atual + [b])) > max_chars:
            partes.append(atual)
            atual = []
        atual.append(b)
    if atual or not partes:
        partes.append(atual)
    n = len(partes)
    return [(f"{cab}\nParte {i}/{n}" if n > 1 else cab) + "\n\n" + "\n\n".join(p) + "\n"
            for i, p in enumerate(partes, 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lista", nargs="?", help="ids separados por | , ou ; ou a matriz [['id', tokens, nota], ...] "
                                                "(sem isso, lê da entrada padrão)")
    ap.add_argument("-o", "--saida", help="arquivo de saída (padrão: arquivo temporário)")
    ap.add_argument("--completo", action="store_true", help="inclui comentário de Kardec e notas de cada pergunta")
    ap.add_argument("--manter-ordem", action="store_true", help="não reordena pela ordem do livro")
    ap.add_argument("--max-caracteres", type=int, default=45000,
                    help="tamanho máximo de cada arquivo; acima disso divide em partes (0 = nunca dividir). "
                         "Padrão 45000: com 60000 a leitura de uma IA chegou a ser truncada")
    ap.add_argument("--banco", default=ARQUIVO_PADRAO, help="caminho do JSON do banco")
    a = ap.parse_args()
    lista = a.lista if a.lista is not None else sys.stdin.read()
    if not lista.strip():
        ap.error("informe a lista de identificadores")
    le = LivroDosEspiritos(a.banco)
    cab, blocos, itens, invalidos = montar(le, lista, a.completo, a.manter_ordem)
    textos = dividir(cab, blocos, a.max_caracteres if a.max_caracteres > 0 else float("inf"))
    if a.saida:
        base, ext = os.path.splitext(a.saida)
        caminhos = [a.saida] if len(textos) == 1 else [f"{base}_parte{i}{ext or '.txt'}" for i in range(1, len(textos) + 1)]
    else:
        pasta = tempfile.mkdtemp(prefix="consulta_le_")
        caminhos = [os.path.join(pasta, f"parte{i}.txt") for i in range(1, len(textos) + 1)]
    for c, t in zip(caminhos, textos):
        with open(c, "w", encoding="utf-8") as f:
            f.write(t)
    print("\n".join(caminhos))
    print(f"{len(itens)} itens, {sum(map(len, textos))} caracteres, {len(textos)} arquivo(s)"
          + (f", {len(invalidos)} não encontrados" if invalidos else ""), file=sys.stderr)

if __name__ == "__main__":
    main()
