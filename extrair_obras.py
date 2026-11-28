#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator de O Livro dos Médiuns, O Céu e o Inferno e A Gênese (Allan Kardec, FEB,
Edição Histórica de 2013) para bancos JSON no mesmo esquema do Evangelho
(meta, partes, capitulos, ordem, itens, notas).

Uso:
    python3 extrair_obras.py mediuns "O Livro dos Médiuns.txt"   [-o dados/livro_dos_mediuns.json]
    python3 extrair_obras.py ceu     "O-Ceu-e-Inferno.txt"       [-o dados/ceu_e_inferno.json]
    python3 extrair_obras.py genese  "a-genese.txt"              [-o dados/genese.json]

Entrada: o PDF (precisa de pypdf) ou o texto já extraído do PDF (páginas separadas
por linha em branco), como no extrator do Evangelho.

Unidades e ids (a unidade é a divisão numerada do próprio livro):
  O Livro dos Médiuns (itens numerados de 1 a 350 no livro inteiro)
    "159"        item 159, inteiro (com as perguntas 1ª, 2ª… que tiver)
    "I1".."In"   parágrafos da Introdução
    "R0".."R29"  cap. XXX, Regulamento da Sociedade: preâmbulo (R0) e artigos 1º a 29
    "D0".."D34"  cap. XXXI, Dissertações espíritas: abertura (D0) e dissertações I a XXXIV
    "V1".."Vn"   cap. XXXII, Vocabulário espírita: um verbete por unidade
  O Céu e o Inferno
    "7:3"        Primeira Parte (Doutrina), cap. VII, item 3; "7:0" = texto antes do item 1
    "E1:3"       Segunda Parte (Exemplos), cap. I (O passamento), item 3
    "E2:1"       Segunda Parte, cap. II, exemplo 1 (Sanson); exemplo com comunicações
                 numeradas pelo livro (I, II…) se divide nelas: "E2:1.1", "E2:1.2"…
  A Gênese
    "6:12"       cap. VI, item 12; "6:0" = texto antes do item 1
    "I1".."In"   parágrafos da Introdução
  Nos três: "N4" = nota de rodapé (as da Nota Explicativa e do Índice ficam de fora).

Cada unidade guarda parte, capítulo e título, seção, autor e local/data (quando a
comunicação é assinada), parágrafos, texto, notas, páginas e o rodapé de citação
(nome do capítulo em caixa alta, como no Evangelho). Ao terminar, imprime a
validação: numeração, sumário do livro e cobertura palavra por palavra.
"""
import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from extrair_evangelho import carregar_paginas, fim_de_paragrafo, romano_para_int
from extrair_evangelho import juntar as _juntar


def juntar(a, b):
    """Junta duas linhas; "dizer-" + "-se" (hífen repetido na linha seguinte) vira "dizer-se"."""
    if a.endswith("\u2060"):
        return a[:-1] + b.lstrip()
    if a.endswith("-") and not a.endswith(" -") and b.lstrip().startswith("-"):
        return a + b.lstrip()[1:]
    return _juntar(a, b)

RE_RODAPE = re.compile(r"^(\d{1,3}) ?(N\. ?E\.|N\. ?T\.|Nota )")
RE_CAP = re.compile(r"^cap[íi]tulo ([ivxlc]+)\s*$", re.I)
RE_ITEM = re.compile(r"^(\d{1,3})\s?\.(?!\d)\s*(\S.*)$")
RE_DIVISOR = re.compile(r"^Capítulo [IVXL]+ (?![–—-])\S")
RE_PARTE = re.compile(r"^(Primeira|Segunda|Terceira|Quarta) Parte$")
RE_ROMANO = re.compile(r"^([IVXL]{1,7})\.?$")
RE_ART = re.compile(r"^Art\.\s*(\d{1,2})\s*[ºo°]?\s*[—–-]\s*(.*)$")
RE_PONTO = re.compile(r"^(\d{1,2})\s?[oº°]\s*\)\s*(.*)$")
RE_VERBETE = re.compile(r"^([A-ZÀ-Ý][\wÀ-ÿ’'-]*(?: [\wÀ-ÿ’'-]+)?)\s*(?:\(|–)")
RE_LOCAL = re.compile(r"^\(([^()]*)\)\.?$")
RE_SO_ORDINAL = re.compile(r"^\d{1,2}\s?[oºaª°]$")
FIM_FRASE = re.compile(r"[.?!”»)]$")
RE_ASSIN_COLADA = re.compile(r"([.!?…]”)\s+(?:—\s*)?([A-ZÀ-Ú][\w’'. -]{1,40})$")
RE_DIALOGO = re.compile(r"^(\d{1,3}\s?\.\s|\d{1,2}\s?[aª]\s|[a-z]\)\s|— ?R\.|R\.\s|— ?P\.|P\.\s)")

LIVROS = {
    "mediuns": {"titulo": "O Livro dos Médiuns", "curto": "Livro dos Médiuns",
                "traducao": "Guillon Ribeiro", "editora": "FEB, 81ª ed., 2013 (Edição Histórica)",
                "cabecalho": "topo", "inicio": "INTRODUÇÃO", "saida": "dados/livro_dos_mediuns.json"},
    "ceu": {"titulo": "O Céu e o Inferno", "curto": "Céu e Inferno",
            "traducao": "Manuel Quintão", "editora": "FEB, 61ª ed., 2013 (Edição Histórica)",
            "cabecalho": "base", "inicio": None, "saida": "dados/ceu_e_inferno.json"},
    "genese": {"titulo": "A Gênese", "curto": "A Gênese",
               "traducao": "Guillon Ribeiro", "editora": "FEB, 53ª ed., 2013 (Edição Histórica)",
               "cabecalho": "topo", "inicio": "INTRODUÇÃO", "saida": "dados/genese.json"},
}


def int_romano(n):
    tab = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
           (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s = ""
    for v, r in tab:
        while n >= v:
            s += r
            n -= v
    return s


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def eh_divisor(L):
    return sum(1 for l in L if RE_DIVISOR.match(l.strip())) >= 2


# ----------------------------------------------------------------------------
# Páginas: recorte, cabeçalhos, notas de rodapé
# ----------------------------------------------------------------------------
def preparar(pags, cfg):
    """Devolve (linhas, notas, sumario): linhas = [(texto_bruto, pagina, [chamadas])]."""
    ini = next(k for k, L in enumerate(pags)
               if (cfg["inicio"] and L[0].strip() == cfg["inicio"]) or (not cfg["inicio"] and eh_divisor(L)))
    fim = next(k for k in range(ini, len(pags)) if pags[k][0].strip().upper().startswith("NOTA EXPLICATIVA"))
    sumario = [l for L in pags[:ini] for l in L]
    pags = pags[ini:fim]

    topo = cfg["cabecalho"] == "topo"

    def cabecalho(L):
        if len(L) < 2:
            return None
        if topo and L[1].strip().isdigit():
            return L[0].strip()
        if not topo and L[-1].strip().isdigit():
            return L[-2].strip()
        return None
    vistos = Counter(h for h in map(cabecalho, pags) if h and len(h) < 90)
    comuns = sorted((h for h, n in vistos.items() if n >= 2), key=len, reverse=True)

    corpos, nums = [], []
    for L in pags:
        L = list(L)
        num = None
        h = cabecalho(L)
        if h is not None:
            resto = None
            if not (h in comuns or len(h) < 60):
                # cabeçalho grudado na última linha do texto: "…hino de reconheciEspíritos felizes"
                suf = next((c for c in comuns if h.endswith(c) and len(h) > len(c)), None)
                pre = next((c for c in comuns if h.startswith(c) and len(h) > len(c)), None)
                if not topo and suf:
                    resto = h[:-len(suf)].rstrip()
                    if resto[-1:].isalpha() and h[-len(suf) - 1].isalpha():
                        resto += "\u2060"               # palavra partida na colagem: junta sem espaço
                elif topo and pre:
                    resto = h[len(pre):].lstrip()
                else:
                    h = None
            if h is not None:
                if topo:
                    num = int(L[1].strip())
                    L = ([resto] if resto else []) + L[2:]
                else:
                    num = int(L[-1].strip())
                    L = L[:-2] + ([resto] if resto else [])
        corpos.append(L)
        nums.append(num)
    for k in range(len(nums) - 1, -1, -1):          # aberturas de capítulo não têm cabeçalho:
        if nums[k] is None and k + 1 < len(nums) and nums[k + 1] is not None:
            nums[k] = nums[k + 1] - 1               # página seguinte menos 1
    for k in range(len(nums)):
        if nums[k] is None and k and nums[k - 1] is not None:
            nums[k] = nums[k - 1] + 1

    linhas, notas = [], {}
    prox = 1
    aberta = None
    for k, (L, num) in enumerate(zip(corpos, nums)):
        if eh_divisor(L):
            idx = [i for i, l in enumerate(L) if RE_DIVISOR.match(l.strip())]
            antes = [l.strip() for l in L[:idx[0]] if len(l.strip()) > 1]
            depois = [l.strip() for l in L[idx[-1] + 1:] if RE_PARTE.match(l.strip())]
            titulo = " – ".join(depois + ([" ".join(antes)] if antes else []))
            if not titulo:                          # divisória continua na página seguinte
                continue
            linhas.append(("\x00PARTE " + titulo, num, []))
            continue
        corpo, atual = [], None
        for l in L:
            m = RE_RODAPE.match(l.strip())
            if not m and atual is not None:         # nota seguinte na mesma página, sem "N.E."/"Nota"
                m = re.match(r"^(\d{1,3}) (\S)", l.strip())
            if m and int(m.group(1)) == prox:
                atual = m.group(1)
                prox += 1
                notas[atual] = {"id": "N" + atual, "numero": int(atual), "texto": "", "pagina": num, "_k": k}
                resto = l.strip()[m.end(1):].strip()
            elif atual is not None:
                resto = l.strip()
            else:
                corpo.append(l)
                continue
            while True:                             # nota seguinte colada na mesma linha
                mm = re.search(r"\s(%d) (N\. ?E\.|Nota )" % prox, resto)
                if not mm:
                    break
                t = notas[atual]["texto"]
                notas[atual]["texto"] = (t + " " + resto[:mm.start()]).strip()
                atual = str(prox)
                prox += 1
                notas[atual] = {"id": "N" + atual, "numero": int(atual), "texto": "", "pagina": num, "_k": k}
                resto = resto[mm.start(1) + len(atual) + 1:].strip()
            t = notas[atual]["texto"]
            notas[atual]["texto"] = (juntar(t, resto) if t.endswith("-") else t + " " + resto).strip()
        if aberta:                                  # nota da página anterior continua no pé desta
            for s0 in range(len(corpo) // 3, len(corpo)):
                if re.match(r"^([a-zà-ú]|\d+[.,]\d)", corpo[s0].strip()) and s0 and \
                        re.search(r"[.?!:;”»)]\s*$", corpo[s0 - 1]):
                    t = notas[aberta]["texto"]
                    cont = " ".join(x.strip() for x in corpo[s0:])
                    notas[aberta]["texto"] = t + cont if t.endswith("-") else t + " " + cont
                    del corpo[s0:]
                    break
        ultima = max((v for v in notas.values() if v["_k"] == k), key=lambda v: v["numero"], default=None)
        aberta = ultima["id"][1:] if ultima and not re.search(r"[.?!)”»\]]\s*$", ultima["texto"]) else None
        chamadas = [[] for _ in corpo]
        for n in [x for x, v in notas.items() if v["_k"] == k]:
            so = [i for i, l in enumerate(corpo) if l.strip() == n]
            if so and so[0] > 0:                    # chamada sozinha numa linha
                i = so[0]
                chamadas[i - 1].append("N" + n)
                del corpo[i], chamadas[i]
                if i < len(corpo) and not re.search(r"[.?!:;”»)]\s*$", corpo[i - 1]):
                    corpo[i - 1] = corpo[i - 1].rstrip() + " " + corpo[i].lstrip()
                    chamadas[i - 1] += chamadas[i]
                    del corpo[i], chamadas[i]
                continue
            padroes = [r"(?<=[^\d\s–—(:])" + n + r"(?=[\s,.;:)”»]|$)",      # …soberano.4
                       r"(?<=[.)”»]),\s?" + n + r"(?=\s|$)",                 # …próprios.30, 31
                       r"(?<=[A-Za-zÀ-ÿ]:)" + n + r"(?=\s*$)",               # …define:46
                       r"^" + n + r" (?=[a-zà-ú(“])",                       # "42 por outra, …"
                       r"^" + n + r" (?=\S)"]                               # "124 Ormuzd,125 …"
            achou = False
            for rx in padroes:
                for i in range(len(corpo) - 1, -1, -1):
                    novo = re.sub(rx, "", corpo[i], count=1)
                    if novo != corpo[i]:
                        corpo[i] = novo
                        chamadas[i].append("N" + n)
                        achou = True
                        break
                if achou:
                    break
            if not achou:
                notas[n]["_sem_chamada"] = True
        linhas += [(l, num, c) for l, c in zip(corpo, chamadas)]

    linhas = [(re.sub(r"^(\s*\d{1,2}[aoªº])(?=[A-ZÀ-Ú“])", r"\1 ", l), p, c) if not l.startswith("\x00") else (l, p, c)
              for l, p, c in linhas]                 # "13aVais dar-nos" → "13a Vais dar-nos"
    # "2o" sozinho + ") A completa..." / "6a" sozinho + " Haverá..." → uma linha só
    j = []
    for l in linhas:
        if j and RE_SO_ORDINAL.match(j[-1][0].strip()) and not l[0].startswith("\x00"):
            a = j.pop()
            b = l[0].lstrip()
            l = (a[0].strip() + ("" if b.startswith(")") else " ") + b, a[1], a[2] + l[2])
        j.append(l)
    linhas = j
    for v in notas.values():
        v["texto"] = re.sub(r"\s+", " ", v["texto"]).strip()
        v["texto"] = v["texto"].replace("assinadaGALILEU", "assinada GALILEU")   # colagem do PDF (Gênese, N29)
    return linhas, notas, sumario


# ----------------------------------------------------------------------------
# Montagem das unidades (comum aos três livros)
# ----------------------------------------------------------------------------
class Montador:
    def __init__(self, cfg, linhas, notas):
        self.cfg, self.L, self.notas = cfg, linhas, notas
        self.itens, self.ordem, self.capitulos, self.partes, self.avisos = {}, [], [], [], []
        self.parte = self.cap = self.secao = self.grupo = None
        self.atual = self.par = None
        self.pinfo = None
        self.fechou = True
        self.ult = ""
        self.i = 0
        self.pendentes = []

    # --- partes e capítulos
    def nova_parte(self, titulo, pag):
        self.fechar()
        self.parte = {"numero": len(self.partes) + 1, "titulo": titulo, "pagina": pag}
        self.partes.append(self.parte)
        self.cap = None
        self.secao = self.grupo = None

    def ler_capitulo(self, i, inicio):
        j = i + 1
        if j < len(self.L) and re.match(r"^[A-ZÀ-Ú]$", self.L[j][0].strip()):
            j += 1
        titulo = []
        while j < len(self.L) and len(titulo) < 4:
            t = self.L[j][0].strip()
            if not t or t.startswith("•") or inicio(t) or t.startswith("\x00"):
                break
            titulo.append(t)
            fim = self.L[j][0]
            j += 1
            if not fim.endswith(" "):
                break
        bullets = []
        while j < len(self.L):
            t = self.L[j][0].strip()
            ja = {norm(b) for b in " ".join(bullets).split("•") if b.strip()}
            if bullets and not t.startswith("•") and norm(t) in ja:   # título de seção repete o anúncio
                break
            grupo = re.match(r"^(I|II|III|IV|V)\. [A-ZÀ-Ú]", t)
            if t.startswith("•") or grupo or \
                    (bullets and (self.L[j - 1][0].endswith(" ") or bullets[-1].endswith("–")) and not inicio(t)):
                bullets.append("• " + t if grupo else t)
                j += 1
            else:
                break
        secoes = [s.strip() for s in " ".join(bullets).split("•") if s.strip()]
        return re.sub(r"\s+", " ", " ".join(titulo)).strip(), secoes, j

    def novo_capitulo(self, numero, titulo, secoes, pag):
        self.fechar()
        p = self.parte["numero"] if self.parte else 0
        self.cap = {"chave": "%d.%d" % (p, numero), "parte": p, "numero": numero, "titulo": titulo,
                    "secoes": secoes, "itens": [], "pagina": pag}
        self.capitulos.append(self.cap)
        self.secao = self.grupo = None
        self.fechou = True

    # --- unidades
    def novo(self, iid, pag, **campos):
        self.fechar()
        u = {"id": iid, "tipo": "item",
             "parte": self.parte["numero"] if self.parte else None,
             "parte_titulo": self.parte["titulo"] if self.parte else None,
             "capitulo": self.cap["numero"] if self.cap else None,
             "capitulo_titulo": self.cap["titulo"] if self.cap else None,
             "capitulo_chave": self.cap["chave"] if self.cap else None,
             "item": None, "rotulo": None, "secao": self.secao, "grupo": self.grupo,
             "_pars": [], "notas": list(self.pendentes), "pagina_inicio": pag, "pagina_fim": pag}
        u.update(campos)
        self.pendentes = []
        if self.cap is not None:
            self.cap["itens"].append(iid)
        self.atual, self.par, self.pinfo, self.fechou = u, None, None, True
        return u

    def renomear(self, iid, **campos):
        old = self.atual["id"]
        self.atual["id"] = iid
        self.atual.update(campos)
        if self.cap is not None and self.cap["itens"] and self.cap["itens"][-1] == old:
            self.cap["itens"][-1] = iid

    def iniciar(self, resto, bruto, pag, chamadas):
        """Primeira linha da unidade (depois do número)."""
        self.atual["notas"] += chamadas
        self.par = resto
        self.pinfo = {"notas": list(chamadas), "p0": pag, "p1": pag}
        resto_bruto = resto + (" " if bruto.endswith(" ") else "")
        self.fechou = fim_de_paragrafo(bruto) or self.linha_solta(resto_bruto) or self.assinatura_colada(bruto)
        self.fechou = self.fechou and not self.continua_minuscula()
        self.ult = bruto

    def fechar_par(self):
        if self.atual is not None and self.par is not None:
            par = re.sub(r"\s+", " ", self.par).strip()
            m = RE_ASSIN_COLADA.search(par)
            if m and len(m.group(2).split()) <= 5:  # "…num ignaro.” Erasto" → texto + assinatura
                self.atual["_pars"].append((par[:m.end(1)], self.pinfo))
                par = m.group(2).strip()
            self.atual["_pars"].append((par, self.pinfo))
        self.par, self.pinfo = None, None
        self.fechou = True

    def fechar(self):
        self.fechar_par()
        u, self.atual = self.atual, None
        if u is None:
            return
        pares = [(p, i) for p, i in u.pop("_pars") if p]
        pars = [p for p, _ in pares]
        u["_pinfo"] = [i for _, i in pares]
        u["autor"] = u.get("autor")
        u["local_data"] = u.get("local_data")
        if self.assina(u):
            self.assinatura(u, pars)
        u["_pinfo"] = u["_pinfo"][:len(pars)]
        u["paragrafos"] = pars
        u["texto"] = "\n".join(pars)
        if not pars:
            self.avisos.append("unidade vazia: %s" % u["id"])
        self.itens[u["id"]] = u
        self.ordem.append(u["id"])

    def assinatura_colada(self, bruto):
        """'…num ignaro.” Erasto' no fim de linha tipográfica: fecha o parágrafo."""
        return not bruto.endswith(" ") and bool(RE_ASSIN_COLADA.search(bruto.strip()))

    def continua_minuscula(self):
        """A linha seguinte começa com minúscula (e não é "a) …"): o parágrafo continua."""
        prox = self.L[self.i + 1][0].strip() if self.i + 1 < len(self.L) else ""
        return bool(re.match(r"^[a-zà-ú]", prox)) and not re.match(r"^[a-z]\)\s", prox)

    def linha_solta(self, bruto, comecou=False):
        """Linha curta que termina sem espaço (assinatura, título, nome) e é seguida de outra que começa
        com maiúscula: fecha o parágrafo, para não grudar no parágrafo seguinte. Com espaço no fim, só
        se for um nome ("Jobard ", "Julienne-Marie ") sozinho entre dois parágrafos."""
        t = bruto.strip()
        if not t or len(t) > 50 or not t[:1].isupper() or re.search(r"[,;:–—-]$", t):
            return False
        if bruto.endswith(" "):
            particulas = {"de", "da", "do", "dos", "das", "e", "d’", "du", "van", "von", "le", "la"}
            if not (comecou and len(t) <= 30 and all(w[:1].isupper() or w in particulas for w in t.split())):
                return False
        prox = self.L[self.i + 1][0].strip() if self.i + 1 < len(self.L) else ""
        return not prox or bool(re.match(r"^[A-ZÀ-Ú0-9“\"(—–«]", prox))

    def pode_abrir(self):
        """A linha anterior fecha parágrafo, termina em pontuação ou é fim de linha tipográfica."""
        return self.fechou or bool(self.par and FIM_FRASE.search(self.par.strip())) or not self.ult.endswith(" ")

    def sem_unidade(self, txt, pag):
        """Gancho: texto que chegou sem unidade aberta (o livro decide o que fazer)."""

    def texto(self, txt, bruto, pag, chamadas):
        if self.atual is None:
            self.sem_unidade(txt, pag)
            if self.atual is None:
                self.avisos.append("linha fora de unidade (p. %s): %s" % (pag, txt[:70]))
                return
        self.atual["notas"] += chamadas
        if self.par is not None and not self.fechou and FIM_FRASE.search(self.par.strip()) and \
                RE_DIALOGO.match(txt):
            self.fechou = True                      # "…me iludiu. " + "5. Dissestes…" / "— R. …"
        comecou = self.par is None or self.fechou
        if self.par is None or self.fechou:
            self.fechar_par()
            self.par = txt
            self.pinfo = {"notas": [], "p0": pag, "p1": pag}
        else:
            self.par = juntar(self.par, txt)
        self.pinfo["notas"] += chamadas
        self.pinfo["p1"] = pag
        self.atual["pagina_fim"] = pag
        self.fechou = fim_de_paragrafo(bruto) or self.linha_solta(bruto, comecou) or self.assinatura_colada(bruto)
        self.fechou = self.fechou and not self.continua_minuscula()
        self.ult = bruto

    def assina(self, u):
        return True

    def assinatura(self, u, pars):
        """Assinatura no último parágrafo: nome curto sem pontuação final, com ou sem (local, data)."""
        if len(pars) < 2:
            return
        local = None
        k = len(pars) - 1
        m = RE_LOCAL.match(pars[k])
        if m and len(pars) >= 3:
            local, k = m.group(1).strip(), k - 1
        p = pars[k]
        m2 = re.match(r"^(.{2,60}?)\s*\(([^()]{3,90})\)\.?$", p)
        if m2 and not local and re.search(r"\d{4}", m2.group(2)):
            nome, local = m2.group(1), m2.group(2).strip()
        else:
            nome = p
        if nome.endswith("”") and "“" not in nome:
            nome = nome[:-1]                                    # "Erasto”": assinatura dentro das aspas
        secs = {norm(s) for c in self.capitulos for s in c["secoes"]}
        if re.fullmatch(r"[A-ZÀ-Ú]\.(?: ?[A-ZÀ-Ú]\.)*", nome):    # assinatura só com iniciais: "P."
            u["autor"], u["local_data"] = nome, local
            del pars[k:]
            return
        mq = re.match(r"^([A-ZÀ-Ú][\w’'. -]{1,30}), [\w’' -]{3,40}\.$", nome)
        if mq and len(nome) <= 60 and all(w[:1].isupper() or w in ("de", "da", "do", "dos", "das", "e")
                                          for w in mq.group(1).split()):
            nome = nome[:-1]                                     # "Jorge, Espírito familiar."
        if (len(nome) <= 60 and nome[:1].isupper() and not re.search(r"[.!?:;,”»\"…—–-]$", nome)
                and not nome.startswith(("Observação", "Nota", "Obs")) and (norm(nome) not in secs or u.get("exemplo"))
                and len(nome.split()) <= 8):
            u["autor"] = nome.strip()
            u["local_data"] = local
            del pars[k:]

    def subtitulo(self, i, inicio):
        """Subtítulo de seção: 1 a 3 linhas curtas logo antes de uma linha que abre unidade."""
        txt = self.L[i][0].strip()
        if not txt[:1].isupper() or inicio(txt):
            return None
        partes = []
        for j in range(i, min(i + 3, len(self.L))):
            t = self.L[j][0].strip()
            if len(t) > 75 or inicio(t) or t.startswith("\x00"):
                return None
            partes.append(t)
            prox = self.L[j + 1][0].strip() if j + 1 < len(self.L) else ""
            if inicio(prox):
                tit = re.sub(r"\s+", " ", " ".join(partes)).strip()
                if re.search(r"[.;:,)”»\"!]$", tit):
                    return None
                if tit.endswith("?") and not (self.cap and any(norm(sc).startswith(norm(tit)[:20])
                                                               for sc in self.cap["secoes"])):
                    return None                              # "Eis aí o que é o espaço!" / pergunta do texto
                return tit, j + 1
            if not self.L[j][0].endswith(" "):
                return None
        return None

    def titulo_no_texto(self, j, pag):
        """Título de seção seguido de texto sem número: fica como parágrafo da unidade aberta,
        para o texto não perder o título (ex.: "Princípios da Doutrina Espírita…" dentro de 7:0)."""
        prox = self.L[j][0].strip() if j < len(self.L) else ""
        if self.atual is not None and prox and not self.inicio_unidade(prox) and not RE_CAP.match(prox):
            self.atual["_pars"].append((self.secao, {"notas": [], "p0": pag, "p1": pag}))

    def inicio_unidade(self, t):
        return False

    def secao_lista(self, i):
        """Seção anunciada na abertura do capítulo, em 1 a 3 linhas a partir de i: (título, j) ou None."""
        if not self.cap or not self.pode_abrir():
            return None
        secs = {norm(s) for s in self.cap["secoes"]}
        partes = []
        for j in range(i, min(i + 3, len(self.L))):
            partes.append(self.L[j][0].strip())
            tit = re.sub(r"\s+", " ", " ".join(partes)).strip()
            if norm(tit) in secs:
                return tit, j + 1
            if not any(sc.startswith(norm(tit)) for sc in secs):
                break
        return None

    def dividir_introducao(self, uid, prefixo, citacao):
        if uid not in self.itens:
            return
        u = self.itens.pop(uid)
        pos = self.ordem.index(uid)
        novas = []
        for k, (p, inf) in enumerate(zip(u["paragrafos"], u["_pinfo"]), 1):
            v = dict(u)
            v.update(id="%s%d" % (prefixo, k), tipo="introducao", item=k, rotulo="§ %d" % k,
                     paragrafos=[p], texto=p, notas=list(inf["notas"]) if inf else [],
                     pagina_inicio=inf["p0"] if inf else u["pagina_inicio"],
                     pagina_fim=inf["p1"] if inf else u["pagina_fim"],
                     autor=None, local_data=None, citacao=citacao)
            novas.append(v)
        for v in novas:
            self.itens[v["id"]] = v
        self.ordem[pos:pos + 1] = [v["id"] for v in novas]

    # --- final
    def finalizar(self, caminho, formato_id):
        for iid in self.ordem:
            u = self.itens[iid]
            u.pop("_pinfo", None)
            u["notas"] = list(dict.fromkeys(u["notas"]))
            if not u.get("citacao"):
                u["citacao"] = self.citacao(u)
            for nid in u["notas"]:
                if nid[1:] in self.notas:
                    self.notas[nid[1:]]["item"] = iid
        for v in self.notas.values():
            v.setdefault("item", None)
            v.pop("_k", None)
        cfg = self.cfg
        return {
            "meta": {"titulo": cfg["titulo"], "titulo_curto": cfg["curto"], "autor": "Allan Kardec",
                     "traducao": cfg["traducao"], "editora": cfg["editora"], "fonte": Path(caminho).name,
                     "versao_esquema": 1, "formato_id": formato_id},
            "partes": self.partes,
            "capitulos": self.capitulos,
            "ordem": self.ordem,
            "itens": self.itens,
            "notas": {v["id"]: v for v in sorted(self.notas.values(), key=lambda x: x["numero"])},
        }

    def cap_maiusc(self, u):
        return (u["capitulo_titulo"] or "").upper()


# ----------------------------------------------------------------------------
# O Livro dos Médiuns
# ----------------------------------------------------------------------------
class Mediuns(Montador):
    FORMATO = ("item (ex.: 159, itens 1 a 350 no livro inteiro); I1..In Introdução; R0..R29 Regulamento "
               "(cap. XXX); D0..D34 Dissertações (cap. XXXI); V1..Vn Vocabulário (cap. XXXII); N# notas")

    def eh_item(self, t):
        m = RE_ITEM.match(t)
        return bool(m and int(m.group(1)) == self.prox)

    def processar(self):
        L = self.L
        self.modo = "introducao"
        self.prox, self.prox_art, self.prox_d, self.k_verb = 1, 1, 1, 0
        self.novo("__intro__", L[0][1], tipo="introducao")
        i = 0
        while i < len(L):
            bruto, pag, ch = L[i]
            txt = bruto.strip()
            self.i = i
            if not txt:
                i += 1
                continue
            if txt.startswith("\x00PARTE "):
                self.nova_parte(txt[7:], pag)
                self.modo = "entre"
                i += 1
                continue
            if self.modo == "introducao" and txt == "INTRODUÇÃO":
                i += 1
                continue
            m = RE_CAP.match(txt)
            if m:
                self.fechar()
                num = romano_para_int(m.group(1))
                titulo, secoes, j = self.ler_capitulo(i, self.eh_item)
                self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                self.novo_capitulo(num, titulo, secoes, pag)
                especial = {30: "regulamento", 31: "dissertacoes", 32: "vocabulario"}
                self.modo = especial.get(num, "itens") if self.parte and self.parte["numero"] == 2 else "itens"
                i = j
                continue

            if self.modo == "itens":
                mi = RE_ITEM.match(txt)
                if mi and int(mi.group(1)) == self.prox and self.pode_abrir():
                    num = self.prox
                    self.prox += 1
                    self.novo(str(num), pag, item=num, rotulo="item %d" % num)
                    self.iniciar(mi.group(2), bruto, pag, ch)
                    i += 1
                    continue
                if self.pode_abrir():
                    sub = self.subtitulo(i, self.eh_item)
                    if sub:
                        tit, j = sub
                        self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                        self.fechar_par()
                        self.secao = tit
                        i = j
                        continue
            elif self.modo == "regulamento":
                ma = RE_ART.match(txt)
                if ma and int(ma.group(1)) == self.prox_art and self.pode_abrir():
                    n = self.prox_art
                    self.prox_art += 1
                    self.novo("R%d" % n, pag, tipo="artigo", item=n, rotulo="art. %dº" % n)
                    self.iniciar(ma.group(2), bruto, pag, ch)
                    i += 1
                    continue
                if self.fechou and re.match(r"^Capítulo [IVX]+ [—–-] ", txt):
                    self.fechar_par()
                    self.secao = txt
                    i += 1
                    continue
                if self.atual is None:
                    self.novo("R0", pag, tipo="regulamento", item=0, rotulo="preâmbulo")
            elif self.modo == "dissertacoes":
                sl = self.secao_lista(i)
                if sl:
                    self.fechar()
                    self.secao, j = sl
                    self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                    i = j
                    continue
                mr = RE_ROMANO.match(txt)
                if mr and romano_para_int(mr.group(1)) == self.prox_d and self.pode_abrir():
                    n = self.prox_d
                    self.prox_d += 1
                    campos = {"tipo": "dissertacao", "item": n, "rotulo": int_romano(n), "secao": self.secao}
                    if self.atual is not None and self.atual["id"] == "__abertura__":
                        self.renomear("D%d" % n, **campos)
                    else:
                        self.novo("D%d" % n, pag, **campos)
                    i += 1
                    continue
                if self.atual is None:
                    self.novo("D0" if self.prox_d == 1 else "__abertura__", pag, tipo="dissertacao",
                              item=0, rotulo="abertura")
            elif self.modo == "vocabulario":
                mv = RE_VERBETE.match(txt)
                if mv and self.pode_abrir():
                    self.k_verb += 1
                    self.novo("V%d" % self.k_verb, pag, tipo="verbete", item=self.k_verb,
                              rotulo=mv.group(1), termo=mv.group(1))
                    self.iniciar(txt, bruto, pag, ch)
                    i += 1
                    continue
            self.texto(txt, bruto, pag, ch)
            i += 1
        self.fechar()
        self.dividir_introducao("__intro__", "I", "%s, INTRODUÇÃO" % self.cfg["curto"])

    def assina(self, u):
        return u["tipo"] in ("item", "dissertacao")

    def citacao(self, u):
        c = "%s, cap. %s" % (self.cfg["curto"], self.cap_maiusc(u))
        if u["tipo"] == "item":
            return "%s, item %d" % (c, u["item"])
        if u["tipo"] == "artigo":
            return "%s, art. %dº" % (c, u["item"])
        if u["tipo"] == "dissertacao" and u["item"]:
            return "%s, item %s" % (c, int_romano(u["item"]))
        if u["tipo"] == "verbete":
            return "%s, %s" % (c, u["termo"])
        return c


# ----------------------------------------------------------------------------
# O Céu e o Inferno
# ----------------------------------------------------------------------------
class Ceu(Montador):
    FORMATO = ("Primeira Parte: capitulo:item (ex.: 7:3; 7:0 = texto antes do item 1); Segunda Parte "
               "(Exemplos): E1:3 = cap. I, item 3; E2:1 = cap. II, exemplo 1; E2:1.2 = exemplo 1, "
               "comunicação II; N# notas")

    def inicio_unidade(self, t):
        if self.modo == "itens":
            m = RE_ITEM.match(t)
            return bool(m and int(m.group(1)) == self.prox)
        if self.modo == "pontos":
            m = RE_PONTO.match(t)
            return bool(m and int(m.group(1)) == self.prox)
        return False

    def achar_exemplos(self, j, nomes):
        """Linha de título de cada exemplo anunciado na abertura do capítulo."""
        fim = next((k for k in range(j, len(self.L)) if RE_CAP.match(self.L[k][0].strip())), len(self.L))
        pos, achados = j, {}
        for k, nome in enumerate(nomes, 1):
            alvo = norm(nome)
            ult = norm(nome).split()[-1]
            f = next((t for t in range(pos, fim) if norm(self.L[t][0]) == alvo), None)
            if f is None:
                f = next((t for t in range(pos, fim)
                          if len(self.L[t][0].strip()) <= 60 and not self.L[t][0].endswith(" ")
                          and norm(self.L[t][0]).split()[-1:] == [ult]
                          and (t == 0 or fim_de_paragrafo(self.L[t - 1][0]))), None)
            if f is None:
                self.avisos.append("exemplo não encontrado: %s" % nome)
                continue
            achados[f] = (k, nome)
            pos = f + 1
        return achados

    def sem_unidade(self, txt, pag):
        if self.cap is not None:
            pre = "E" if self.parte["numero"] == 2 else ""
            self.novo("%s%d:0" % (pre, self.cap["numero"]), pag, item=0, rotulo=self.secao or "abertura",
                      tipo="abertura")

    def processar(self):
        L = self.L
        self.modo, self.prox, self.titulos, self.exemplo = "entre", 1, {}, None
        i = 0
        while i < len(L):
            bruto, pag, ch = L[i]
            txt = bruto.strip()
            self.i = i
            if not txt:
                i += 1
                continue
            if txt.startswith("\x00PARTE "):
                self.nova_parte(txt[7:], pag)
                self.modo = "entre"
                i += 1
                continue
            m = RE_CAP.match(txt)
            if m:
                self.fechar()
                num = romano_para_int(m.group(1))
                p2 = self.parte["numero"] == 2
                self.modo = "exemplos" if p2 and num >= 2 else ("pontos" if not p2 and num == 7 else "itens")
                self.prox = 1
                titulo, secoes, j = self.ler_capitulo(i, self.inicio_unidade)
                self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                self.novo_capitulo(num, titulo, secoes, pag)
                self.titulos = self.achar_exemplos(j, secoes) if self.modo == "exemplos" else {}
                i = j
                continue
            pre = "E" if self.parte and self.parte["numero"] == 2 else ""
            cap = self.cap["numero"] if self.cap else 0

            if self.modo in ("itens", "pontos"):
                rx = RE_ITEM if self.modo == "itens" else RE_PONTO
                mi = rx.match(txt)
                if mi and int(mi.group(1)) == self.prox and self.pode_abrir():
                    n = self.prox
                    self.prox += 1
                    self.novo("%s%d:%d" % (pre, cap, n), pag, item=n,
                              rotulo=("item %d" % n) if self.modo == "itens" else "%dº" % n)
                    self.iniciar(mi.group(2), bruto, pag, ch)
                    i += 1
                    continue
                sl = self.secao_lista(i)
                if sl:
                    self.fechar_par()
                    self.secao, j = sl
                    self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                    if self.atual is not None and not self.atual["_pars"] and self.atual["tipo"] == "abertura":
                        self.atual["secao"] = self.secao
                    else:
                        self.titulo_no_texto(j, pag)
                    i = j
                    continue
                if self.pode_abrir():
                    sub = self.subtitulo(i, self.inicio_unidade)
                    if sub:
                        tit, j = sub
                        self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                        self.fechar_par()
                        self.secao = tit
                        i = j
                        continue
            elif self.modo == "exemplos":
                if i in self.titulos:
                    k, _ = self.titulos[i]
                    nome = re.sub(r"\s+", " ", txt).strip()          # nome como está no título do texto
                    self.pendentes += ch
                    self.secao = nome
                    self.exemplo = {"k": k, "nome": nome, "prox": 1}
                    self.novo("E%d:%d" % (cap, k), pag, tipo="exemplo", item=k, rotulo=nome, exemplo=nome)
                    i += 1
                    continue
                mr = RE_ROMANO.match(txt)
                ex = self.exemplo
                if mr and ex and self.pode_abrir() and self.atual is not None:
                    v = romano_para_int(mr.group(1))
                    base = "E%d:%d" % (cap, ex["k"])
                    if v == ex["prox"] or (ex["prox"] == 1 and v == 2):
                        if ex["prox"] == 1:
                            self.renomear(base + ".1", sessao=1, rotulo="%s, I" % ex["nome"])
                            ex["prox"] = 2
                        if v >= 2:
                            self.novo("%s.%d" % (base, v), pag, tipo="exemplo", item=ex["k"], sessao=v,
                                      rotulo="%s, %s" % (ex["nome"], int_romano(v)), exemplo=ex["nome"])
                            ex["prox"] = v + 1
                        i += 1
                        continue
            self.texto(txt, bruto, pag, ch)
            i += 1
        self.fechar()
        # exemplo com uma só comunicação numerada volta a ter id simples
        for c in self.capitulos:
            for iid in list(c["itens"]):
                if iid.endswith(".1") and iid[:-2] + ".2" not in self.itens:
                    u = self.itens.pop(iid)
                    u["id"] = iid[:-2]
                    u.pop("sessao", None)
                    u["rotulo"] = u["exemplo"]
                    self.itens[u["id"]] = u
                    self.ordem[self.ordem.index(iid)] = u["id"]
                    c["itens"][c["itens"].index(iid)] = u["id"]

    def citacao(self, u):
        c = "%s, cap. %s" % (self.cfg["curto"], self.cap_maiusc(u))
        if u["tipo"] == "exemplo":
            return "%s, %s" % (c, u["rotulo"])
        if u["tipo"] == "abertura":
            return "%s, %s" % (c, u["secao"]) if u.get("secao") else c
        if u["parte"] == 1 and u["capitulo"] == 7:
            return "%s, Código penal da vida futura, %dº" % (c, u["item"])
        return "%s, item %d" % (c, u["item"])


# ----------------------------------------------------------------------------
# A Gênese
# ----------------------------------------------------------------------------
class Genese(Montador):
    FORMATO = "capitulo:item (ex.: 6:12; 6:0 = texto antes do item 1); I1..In Introdução; N# notas"

    def inicio_unidade(self, t):
        m = RE_ITEM.match(t)
        return bool(m and int(m.group(1)) == self.prox)

    def sem_unidade(self, txt, pag):
        if self.cap is not None:
            self.novo("%d:0" % self.cap["numero"], pag, item=0, rotulo=self.secao or "abertura", tipo="abertura")

    def processar(self):
        L = self.L
        self.modo, self.prox = "introducao", 1
        self.novo("__intro__", L[0][1], tipo="introducao")
        i = 0
        while i < len(L):
            bruto, pag, ch = L[i]
            txt = bruto.strip()
            self.i = i
            if not txt:
                i += 1
                continue
            if txt.startswith("\x00PARTE "):
                self.nova_parte(txt[7:], pag)
                self.modo = "entre"
                i += 1
                continue
            if self.modo == "introducao" and (txt == "INTRODUÇÃO" or txt.startswith("À PRIMEIRA EDIÇÃO")):
                i += 1
                continue
            m = RE_CAP.match(txt)
            if m:
                self.fechar()
                num = romano_para_int(m.group(1))
                self.modo, self.prox = "itens", 1
                titulo, secoes, j = self.ler_capitulo(i, self.inicio_unidade)
                self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                self.novo_capitulo(num, titulo, secoes, pag)
                i = j
                continue
            if self.modo == "itens":
                mi = RE_ITEM.match(txt)
                if mi and int(mi.group(1)) == self.prox and self.pode_abrir():
                    n = self.prox
                    self.prox += 1
                    self.novo("%d:%d" % (self.cap["numero"], n), pag, item=n, rotulo="item %d" % n)
                    self.iniciar(mi.group(2), bruto, pag, ch)
                    i += 1
                    continue
                if self.pode_abrir() and re.match(r"^(I|II|III|IV|V)\. [A-ZÀ-Ú]", txt) and len(txt) < 90 and \
                        any(norm(sc).startswith(norm(txt)[:25]) for sc in self.cap["secoes"]):
                    self.fechar_par()
                    self.grupo = txt
                    self.pendentes += ch
                    while bruto.endswith(" ") and i + 1 < len(L) and len(L[i + 1][0].strip()) < 60 \
                            and not self.inicio_unidade(L[i + 1][0].strip()):
                        i += 1
                        bruto = L[i][0]
                        self.grupo += " " + bruto.strip()
                    i += 1
                    continue
                sl = self.secao_lista(i)
                if sl:
                    self.fechar_par()
                    self.secao, j = sl
                    self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                    self.titulo_no_texto(j, pag)
                    i = j
                    continue
                if self.pode_abrir():
                    sub = self.subtitulo(i, self.inicio_unidade)
                    if sub:
                        tit, j = sub
                        self.pendentes += [x for k in range(i, j) for x in L[k][2]]
                        self.fechar_par()
                        self.secao = tit
                        i = j
                        continue
            self.texto(txt, bruto, pag, ch)
            i += 1
        self.fechar()
        self.dividir_introducao("__intro__", "I", "%s, INTRODUÇÃO" % self.cfg["curto"])

    def citacao(self, u):
        c = "%s, cap. %s" % (self.cfg["curto"], self.cap_maiusc(u))
        if u["tipo"] == "abertura":
            return c
        return "%s, item %d" % (c, u["item"])


CLASSES = {"mediuns": Mediuns, "ceu": Ceu, "genese": Genese}


# ----------------------------------------------------------------------------
# Validação
# ----------------------------------------------------------------------------
def palavras(texto):
    return [w for w in re.findall(r"[\wÀ-ÿ’'-]+", texto.lower())
            if not re.fullmatch(r"[\divxlc]+[oºaª°]?|[-–—]+", w)]


def validar(db, linhas, sumario):
    av = []
    # 1) sumário do livro × capítulos extraídos
    ent, cur = [], None
    for l in sumario:
        t = l.strip()
        if re.match(r"^Capítulo [IVXLC]+\s*[–—-]", t, re.I):
            cur = t
            if re.search(r"\.{3,}", t) or re.search(r"\s\d{1,3}$", t):
                ent.append(cur)
                cur = None
        elif cur is not None:
            cur += " " + t
            if re.search(r"\.{3,}", t) or re.search(r"\s\d{1,3}$", t):
                ent.append(cur)
                cur = None
    sumtit = []
    for e in ent:
        m = re.match(r"^Capítulo ([IVXLC]+)\s*[–—-]\s*(.*?)\s*\.{2,}\s*(\d{1,3})?\s*$", e, re.I)
        if not m:
            m = re.match(r"^Capítulo ([IVXLC]+)\s*[–—-]\s*(.*?)\s+(\d{1,3})\s*$", e, re.I)
        if m:
            sumtit.append((m.group(2), int(m.group(3)) if m.group(3) else None))
    caps = db["capitulos"]
    av.append("(sumário: %d capítulos lidos)" % len(sumtit))
    if len(sumtit) != len(caps):
        av.append("sumário tem %d capítulos; extraídos %d" % (len(sumtit), len(caps)))
    for (st, sp), c in zip(sumtit, caps):
        a, b = norm(st).rstrip(" ."), norm(c["titulo"]).rstrip(" .")
        if a[:25] != b[:25]:
            av.append("título difere do sumário: %r × %r" % (st, c["titulo"]))
        if sp and c["pagina"] and abs(sp - c["pagina"]) > 1:
            av.append("página difere do sumário: %s (%s × %s)" % (c["titulo"][:40], sp, c["pagina"]))
    # 2) numeração dentro de cada capítulo
    for c in caps:
        nums = [db["itens"][x]["item"] for x in c["itens"] if db["itens"][x]["tipo"] in ("item", "artigo")]
        if nums and nums != list(range(nums[0], nums[0] + len(nums))):
            av.append("numeração irregular no cap. %s %s" % (c["chave"], c["titulo"][:40]))
    # 3) cobertura palavra por palavra
    fonte = []
    ant = ""
    for bruto, _, _ in linhas:
        if bruto.startswith("\x00"):
            fonte.append(bruto[7:])
            continue
        t = bruto.strip()
        if ant.endswith("-") and not ant.endswith(" -"):
            fonte[-1] = fonte[-1] + t
        else:
            fonte.append(t)
        ant = t
    fonte = Counter(palavras(" ".join(fonte)))
    banco = []
    for c in caps:
        banco += [c["titulo"]] + c["secoes"]
    for p in db["partes"]:
        banco.append(p["titulo"])
    vistos = set()
    for iid in db["ordem"]:
        u = db["itens"][iid]
        banco += u["paragrafos"] + [u.get("autor") or "", u.get("local_data") or ""]
        for campo in ("secao", "grupo"):
            chave = (u["capitulo_chave"], campo, u.get(campo))
            if u.get(campo) and chave not in vistos:
                vistos.add(chave)
                banco.append(u[campo])
    banco = Counter(palavras(" ".join(banco)))
    falta = fonte - banco
    sobra = banco - fonte
    return av, falta, sobra


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("livro", choices=sorted(LIVROS))
    ap.add_argument("entrada")
    ap.add_argument("-o", "--saida")
    a = ap.parse_args()
    cfg = LIVROS[a.livro]
    pags = carregar_paginas(a.entrada)
    linhas, notas, sumario = preparar(pags, cfg)
    m = CLASSES[a.livro](cfg, linhas, notas)
    m.processar()
    db = m.finalizar(a.entrada, m.FORMATO)
    saida = Path(a.saida or cfg["saida"])
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")

    av, falta, sobra = validar(db, linhas, sumario)
    tok = sum(len(u["texto"]) for u in db["itens"].values()) / 3.5
    print("%s: %d partes | %d capítulos | %d unidades | %d notas | ~%d mil tokens"
          % (cfg["titulo"], len(db["partes"]), len(db["capitulos"]), len(db["itens"]), len(db["notas"]), tok / 1000))
    for c in db["capitulos"]:
        print("  %-5s %-58s %3d unid.  p.%s" % (c["chave"], c["titulo"][:58], len(c["itens"]), c["pagina"]))
    sem = [v["id"] for v in db["notas"].values() if not v.get("item")]
    if sem:
        print("Notas sem unidade:", ", ".join(sem))
    print("Palavras do PDF ausentes do banco: %d (ex.: %s)" % (sum(falta.values()), ", ".join("%s×%d" % kv for kv in falta.most_common(12))))
    print("Palavras do banco ausentes do PDF: %d (ex.: %s)" % (sum(sobra.values()), ", ".join("%s×%d" % kv for kv in sobra.most_common(12))))
    print("Avisos (%d):" % (len(m.avisos) + len(av)))
    for x in (av + m.avisos)[:80]:
        print("  -", x)


if __name__ == "__main__":
    main()
