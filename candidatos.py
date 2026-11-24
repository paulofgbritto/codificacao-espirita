"""Busca de perguntas de O Livro dos Espíritos para a skill copia-pergunta.

Modo padrão (rápido): uma busca só, lista as 30 perguntas mais parecidas com a do usuário
(com o id entre colchetes) e mostra um trecho da resposta das 3 primeiras.

    python3 candidatos.py "o que é espírito?"            # = rapido, 30 perguntas
    python3 candidatos.py rapido "o que é espírito?" 60  # mais perguntas
    python3 candidatos.py resposta 23                    # resposta do Espírito, no formato final

Modo antigo, em lotes conferidos por um agente (mais lento; só se for realmente necessário):

    python3 candidatos.py lote "o que é espírito?" 1 saida.txt   # lote 1 = 10, 2 = 30, 3 a 6 = 40
    python3 candidatos.py conferir saida.txt "CODIGO;1:N,2:N,...:S"

Usa o índice em indice/ (já vem no repositório) e o modelo em modelo_onnx/.
"""
import json
import random
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

# Lote 1 é pequeno (a equivalente quase sempre está entre as primeiras); depois crescem.
TAMANHOS = [10, 30, 40, 40, 40, 40]
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
    n = int(numero)
    if not 1 <= n <= len(TAMANHOS):
        sys.exit(f"lote deve ser de 1 a {len(TAMANHOS)}")
    ini = sum(TAMANHOS[:n - 1])
    parte = ids[ini:ini + TAMANHOS[n - 1]]
    linhas, mapa = [], {}
    for k, i in enumerate(parte, 1):
        it = b.itens[b.pos[i]]
        r = re.sub(r"\s+", " ", it["resposta"]).strip()
        if len(r) > MAX_RESPOSTA:
            r = r[:MAX_RESPOSTA].rsplit(" ", 1)[0] + " [...]"
        p = re.sub(r"\s+", " ", it["pergunta"]).strip()
        linhas.append(f"#{k}\nP: {p}\nR: {r}\n")
        mapa[k] = i
    # Código que só aparece no FIM do arquivo: prova que o avaliador leu tudo.
    codigo = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
    linhas.append(f"CODIGO-DE-LEITURA: {codigo}\n")
    Path(saida).write_text("\n".join(linhas), encoding="utf-8")
    Path(str(saida) + ".mapa.json").write_text(
        json.dumps({"mapa": mapa, "codigo": codigo}), encoding="utf-8")
    print(f"lote {numero}: posições {ini + 1}-{ini + len(parte)} de {len(ids)} perguntas -> {saida}")


def conferir(saida, veredito):
    dados = json.loads(Path(str(saida) + ".mapa.json").read_text())
    mapa = {int(k): v for k, v in dados["mapa"].items()}
    if dados["codigo"] not in veredito.upper():
        print("INVALIDO: faltou o CODIGO-DE-LEITURA (o avaliador não leu o arquivo até o fim).")
        sys.exit(1)
    vistos = {int(n): s.upper() for n, s in re.findall(r"(\d+)\s*:\s*([SN])", veredito, re.I)}
    faltam = sorted(set(mapa) - set(vistos))
    if faltam:
        print("INCOMPLETO: faltam os números " + ", ".join(map(str, faltam)))
        sys.exit(1)
    sim = [mapa[n] for n in sorted(vistos) if vistos[n] == "S" and n in mapa]
    print("COMPLETO. Equivalentes: " + (", ".join(sim) if sim else "NENHUMA"))


def resposta(*pids):
    """Imprime, no formato final, uma ou mais perguntas (cada uma com a citação embaixo)."""
    for k, pid in enumerate(pids):
        if k:
            print()
        _uma(pid)


def _uma(pid):
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
    print("\nLivro dos Espíritos")


def rapido(pergunta, n="30"):
    """Uma busca só: lista as n primeiras perguntas (id + pergunta) e a resposta das 3 primeiras."""
    b, ids = _ordem(pergunta)
    for k, i in enumerate(ids[:int(n)], 1):
        it = b.itens[b.pos[i]]
        p = re.sub(r"\s+", " ", it["pergunta"]).strip()
        print(f"{k:>2} [{i}] {p[:170]}")
        if k <= 3:
            r = re.sub(r"\s+", " ", it["resposta"]).strip()
            print(f"      R: {r[:260]}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["ajuda"]
    comandos = {"lote": lote, "conferir": conferir, "resposta": resposta, "rapido": rapido}
    if cmd == "ajuda":
        print(__doc__)
    elif cmd in comandos:
        comandos[cmd](*args)
    else:                      # padrão: o primeiro argumento já é a pergunta
        rapido(cmd, *args)
