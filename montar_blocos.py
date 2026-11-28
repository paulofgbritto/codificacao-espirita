"""Gera os blocos que os agentes Haiku leem, sempre com capítulos inteiros.

Uso:
  python montar_blocos.py [pasta_saida]               O Livro dos Espíritos: 8 blocos (padrão: blocos/)
  python montar_blocos.py --evangelho [pasta_saida]   O Evangelho segundo o Espiritismo: 7 blocos
                                                      (padrão: blocos_evangelho/)
  python montar_blocos.py --mediuns [pasta_saida]     O Livro dos Médiuns: 8 blocos (padrão: blocos_mediuns/)
  python montar_blocos.py --ceu [pasta_saida]         O Céu e o Inferno: 8 blocos (padrão: blocos_ceu/)
  python montar_blocos.py --genese [pasta_saida]      A Gênese: 8 blocos (padrão: blocos_genese/)
Livro dos Espíritos: exporta a Introdução (INTRO) e os 29 capítulos com codificacao_db.py e junta-os
em bloco1.txt ... bloco8.txt de tamanho parecido.
Evangelho: junta CAP00 (Prefácio e Introdução) e CAP01 ... CAP28 (evangelho_db.py) em bloco1.txt ...
bloco7.txt. Nenhum capítulo é dividido entre blocos: um item pode depender do capítulo inteiro.
Médiuns, Céu e Inferno e Gênese: capítulos exportados por obras_db.py (P0C00 = Introdução), juntos em
bloco1.txt ... bloco8.txt pela partição que minimiza o maior bloco sem cortar capítulos.
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


# Médiuns, Céu e Inferno e Gênese: chaves parte.capítulo de obras_db.py ("0.0" = Introdução), em 8 blocos
# de ~16-36 mil tokens (menor bloco máximo possível sem cortar capítulos; desempate: blocos mais parecidos).
BLOCOS_OBRAS = {
    "mediuns": [
        ["0.0", "1.1", "1.2", "1.3", "1.4"],                   # Introdução e Primeira Parte   (~31 mil tokens)
        ["2.1", "2.2", "2.3", "2.4", "2.5"],                   # II, I a V                     (~28 mil)
        ["2.6", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12"],  # II, VI a XII                  (~34 mil)
        ["2.13", "2.14", "2.15", "2.16", "2.17"],              # II, XIII a XVII               (~33 mil)
        ["2.18", "2.19", "2.20", "2.21", "2.22", "2.23"],      # II, XVIII a XXIII             (~30 mil)
        ["2.24", "2.25"],                                      # II, XXIV e XXV                (~28 mil)
        ["2.26", "2.27", "2.28", "2.29"],                      # II, XXVI a XXIX               (~35 mil)
        ["2.30", "2.31", "2.32"],                              # Regulamento, Dissertações, Vocabulário (~23 mil)
    ],
    "ceu": [
        ["1.1", "1.2", "1.3", "1.4"],                          # Doutrina, I a IV              (~28 mil)
        ["1.5", "1.6", "1.7", "1.8"],                          # Doutrina, V a VIII            (~27 mil)
        ["1.9", "1.10", "1.11", "2.1"],                        # Doutrina IX a XI; O passamento (~32 mil)
        ["2.2"],                                               # Espíritos felizes             (~36 mil)
        ["2.3", "2.4"],                                        # Condições medianas; sofredores (~25 mil)
        ["2.5"],                                               # Suicidas                      (~17 mil)
        ["2.6", "2.7"],                                        # Criminosos arrependidos; endurecidos (~24 mil)
        ["2.8"],                                               # Expiações terrestres          (~25 mil)
    ],
    "genese": [
        ["0.0", "1.1"],                                        # Introdução e I                (~25 mil)
        ["1.2", "1.3", "1.4", "1.5"],                          # II a V                        (~26 mil)
        ["1.6", "1.7"],                                        # VI e VII                      (~36 mil)
        ["1.8", "1.9", "1.10"],                                # VIII a X                      (~21 mil)
        ["1.11", "1.12"],                                      # XI e XII                      (~29 mil)
        ["2.13", "2.14"],                                      # Milagres: XIII e XIV          (~27 mil)
        ["2.15", "3.16"],                                      # XV; Predições: XVI            (~32 mil)
        ["3.17", "3.18"],                                      # XVII e XVIII                  (~30 mil)
    ],
}


def montar_obra(livro, saida):
    sys.path.insert(0, AQUI)
    from obras_db import Obra, tokens_aprox
    ob = Obra(livro)
    blocos = BLOCOS_OBRAS[livro]
    assert sorted(c for b in blocos for c in b) == sorted(ob.C), f"BLOCOS_OBRAS[{livro!r}] não cobre o livro"
    for i, caps in enumerate(blocos, 1):
        destino = os.path.join(saida, f"bloco{i}.txt")
        texto = "\n".join(ob.texto_capitulo(c) for c in caps)
        with open(destino, "w", encoding="utf-8") as out:
            out.write(texto)
        print(destino, os.path.getsize(destino), f"~{tokens_aprox(texto)} tokens", "caps", caps)


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
    for livro in BLOCOS_OBRAS:
        if f"--{livro}" in sys.argv[1:]:
            args = [x for x in sys.argv[1:] if not x.startswith("--")]
            saida = os.path.abspath(args[0] if args else os.path.join(AQUI, f"blocos_{livro}"))
            os.makedirs(saida, exist_ok=True)
            montar_obra(livro, saida)
            return
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
