#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator de "O Evangelho segundo o Espiritismo" (Allan Kardec, tradução Guillon
Ribeiro, FEB, 131ª ed.) para um banco de dados JSON.

Uso:
    python3 extrair_evangelho.py O-evangelho-segundo-o-espiritismo.txt -o dados/evangelho.json
    python3 extrair_evangelho.py O-evangelho-segundo-o-espiritismo.pdf   (precisa de pypdf)

Entrada: o PDF ou o texto já extraído do PDF (páginas separadas por linha em branco).

Unidade = item numerado do livro. Ids no formato capítulo:item, como se cita o livro:
  - "5:4"      capítulo V, item 4 (capítulos I a XXVIII);
  - "0:0"      Prefácio (comunicação do Espírito de Verdade);
  - "0:1".."0:4"   Introdução, partes I a IV;
  - "0:4.1".."0:4.19"  Introdução IV, pontos I a XIX do resumo da doutrina de
                   Sócrates e Platão (cada ponto com o comentário de Kardec);
  - "N1".."N29"    notas de rodapé (de Kardec e da editora).

Cada item guarda: capítulo e título, seção (subtítulo do livro), se está nas
"Instruções dos Espíritos", autor e local/data da comunicação (quando assinada),
texto em parágrafos, a "Nota –" de Kardec que o acompanha, notas de rodapé e páginas.
Ao terminar, imprime um relatório de validação (itens faltando ou fora de ordem).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROMANOS = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def romano_para_int(s):
    s = s.lower()
    total = 0
    for i, ch in enumerate(s):
        v = ROMANOS[ch]
        total += -v if i + 1 < len(s) and ROMANOS[s[i + 1]] > v else v
    return total


RE_CAP = re.compile(r"^capítulo ([ivxl]+)\s*$")
RE_ITEM = re.compile(r"^(\d{1,3})\.\s*(?![\d)])(\S.*)$")
RE_RODAPE = re.compile(r"^(\d{1,2}) (N\. ?E\.|Nota )")
RE_SOCRATES = re.compile(r"^([IVX]{1,5})\.\s+(.*)$")
RE_INTRO_PARTE = re.compile(r"^(I|II|III|IV) – (.*)$")
# assinatura no fim de uma comunicação: " – Fénelon. (Poitiers, 1861.)"
RE_ASSINATURA = re.compile(r"\s[–-]\s*([^–()]{2,120}?)\.?\s*(?:\(([^()]*?)\.?\))?\s*$")

# notas de rodapé que continuam na página seguinte: início do trecho que continua
CONTINUA_NOTA = {
    "4": "Esses textos truncados",
}


def limpar(l):
    return l.replace("\r", "").replace("\x02", "").replace("\xad", "")


# ----------------------------------------------------------------------------
# Páginas
# ----------------------------------------------------------------------------
def carregar_paginas(caminho):
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            sys.exit("Instale o pypdf:  pip install pypdf")
        brutas = [p.extract_text() or "" for p in PdfReader(str(caminho)).pages]
    else:
        brutas = re.split(r"\n\n+", caminho.read_text(encoding="utf-8", errors="replace"))
    pags = []
    for b in brutas:
        L = [limpar(l) for l in b.split("\n")]
        while L and not L[0].strip():
            L.pop(0)
        while L and not L[-1].strip():
            L.pop()
        if L:
            pags.append(L)
    return pags


def preparar(pags):
    """Tira cabeçalho/número de página e notas de rodapé.
    Devolve (linhas, notas): linhas = [(texto_bruto, pagina)], notas = {n: {...}}."""
    linhas, notas = [], {}
    prox_nota = 1
    pag_num = None
    nota_aberta = None
    inicio = False
    for L in pags:
        primeira = L[0].strip()
        if not inicio:
            if primeira == "Prefácio":
                inicio = True
            else:
                continue
        if len(L) > 1 and L[1].strip().isdigit() and len(primeira) < 80:
            pag_num = int(L[1].strip())
            L = L[2:]
        else:
            pag_num = pag_num + 1 if pag_num else 15
        corpo = []
        atual = None
        cont = CONTINUA_NOTA.get(nota_aberta) if nota_aberta else None
        for l in L:
            m = RE_RODAPE.match(l)
            if m and int(m.group(1)) == prox_nota:
                atual = m.group(1)
                prox_nota += 1
                notas[atual] = {"id": "N" + atual, "numero": int(atual),
                                "texto": l[len(atual) + 1:].strip(), "pagina": pag_num}
            elif cont and l.startswith(cont):
                atual = nota_aberta
                notas[atual]["texto"] += " " + l.strip()
                cont = None
            elif atual is not None:
                if notas[atual]["texto"].endswith("-"):
                    notas[atual]["texto"] += l.strip()
                else:
                    notas[atual]["texto"] += " " + l.strip()
            else:
                corpo.append(l)
        nota_aberta = atual if atual and atual in CONTINUA_NOTA else None
        # chamadas de nota coladas ao texto (…soberano.4); guarda em que linha estavam
        chamadas = [[] for _ in corpo]
        for n in [k for k, v in notas.items() if v["pagina"] == pag_num]:
            so = [i for i, l in enumerate(corpo) if l.strip() == n]
            if so and so[0] > 0:
                # chamada sozinha numa linha ("chefe Hillel," / "2" / " doutor judeu…"):
                # junta a linha de antes com a de depois
                i = so[0]
                chamadas[i - 1].append("N" + n)
                del corpo[i], chamadas[i]
                if i < len(corpo):
                    corpo[i - 1] = corpo[i - 1].rstrip() + " " + corpo[i].lstrip()
                    chamadas[i - 1] += chamadas[i]
                    del corpo[i], chamadas[i]
                continue
            for i in range(len(corpo) - 1, -1, -1):
                novo = re.sub(r"(?<=[^\d\s–—(:])" + n + r"(?=[\s,.;:]|$)", "", corpo[i], count=1)
                if novo == corpo[i]:
                    novo = re.sub(r"^" + n + r" (?=\()", "", corpo[i])   # "13 (Bordeaux, 1861.)"
                if novo != corpo[i]:
                    corpo[i] = novo
                    chamadas[i].append("N" + n)
                    break
        linhas += [(l, pag_num, c) for l, c in zip(corpo, chamadas)]
    for v in notas.values():
        v["texto"] = re.sub(r"\s+", " ", v["texto"]).strip()
    return linhas, notas


# ----------------------------------------------------------------------------
# Parágrafos (mesma regra estrita da Introdução de O Livro dos Espíritos)
# ----------------------------------------------------------------------------
def fim_de_paragrafo(bruto):
    txt = bruto.strip()
    if bruto.endswith("-"):
        return False
    fim = re.search(r"[.?!:;”»)\"]$", txt)
    return bool(fim and (not bruto.endswith(" ") or len(txt) < 60))


def juntar(a, b):
    if a.endswith("-") and not a.endswith(" -"):
        return a + b
    return a + " " + b


# ----------------------------------------------------------------------------
# Estrutura
# ----------------------------------------------------------------------------
def subtitulo(linhas, i, esperado):
    """Subtítulo de seção: 1 a 3 linhas curtas logo antes do próximo item numerado
    (ex.: "Moisés" antes de "2."; "Se alguém vos bater na face direita, / apresentai-lhe
    também a outra" antes de "7."). Devolve (titulo, índice da linha do item) ou None."""
    txt = linhas[i][0].strip()
    if not txt[:1].isupper() or RE_ITEM.match(txt):
        return None
    partes = []
    for j in range(i, min(i + 3, len(linhas))):
        t = linhas[j][0].strip()
        if len(t) > 75 or RE_ITEM.match(t):
            return None
        partes.append(t)
        prox = linhas[j + 1][0].strip() if j + 1 < len(linhas) else ""
        mi = RE_ITEM.match(prox)
        if mi and int(mi.group(1)) == esperado:
            tit = re.sub(r"\s+", " ", " ".join(partes)).strip()
            if re.search(r"[.;:,)]$", tit) or RE_ASSINATURA.search(tit) and "(" in tit:
                return None
            return tit, j + 1
        if not linhas[j][0].endswith(" "):
            return None
    return None


def extrair(caminho):
    pags = carregar_paginas(caminho)
    linhas, notas = preparar(pags)

    itens, ordem, capitulos, avisos = {}, [], [], []
    regiao = "prefacio"
    cap = 0
    cap_info = None
    secao = None
    grupo = None
    pendentes = []
    instrucoes = False
    atual = None          # item em construção
    par = None            # parágrafo em construção (texto)
    fechou = True
    i = 0

    def novo_item(iid, numero, pag, sec=None):
        nonlocal atual, par
        fechar_item()
        nonlocal pendentes
        atual = {"id": iid, "tipo": "item", "capitulo": cap,
                 "capitulo_titulo": cap_info["titulo"] if cap_info else None,
                 "item": numero, "secao": sec, "grupo": grupo if cap == 28 else None, "instrucoes_dos_espiritos": instrucoes,
                 "_pars": [], "notas": pendentes + list(chamadas), "pagina_inicio": pag, "pagina_fim": pag}
        par = None
        pendentes = []
        return atual

    def fechar_par():
        nonlocal par
        if atual is not None and par is not None:
            atual["_pars"].append(re.sub(r"\s+", " ", par).strip())
        par = None

    def fechar_item():
        nonlocal atual
        fechar_par()
        if atual is None:
            return
        pars = atual.pop("_pars")
        # "Nota –" de Kardec depois do item (no Prefácio vem colada à assinatura)
        if atual["id"] == "0:0":
            pars = [q for p in pars for q in re.split(r"(?<=O Espírito de Verdade) (?=Nota – )", p)]
        k = next((n for n, p in enumerate(pars) if n and p.startswith("Nota –")), len(pars))
        nota_k = pars[k:]
        pars = pars[:k]
        atual["nota_kardec"] = "\n".join(nota_k) or None
        # assinatura da comunicação
        atual["autor"] = atual["local_data"] = None
        if len(pars) > 1 and re.match(r"^\([^()]*\d{4}\.?\)$", pars[-1]):
            ult = pars.pop()
            pars[-1] += " " + ult
        extra = []
        if len(pars) > 1 and pars[-1].startswith("(Veja-se"):
            extra = [pars.pop()]
        if pars and (atual["instrucoes_dos_espiritos"] or atual["id"] == "0:0" or atual["capitulo"] == 28):
            m = RE_ASSINATURA.search(pars[-1])
            if m and (m.group(2) or len(m.group(1)) < 60) and re.search(r"[.!?”…]\s*$", pars[-1][:m.start()] or "."):
                atual["autor"] = m.group(1).strip()
                atual["local_data"] = (m.group(2) or "").strip() or None
                pars[-1] = pars[-1][:m.start()].rstrip()
                if not pars[-1]:
                    pars.pop()
        pars += extra
        if atual["id"] == "0:0" and pars and pars[-1] == "O Espírito de Verdade":
            pars.pop()
            atual["autor"] = "O Espírito de Verdade"
        atual["paragrafos"] = pars
        atual["texto"] = "\n".join(pars)
        itens[atual["id"]] = atual
        ordem.append(atual["id"])
        atual = None

    while i < len(linhas):
        bruto, pag, chamadas = linhas[i]
        txt = bruto.strip()
        prox = linhas[i + 1][0].strip() if i + 1 < len(linhas) else ""
        if not txt:
            i += 1
            continue

        # mudanças de região
        if regiao == "prefacio" and txt == "Prefácio":
            novo_item("0:0", 0, pag, "Prefácio")
            atual["capitulo_titulo"] = "Prefácio"
            i += 1
            continue
        if txt == "Introdução" and regiao == "prefacio":
            regiao = "introducao"
            fechar_item()
            i += 1
            continue
        mcap = RE_CAP.match(txt)
        if mcap:
            regiao = "capitulos"
            fechar_item()
            cap = romano_para_int(mcap.group(1))
            j = i + 1
            if linhas[j][0].strip() == "M":
                j += 1
            titulo = []
            while j < len(linhas) and not linhas[j][0].strip().startswith("•") \
                    and not RE_ITEM.match(linhas[j][0].strip()):
                titulo.append(linhas[j][0].strip())
                fim = linhas[j][0]
                j += 1
                if not fim.endswith(" "):
                    break
            bullets = []
            while j < len(linhas) and (linhas[j][0].strip().startswith("•") or
                                       (bullets and (linhas[j - 1][0].endswith(" ") or bullets[-1].endswith("–")) and
                                        not RE_ITEM.match(linhas[j][0].strip()))):
                bullets.append(linhas[j][0].strip())
                j += 1
            cap_info = {"numero": cap, "titulo": " ".join(titulo),
                        "secoes": [s.strip() for s in " ".join(bullets).split("•") if s.strip()],
                        "itens": [], "pagina": pag}
            capitulos.append(cap_info)
            secao = None
            instrucoes = False
            fechou = True
            i = j
            continue
        if txt.startswith("Nota Explicativa") and regiao == "capitulos" and fechou:
            fechar_item()
            regiao = "fim"
        if regiao == "fim":
            break

        # Introdução: partes I–IV e pontos do resumo de Sócrates
        if regiao == "introducao":
            mp = RE_INTRO_PARTE.match(txt)
            if mp and fechou:
                titulo = mp.group(2)
                j = i + 1
                while bruto.endswith(" ") and j < len(linhas) and not fim_de_paragrafo(bruto) \
                        and len(linhas[j][0].strip()) < 60:
                    bruto = linhas[j][0]
                    titulo += " " + bruto.strip()
                    j += 1
                n = romano_para_int(mp.group(1))
                novo_item("0:%d" % n, n, pag, re.sub(r"\s+", " ", titulo).strip())
                atual["capitulo_titulo"] = "Introdução"
                atual["parte_introducao"] = mp.group(1)
                fechou = True
                i = j
                continue
            if txt.startswith("Resumo da doutrina de Sócrates") and fechou:
                fechar_par()
                secao = txt
                i += 1
                continue
            ms = RE_SOCRATES.match(txt)
            if ms and (fechou or (par and re.search(r"[.?!”»)]$", par.strip()))) and atual and atual["id"].startswith("0:4") and secao:
                n = romano_para_int(ms.group(1))
                novo_item("0:4.%d" % n, n, pag, secao)
                atual["capitulo_titulo"] = "Introdução"
                atual["parte_introducao"] = "IV"
                par = ms.group(2)
                fechou = fim_de_paragrafo(bruto)
                i += 1
                continue
            if txt.startswith("Controle universal") and atual and atual["id"] == "0:2" and not atual["_pars"] and par is None:
                atual["secao"] += " — " + txt
                i += 1
                continue

        if regiao == "capitulos":
            mi = RE_ITEM.match(txt)
            esperado = (cap_info["itens"] and int(cap_info["itens"][-1].split(":")[1]) + 1) or 1
            if mi and int(mi.group(1)) == esperado and (fechou or (par and re.search(r"[.?!”»)]$", par.strip()))):
                novo_item("%d:%d" % (cap, esperado), esperado, pag, secao)
                cap_info["itens"].append(atual["id"])
                par = mi.group(2)
                fechou = fim_de_paragrafo(bruto)
                i += 1
                continue
            if fechou and txt == "Instruções dos Espíritos":
                fechar_par()
                instrucoes = True
                secao = None
                i += 1
                continue
            if fechou and cap == 28 and re.match(r"^[IVX]+ – ", txt):
                # grupo de preces do cap. XXVIII ("III – Preces por outrem")
                fechar_par()
                grupo = txt
                i += 1
                continue
            sub = subtitulo(linhas, i, esperado) if fechou else None
            if sub:
                tit, j = sub
                pendentes += [n for k in range(i, j) for n in linhas[k][2]]
                fechar_par()
                secao = tit
                i = j
                continue

        # texto corrido
        if atual is None:
            avisos.append("linha fora de item (p. %s): %s" % (pag, txt[:70]))
            i += 1
            continue
        for nid in chamadas:
            atual["notas"].append(nid)
        if par is None or fechou:
            fechar_par()
            par = txt
        else:
            par = juntar(par, txt)
        atual["pagina_fim"] = pag
        fechou = fim_de_paragrafo(bruto)
        i += 1
    fechar_item()

    # notas de rodapé → item onde está a chamada
    for iid in ordem:
        for nid in itens[iid]["notas"]:
            notas[nid[1:]]["item"] = iid
    for v in notas.values():
        v.setdefault("item", None)

    # validação
    for c in capitulos:
        nums = [itens[x]["item"] for x in c["itens"]]
        if nums != list(range(1, len(nums) + 1)):
            avisos.append("cap. %d: numeração irregular" % c["numero"])
    socr = [x for x in ordem if x.startswith("0:4.")]
    if [itens[x]["item"] for x in socr] != list(range(1, len(socr) + 1)):
        avisos.append("Sócrates: numeração irregular")

    db = {
        "meta": {
            "titulo": "O Evangelho segundo o Espiritismo",
            "autor": "Allan Kardec",
            "traducao": "Guillon Ribeiro",
            "editora": "FEB, 131ª ed., 2013",
            "fonte": Path(caminho).name,
            "versao_esquema": 1,
            "formato_id": "capitulo:item (ex.: 5:4); 0:0 Prefácio; 0:1–0:4 Introdução; "
                          "0:4.N pontos de Sócrates e Platão; N# notas de rodapé",
        },
        "capitulos": capitulos,
        "ordem": ordem,
        "itens": itens,
        "notas": {v["id"]: v for v in notas.values()},
    }
    return db, avisos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("entrada")
    ap.add_argument("-o", "--saida", default="dados/evangelho.json")
    a = ap.parse_args()
    db, avisos = extrair(a.entrada)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    caps = db["capitulos"]
    print("Capítulos: %d | itens: %d | notas: %d" % (len(caps), len(db["itens"]), len(db["notas"])))
    for c in caps:
        print("  %2d %-55s %3d itens" % (c["numero"], c["titulo"][:55], len(c["itens"])))
    print("Avisos (%d):" % len(avisos))
    for x in avisos[:60]:
        print("  -", x)


if __name__ == "__main__":
    main()
