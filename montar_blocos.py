"""Gera os blocos que os agentes Haiku leem, sempre com capítulos inteiros.

Uso:
  python montar_blocos.py [pasta_saida]               O Livro dos Espíritos: 8 blocos (padrão: blocos/)
  python montar_blocos.py --evangelho [pasta_saida]   O Evangelho segundo o Espiritismo: 7 blocos
                                                      (padrão: blocos_evangelho/)
Livro dos Espíritos: exporta a Introdução (INTRO) e os 29 capítulos com codificacao_db.py e junta-os
em bloco1.txt ... bloco8.txt de tamanho parecido.
Evangelho: junta CAP00 (Prefácio e Introdução) e CAP01 ... CAP28 (evangelho_db.py) em bloco1.txt ...
bloco7.txt. Nenhum capítulo é dividido entre blocos: um item pode depender do capítulo inteiro.
Cada item sai com "(tokens: N)" logo após o [id], para o agente copiar na resposta.
Não usa IA: não gasta tokens.
"""
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))

# Agrupamento testado (cada bloco ~45-125 KB; P2C06 e P2C09 são capítulos grandes)
BLOCOS = [
    ["P1C01", "P1C02", "P1C03", "P1C04", "P2C01"],
    ["P2C02", "P2C03", "P2C04", "P2C05"],
    ["P2C06", "P2C07"],
    ["INTRO", "P2C08"],       # a Introdução (I1 a I125) vai no bloco 4, o menor
    ["P2C09", "P2C10", "P2C11", "P3C01"],
    ["P3C02", "P3C03", "P3C04", "P3C05", "P3C06", "P3C07", "P3C08"],
    ["P3C09", "P3C10", "P3C11", "P3C12"],
    ["P4C01", "P4C02"],
]


# Evangelho: capítulos em ordem, divididos em 7 blocos de ~25-34 mil tokens (partição que minimiza o
# maior bloco sem cortar capítulos; o cap. XXVIII, das preces, tem ~30 mil tokens e fica sozinho).
BLOCOS_EVANGELHO = [
    [0, 1, 2],                   # Prefácio e Introdução, I, II       (~25 mil tokens)
    [3, 4, 5, 6],                # III a VI                           (~32 mil)
    [7, 8, 9, 10, 11],           # VII a XI                           (~32 mil)
    [12, 13, 14, 15],            # XII a XV                           (~30 mil)
    [16, 17, 18, 19, 20],        # XVI a XX                           (~33 mil)
    [21, 22, 23, 24, 25, 26, 27],  # XXI a XXVII                      (~34 mil)
    [28],                        # XXVIII – Coletânea de preces        (~30 mil)
]


def montar_evangelho(saida):
    sys.path.insert(0, AQUI)
    from evangelho_db import Evangelho, tokens_aprox
    ev = Evangelho()
    assert sorted(c for b in BLOCOS_EVANGELHO for c in b) == sorted(ev.C), "BLOCOS_EVANGELHO não cobre 0 a 28"
    for i, caps in enumerate(BLOCOS_EVANGELHO, 1):
        destino = os.path.join(saida, f"bloco{i}.txt")
        texto = "\n".join(ev.texto_capitulo(c) for c in caps)
        with open(destino, "w", encoding="utf-8") as out:
            out.write(texto)
        print(destino, os.path.getsize(destino), f"~{tokens_aprox(texto)} tokens", "caps", caps)


def _marcar_tokens(caminho):
    """Põe '(tokens: N)' logo após o [id] de cada item, para o agente copiar na resposta."""
    import re
    sys.path.insert(0, AQUI)
    from busca import carregar_itens
    from codificacao_db import LivroDosEspiritos
    from situacao import _texto, tokens_aprox
    tok = {it["id"]: tokens_aprox(_texto(it)) for it in carregar_itens(LivroDosEspiritos())}
    linhas = open(caminho, encoding="utf-8").read().split("\n")
    for k, l in enumerate(linhas):
        m = re.match(r"\[([^\]]+)\] ", l)
        if m and m.group(1) in tok and "(tokens:" not in l[:40]:
            linhas[k] = f"[{m.group(1)}] (tokens: {tok[m.group(1)]}) " + l[m.end():]
    open(caminho, "w", encoding="utf-8").write("\n".join(linhas))


def main():
    args = [x for x in sys.argv[1:] if x != "--evangelho"]
    if "--evangelho" in sys.argv[1:]:
        saida = os.path.abspath(args[0] if args else os.path.join(AQUI, "blocos_evangelho"))
        os.makedirs(saida, exist_ok=True)
        montar_evangelho(saida)
        return
    saida = os.path.abspath(args[0] if args else os.path.join(AQUI, "blocos"))
    os.makedirs(saida, exist_ok=True)
    with tempfile.TemporaryDirectory() as caps:
        subprocess.run(
            [sys.executable, os.path.join(AQUI, "codificacao_db.py"), "exportar", caps],
            check=True, cwd=AQUI, stdout=subprocess.DEVNULL,
        )
        for i, caps_bloco in enumerate(BLOCOS, 1):
            destino = os.path.join(saida, f"bloco{i}.txt")
            with open(destino, "w", encoding="utf-8") as out:
                for cap in caps_bloco:
                    with open(os.path.join(caps, f"{cap}.txt"), encoding="utf-8") as f:
                        out.write(f.read())
            _marcar_tokens(destino)
            print(destino, os.path.getsize(destino))


if __name__ == "__main__":
    main()
