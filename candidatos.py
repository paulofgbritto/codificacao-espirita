"""Lotes de candidatos para a skill copia-pergunta.

Ordena as perguntas de O Livro dos Espíritos pela semelhança com a pergunta do usuário
e grava um lote numerado (pergunta + começo da resposta), pequeno o bastante para ser
lido de uma vez só.

    python3 candidatos.py lote "o que é espírito?" 1 saida.txt     # posições 1-40
    python3 candidatos.py lote "o que é espírito?" 2 saida.txt     # posições 41-80
    python3 candidatos.py conferir saida.txt "1:N,2:N,...,40:S"    # todos os números vieram?
    python3 candidatos.py resposta 23                              # resposta do Espírito, inteira

Usa o índice em indice/ (já vem no repositório) e o modelo em modelo_onnx/.
"""
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

TAMANHO_LOTE = 40
MAX_RESPOSTA = 700   # caracteres da resposta mostrados ao avaliador


def _ordem(pergunta):
    import busca
    b = busca.Buscador(usar_reranker=False)
    notas = b.pontuar(pergunta, candidatos=0, rerank=False)
    ids = [i for i in sorted(notas, key=lambda i: -notas[i])
           if b.itens[b.pos[i]]["tipo"] == "pergunta"]
    return b, ids


def lote(pergunta, numero, saida):
    b, ids = _ordem(pergunta)
    ini = (int(numero) - 1) * TAMANHO_LOTE
    parte = ids[ini:ini + TAMANHO_LOTE]
    linhas, mapa = [], {}
    for k, i in enumerate(parte, 1):
        it = b.itens[b.pos[i]]
        r = re.sub(r"\s+", " ", it["resposta"]).strip()
        if len(r) > MAX_RESPOSTA:
            r = r[:MAX_RESPOSTA].rsplit(" ", 1)[0] + " [...]"
        p = re.sub(r"\s+", " ", it["pergunta"]).strip()
        linhas.append(f"#{k}\nP: {p}\nR: {r}\n")
        mapa[k] = i
    Path(saida).write_text("\n".join(linhas), encoding="utf-8")
    Path(str(saida) + ".mapa.json").write_text(json.dumps(mapa), encoding="utf-8")
    print(f"lote {numero}: posições {ini + 1}-{ini + len(parte)} de {len(ids)} perguntas -> {saida}")


def conferir(saida, veredito):
    mapa = {int(k): v for k, v in json.loads(Path(str(saida) + ".mapa.json").read_text()).items()}
    vistos = {int(n): s.upper() for n, s in re.findall(r"(\d+)\s*:\s*([SN])", veredito, re.I)}
    faltam = sorted(set(mapa) - set(vistos))
    if faltam:
        print("INCOMPLETO: faltam os números " + ", ".join(map(str, faltam)))
        sys.exit(1)
    sim = [mapa[n] for n in sorted(vistos) if vistos[n] == "S" and n in mapa]
    print("COMPLETO. Equivalentes: " + (", ".join(sim) if sim else "NENHUMA"))


def resposta(pid):
    from codificacao_db import LivroDosEspiritos
    le = LivroDosEspiritos()
    p = le.P.get(pid)
    if not p or p["tipo"] != "pergunta":
        sys.exit(f"{pid} não é uma pergunta do livro.")
    # Formato da skill copia-pergunta: tudo entre aspas, recuo de parágrafo (espaço eme),
    # "[x] — pergunta" em fonte normal e "— resposta" em itálico; citação embaixo.
    recuo = " "
    resp = p["resposta"].strip().strip("“”\"").strip()
    pars = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"\n\s*\n|\n", resp) if x.strip()]
    linhas = [f"“{recuo}[{pid}] — {p['pergunta'].strip()}"]
    for k, par in enumerate(pars):
        linhas.append(f"{recuo}{'— ' if k == 0 else ''}*{par}*")
    linhas[-1] += "”"
    print("  \n".join(linhas))
    print(f"\nLivro dos Espíritos, pergunta {pid}.")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["ajuda"]
    {"lote": lote, "conferir": conferir, "resposta": resposta}.get(
        cmd, lambda *a: print(__doc__))(*args)
