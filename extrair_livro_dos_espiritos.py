#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator de "O Livro dos Espíritos" (Allan Kardec, tradução Guillon Ribeiro, FEB)
para um banco de dados JSON consultável pela API `codificacao_db.py`.

Uso:
    python extrair_livro_dos_espiritos.py Livro-dos-Espiritos.pdf
    python extrair_livro_dos_espiritos.py Livro-dos-Espiritos.txt  -o dados/livro_dos_espiritos.json

Entrada: o PDF (precisa de `pip install pypdf`) ou o texto já extraído do PDF
(páginas separadas por linha em branco dupla).

O que é extraído:
  - 1019 perguntas + subperguntas (ex.: 182, 182.a, 182.b), cada uma com
    pergunta, resposta dos Espíritos, comentário de Kardec, parte, capítulo,
    seção, página inicial/final e temas;
  - estrutura de partes, capítulos e seções;
  - Introdução (itens I–XVII), Prolegômenos, Conclusão (I–IX), Nota Explicativa;
  - Introdução dividida em parágrafos: `introducao` (ids I1, I2, ..., na ordem do livro);
  - texto limpo de cada página (numeração impressa do livro);
  - notas de rodapé;
  - Índice geral do livro (assunto → perguntas).

Ao terminar, o script imprime um relatório de validação (números faltando,
fora de ordem, perguntas sem resposta etc.).
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# ----------------------------------------------------------------------------
# Constantes do livro
# ----------------------------------------------------------------------------
PARTES = [
    ("Primeira", "Das causas primárias"),
    ("Segunda", "Do mundo espírita ou mundo dos Espíritos"),
    ("Terceira", "Das leis morais"),
    ("Quarta", "Das esperanças e consolações"),
]

ROMANOS = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def romano_para_int(s):
    s = s.lower()
    total = 0
    for i, ch in enumerate(s):
        v = ROMANOS[ch]
        if i + 1 < len(s) and ROMANOS[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def int_para_romano(n):
    tabela = [(50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, r in tabela:
        while n >= v:
            out += r
            n -= v
    return out


# Temas (tags) por capítulo, revisados no arquivo codificacao-espirita.md
TEMAS_CAPITULO = {
    'P1C01': ["Moral", "Ciência", "Deus", "Atributos de Deus", "Criação", "Universo", "Matéria", "Inteligência", "Instinto", "Justiça divina", "Filosofia", "Panteísmo", "Orgulho", "Progresso espiritual", "Acaso", "Infinito", "Causa primária"],
    'P1C02': ["Moral", "Ciência", "Deus", "Atributos de Deus", "Criação", "Universo", "Matéria", "Fluido universal", "Espírito", "Inteligência", "Progresso espiritual", "Orgulho", "Espaço universal"],
    'P1C03': ["Ciência", "Moral", "Deus", "Atributos de Deus", "Criação", "Universo", "Matéria", "Lei natural", "Pluralidade dos mundos", "Princípio vital", "Reinos da natureza", "Raças humanas", "Animais", "Orgulho", "Religião", "Bíblia", "Dilúvio"],
    'P1C04': ["Ciência", "Matéria", "Fluido universal", "Princípio vital", "Vida e morte", "Morte", "Espírito", "Inteligência", "Instinto", "Universo", "Reinos da natureza", "Livre-arbítrio", "Lei natural"],
    'P2C01': ["Moral", "Ciência", "Deus", "Criação", "Matéria", "Espírito", "Natureza dos Espíritos", "Escala espírita", "Perispírito", "Mundo espiritual", "Progresso espiritual", "Livre-arbítrio", "Influência dos Espíritos", "Provas", "Anjos e demônios"],
    'P2C02': ["Moral", "Ciência", "Espírito", "Alma", "Encarnação", "Perispírito", "Princípio vital", "Expiação", "Missões dos Espíritos", "Progresso espiritual", "Morte", "Materialismo", "Filosofia", "Céu e inferno", "Religião"],
    'P2C03': ["Moral", "Ciência", "Morte", "Desencarnação", "Alma", "Perispírito", "Espírito", "Vida e morte", "Perturbação espiritual", "Mundo espiritual", "Vida espírita", "Emancipação da alma", "Suicídio", "Sofrimento", "Progresso espiritual", "Individualidade"],
    'P2C04': ["Moral", "Ciência", "Deus", "Pluralidade das existências", "Reencarnação", "Pluralidade dos mundos", "Progresso espiritual", "Justiça divina", "Expiação", "Provas", "Perispírito", "Esquecimento do passado", "Família", "Laços espirituais", "Infância"],
    'P2C05': ["Moral", "Ciência", "Deus", "Alma", "Reencarnação", "Pluralidade das existências", "Progresso espiritual", "Justiça divina", "Lei natural", "Livre-arbítrio", "Esquecimento do passado", "Provas", "Penas eternas", "Raças humanas", "Religião", "Jesus", "Bíblia"],
    'P2C06': ["Moral", "Ciência", "Vida espírita", "Erraticidade", "Perispírito", "Desencarnação", "Pluralidade dos mundos", "Reencarnação", "Livre-arbítrio", "Provas", "Expiação", "Sofrimento", "Progresso espiritual", "Escala espírita", "Esquecimento do passado", "Laços espirituais"],
    'P2C07': ["Moral", "Ciência", "Reencarnação", "Encarnação", "Pluralidade das existências", "Esquecimento do passado", "Livre-arbítrio", "Provas", "Expiação", "Perturbação espiritual", "Infância", "Família", "Matéria", "Inteligência", "Suicídio", "Aborto", "Loucura"],
    'P2C08': ["Ciência", "Moral", "Espírito", "Alma", "Perispírito", "Encarnação", "Emancipação da alma", "Sono e sonhos", "Sonambulismo", "Esquecimento do passado", "Pluralidade das existências", "Influência dos Espíritos", "Fluido universal", "Lei natural", "Materialismo", "Êxtase", "Dupla vista"],
    'P2C09': ["Moral", "Ciência", "Espírito", "Influência dos Espíritos", "Obsessão", "Anjos da guarda", "Missões dos Espíritos", "Livre-arbítrio", "Lei natural", "Mediunidade", "Instinto", "Sonambulismo", "Egoísmo", "Provas", "Prece", "Magnetismo", "Superstição"],
    'P2C10': ["Moral", "Deus", "Espírito", "Missões dos Espíritos", "Trabalho", "Progresso espiritual", "Erraticidade", "Encarnação", "Vida espírita", "Anjos da guarda", "Influência dos Espíritos", "Livre-arbítrio", "Família", "Expiação", "Sofrimento"],
    'P2C11': ["Moral", "Ciência", "Criação", "Espírito", "Alma", "Animais", "Reinos da natureza", "Instinto", "Inteligência", "Princípio vital", "Matéria", "Reencarnação", "Metempsicose", "Livre-arbítrio", "Evolução"],
    'P3C01': ["Moral", "Ciência", "Deus", "Lei divina", "Lei natural", "Espírito", "Pluralidade das existências", "Justiça divina", "Livre-arbítrio", "Progresso espiritual", "Caridade", "Egoísmo", "Vícios", "Jesus", "Consciência", "Responsabilidade", "Revelação"],
    'P3C02': ["Moral", "Deus", "Adoração", "Prece", "Lei natural", "Lei divina", "Religião", "Caridade", "Amor", "Orgulho", "Egoísmo", "Arrependimento", "Sofrimento", "Influência dos Espíritos", "Politeísmo", "Sacrifício", "Guerra"],
    'P3C03': ["Moral", "Trabalho", "Lei natural", "Lei divina", "Deus", "Justiça divina", "Progresso espiritual", "Inteligência", "Expiação", "Animais", "Caridade", "Família", "Sociedade", "Bens materiais", "Educação", "Repouso"],
    'P3C04': ["Moral", "Ciência", "Deus", "Criação", "Reprodução", "Lei natural", "Reinos da natureza", "Animais", "Raças humanas", "Evolução", "Progresso social", "Família", "Egoísmo", "Caridade", "Paixões", "Inteligência"],
    'P3C05': ["Moral", "Ciência", "Deus", "Lei natural", "Instinto", "Conservação", "Bens materiais", "Penas e gozos", "Vícios", "Egoísmo", "Caridade", "Trabalho", "Expiação", "Sofrimento", "Mortificação", "Alimentação", "Homicídio"],
    'P3C06': ["Moral", "Ciência", "Lei natural", "Lei divina", "Destruição", "Instinto", "Conservação", "Livre-arbítrio", "Animais", "Provas", "Expiação", "Progresso espiritual", "Guerra", "Crueldade", "Homicídio", "Pena de morte", "Duelo"],
    'P3C07': ["Moral", "Lei natural", "Lei divina", "Sociedade", "Progresso social", "Caridade", "Amor", "Egoísmo", "Trabalho", "Família", "Instinto", "Animais", "Expiação", "Insulamento", "Silêncio"],
    'P3C08': ["Moral", "Progresso espiritual", "Progresso social", "Lei natural", "Lei divina", "Justiça divina", "Livre-arbítrio", "Egoísmo", "Orgulho", "Caridade", "Reencarnação", "Pluralidade das existências", "Materialismo", "Espiritismo", "Civilização", "Legislação humana"],
    'P3C09': ["Moral", "Deus", "Lei divina", "Lei natural", "Igualdade", "Espírito", "Progresso espiritual", "Livre-arbítrio", "Provas", "Bens materiais", "Egoísmo", "Orgulho", "Caridade", "Sociedade", "Progresso social", "Justiça divina"],
    'P3C10': ["Moral", "Liberdade", "Livre-arbítrio", "Fatalidade", "Lei natural", "Lei divina", "Escravidão", "Religião", "Caridade", "Provas", "Expiação", "Pluralidade das existências", "Influência dos Espíritos", "Instinto", "Paixões", "Morte"],
    'P3C11': ["Moral", "Deus", "Lei divina", "Lei natural", "Justiça", "Amor", "Caridade", "Egoísmo", "Paixões", "Bens materiais", "Trabalho", "Sociedade", "Família", "Provas", "Jesus"],
    'P3C12': ["Moral", "Virtudes", "Caridade", "Egoísmo", "Vícios", "Orgulho", "Paixões", "Bens materiais", "Amor", "Progresso espiritual", "Livre-arbítrio", "Lei divina", "Jesus", "Autoconhecimento", "Felicidade"],
    'P4C01': ["Moral", "Penas e gozos", "Felicidade", "Provas", "Expiação", "Sofrimento", "Bens materiais", "Egoísmo", "Orgulho", "Paixões", "Amor", "Caridade", "Trabalho", "Suicídio", "Morte", "Sociedade", "Mediunidade"],
    'P4C02': ["Moral", "Ciência", "Penas e gozos", "Justiça divina", "Expiação", "Arrependimento", "Penas eternas", "Céu e inferno", "Felicidade", "Sofrimento", "Reencarnação", "Pluralidade das existências", "Ressurreição", "Erraticidade", "Progresso espiritual", "Prece", "Purgatório"],
}

# ----------------------------------------------------------------------------
# Utilidades de texto
# ----------------------------------------------------------------------------
RE_PERGUNTA = re.compile(r"^(\d{1,4})\.\s+")
RE_SUB = re.compile(r"^([a-z])\)\s+")
RE_RODAPE = re.compile(r"^(\d{1,2}) (Nota de Allan Kardec|N\.E\.|N\.T\.)")
RE_CAPITULO = re.compile(r"^cap[íi]tulo\s+([ivxl]+)\s*$", re.I)
RE_ROMANO_SO = re.compile(r"^([IVXL]+)\d{0,2}$")  # "IV26" = item IV + chamada de nota 26


def normalizar(s):
    """minúsculas, sem acento, sem pontuação, espaços simples (para comparar)."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def limpar_linha(l):
    return l.replace("\r", "").replace("\x02", "").replace("­", "")


# ----------------------------------------------------------------------------
# Leitura das páginas
# ----------------------------------------------------------------------------
def carregar_paginas(caminho):
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            sys.exit("Instale o pypdf:  pip install pypdf")
        leitor = PdfReader(str(caminho))
        brutas = [p.extract_text() or "" for p in leitor.pages]
    else:
        texto = caminho.read_bytes().decode("utf-8", errors="replace")
        brutas = re.split(r"(?<!\r)\n\n+", texto)
    paginas = []
    for b in brutas:
        linhas = [l.replace("\r", "") for l in re.split(r"\n", b)]
        while linhas and not linhas[0].strip():
            linhas.pop(0)
        while linhas and not linhas[-1].strip():
            linhas.pop()
        paginas.append(linhas)
    return paginas


def detectar_modo_espaco(paginas):
    """No texto do PDF, linha que continua no parágrafo seguinte termina com espaço.
    Se o extrator não preservar isso, usamos regras estruturais."""
    total = fim_espaco = 0
    for p in paginas:
        for l in p:
            if l.strip():
                total += 1
                if l.endswith(" "):
                    fim_espaco += 1
    return total and fim_espaco / total > 0.2


# ----------------------------------------------------------------------------
# Classificação das páginas
# ----------------------------------------------------------------------------
def classificar(paginas):
    """Devolve lista de dicts: {pdf, regiao, numero, linhas(conteúdo), cabecalho,
    capitulo_inicio, parte_inicio, notas}"""
    out = []
    regiao = "pre"
    parte = 0
    for i, L in enumerate(paginas):
        info = {"pdf": i, "numero": None, "cabecalho": None, "linhas": [],
                "capitulo_inicio": None, "parte_inicio": None, "notas": {}}
        if not L:
            info["regiao"] = regiao
            out.append(info)
            continue
        primeira = limpar_linha(L[0]).strip()
        conteudo = L
        if primeira.startswith("Introdução") and regiao == "pre":
            regiao = "introducao"
            k = 1
            while k < len(L) and not RE_ROMANO_SO.match(L[k].strip()):
                k += 1
            conteudo = L[k:]
        elif primeira == "Prolegômenos":
            regiao = "prolegomenos"
            conteudo = L[1:]
        elif primeira == "M" and regiao in ("prolegomenos", "parte"):
            parte += 1
            regiao = "parte"
            info["parte_inicio"] = parte
            conteudo = []
        elif RE_CAPITULO.match(primeira) and regiao == "parte":
            info["capitulo_inicio"] = romano_para_int(RE_CAPITULO.match(primeira).group(1))
            conteudo = L[1:]
            if conteudo and conteudo[0].strip() == "M":
                conteudo = conteudo[1:]
        elif primeira.startswith("Conclusão") and regiao == "parte":
            regiao = "conclusao"
            conteudo = L[1:]
        elif primeira.startswith("Nota Explicativa") and regiao == "conclusao":
            regiao = "nota_explicativa"
            conteudo = L[1:]
        elif primeira.lower().startswith("índice geral") and regiao == "nota_explicativa":
            regiao = "indice"
            conteudo = L[1:]
        elif len(L) > 1 and L[1].strip().isdigit() and regiao != "pre":
            info["cabecalho"] = primeira
            info["numero"] = int(L[1].strip())
            conteudo = L[2:]
        info["regiao"] = regiao
        info["parte"] = parte
        # notas de rodapé: da primeira marca até o fim da página
        corpo, notas, atual = [], {}, None
        for l in conteudo:
            m = RE_RODAPE.match(limpar_linha(l))
            if m and regiao != "pre":
                atual = m.group(1)
                notas[atual] = limpar_linha(l)[len(atual) + 1:].strip()
            elif atual is not None:
                notas[atual] += " " + limpar_linha(l).strip()
            else:
                corpo.append(l)
        info["linhas"] = corpo
        info["notas"] = notas
        out.append(info)
    # numeração das páginas sem número impresso (início de capítulo, de parte etc.)
    nums = [p["numero"] for p in out]
    for i, p in enumerate(out):
        if p["numero"] is None and p["regiao"] != "pre" and (p["linhas"] or p["parte_inicio"]):
            prox = next(((j, nums[j]) for j in range(i + 1, len(out)) if nums[j]), None)
            ant = next(((j, nums[j]) for j in range(i - 1, -1, -1) if nums[j]), None)
            if prox:
                p["numero"] = prox[1] - (prox[0] - i)
            elif ant:
                p["numero"] = ant[1] + (i - ant[0])
    return out


# ----------------------------------------------------------------------------
# Parágrafos
# ----------------------------------------------------------------------------
def montar_paragrafos(linhas_pag, modo_espaco, e_titulo=None, estrito=False):
    """linhas_pag: lista de (texto_bruto, pagina). Devolve lista de
    {'t': texto, 'p0': pag_inicio, 'p1': pag_fim}.
    estrito=True (Introdução): só há parágrafo novo depois de pontuação final (. ? ! : ; » ” ))
    e, se a linha tiver espaço no fim, só quando ela for curta (< 60 caracteres)."""
    pars = []
    atual = None
    continua = False
    for bruto, pag in linhas_pag:
        l = limpar_linha(bruto)
        if not l.strip():
            continue
        txt = l.strip()
        inicio_estrutural = bool(RE_PERGUNTA.match(txt) or RE_SUB.match(txt) or txt.startswith("“")
                                 or (e_titulo is not None and e_titulo(txt)))
        fim_frase = atual is not None and re.search(r"[.?!:”»)]\s*\d*(,\s*\d+)*$", atual["t"])
        if atual is not None and continua and not (inicio_estrutural and (fim_frase or not modo_espaco)):
            if atual["t"].endswith("-") and not atual["t"].endswith(" -"):
                atual["t"] += txt
            else:
                atual["t"] += " " + txt
            atual["p1"] = pag
        else:
            atual = {"t": txt, "p0": pag, "p1": pag}
            pars.append(atual)
        if e_titulo is not None and e_titulo(txt) and atual["t"] == txt:
            continua = False
        elif estrito:
            fim = re.search(r"[.?!:;”»)\"]\s*\d*(,\s*\d+)*$", txt)
            continua = l.endswith("-") or not (fim and (not l.endswith(" ") or len(txt) < 60))
        elif modo_espaco:
            continua = l.endswith(" ") or l.endswith("-")
        else:
            continua = not re.search(r"[.?!:”»]\s*\d*(,\s*\d+)*$", txt)
    for p in pars:
        p["t"] = re.sub(r"\s+", " ", p["t"]).strip()
    return pars


# ----------------------------------------------------------------------------
# Início de capítulo: título e lista de seções
# ----------------------------------------------------------------------------
def separar_cabecalho_capitulo(linhas, modo_espaco):
    """linhas: conteúdo da página de abertura do capítulo (sem 'capítulo x' e 'M').
    Devolve (titulo, secoes, resto_das_linhas)."""
    titulo = []
    k = 0
    while k < len(linhas):
        t = limpar_linha(linhas[k]).strip()
        if t.startswith("•") or RE_PERGUNTA.match(t):
            break
        if titulo and modo_espaco and not titulo[-1][1]:
            break
        titulo.append((t, limpar_linha(linhas[k]).endswith(" ")))
        k += 1
        if not modo_espaco and len(titulo) >= 2:
            break
    titulo_txt = " ".join(t for t, _ in titulo)
    bullets = []
    prev_wrap = False
    while k < len(linhas):
        bruto = limpar_linha(linhas[k])
        t = bruto.strip()
        if t.startswith("•") or "•" in t or (prev_wrap and bullets):
            bullets.append(t)
            prev_wrap = bruto.endswith(" ")
            k += 1
        else:
            break
    secoes = [s.strip() for s in " ".join(bullets).split("•") if s.strip()]
    return re.sub(r"\s+", " ", titulo_txt).strip(), secoes, linhas[k:]


# ----------------------------------------------------------------------------
# Itens (perguntas) dentro das partes
# ----------------------------------------------------------------------------
def tirar_refs_rodape(s):
    # remove chamadas de nota coladas no fim: ...coisas.”4, 5
    return re.sub(r"(?<=[”?.!»])\s?\d{1,2}(,\s?\d{1,2})*$", "", s).strip()


def finalizar_item(item):
    perg = "\n".join(item.pop("_perg"))
    resp = "\n".join(item.pop("_resp"))
    com = "\n".join(item.pop("_com"))
    item["resposta_sem_aspas"] = False
    item.setdefault("tipo", "pergunta")
    item.setdefault("texto", "")
    if not resp:
        # Alguns trechos do PDF perderam as aspas da resposta. Se o item é uma
        # pergunta (tem "?"), o que vem logo depois do "?" é tratado como resposta.
        m = re.search(r"\?\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ“])", perg)
        if m and m.end() < len(perg) and len(perg[:m.start()]) < 600 and not re.search(r"[.!]\s", perg[:m.start()]):
            perg, resp = perg[:m.start() + 1], perg[m.end():]
            item["resposta_sem_aspas"] = True
        elif perg.rstrip().endswith("?") and com and len(perg) < 600:
            resp, _, com = com.partition("\n")
            item["resposta_sem_aspas"] = True
        else:  # item numerado escrito por Kardec (59, 100–113, 222, 257, 455, 872): não é pergunta
            item["tipo"] = "kardec"
            item["texto"] = tirar_refs_rodape((perg + ("\n" + com if com else "")).strip())
            perg, com = "", ""
    # chamadas de nota de rodapé coladas ao texto (ex.: coisas.”4, 5) — validadas depois pela página
    item["_chamadas"] = set(re.findall(r"(?<=[A-Za-zÀ-ÿ”?.!»:;,)])(\d{1,2})(?=(?:,\s?\d{1,2})*(?:\s|$))",
                                       "\n".join([perg, resp, com, item.get("_texto_bruto", "")])))
    # assinatura do Espírito (ex.: "São Luís") na 1ª linha após a resposta
    item["assinatura"] = None
    if com and resp:
        primeira, _, resto = com.partition("\n")
        if (len(primeira) < 45 and primeira[:1].isupper() and "." not in primeira
                and not primeira.startswith("(")):
            item["assinatura"], com = primeira.strip(), resto.strip()
    item["pergunta"] = tirar_refs_rodape(perg).strip()
    item["resposta"] = tirar_refs_rodape(resp).strip()
    # Comentário que começa só com uma remissão, ex. "(540)", "(Vide: “Egoísmo”, cap. XII.)",
    # ou com uma nota da Editora ("N.E.: ...") não é texto de Kardec: vai para campos próprios.
    item["referencia"] = None
    item["nota_editora"] = None
    m = RE_REF_INICIAL.match(com)
    if m:
        item["referencia"] = re.sub(r"\s+", " ", m.group(1)).replace("(l9", "(19").replace(" .)", ".)")
        com = com[m.end():].strip()
    m = re.match(r"N\.E\.:\s*(.+?)(?:\n\.?\s*|$)", com, re.S)
    if m and com.startswith("N.E."):
        item["nota_editora"] = m.group(1).strip()
        com = com[m.end():].strip()
    item["comentario"] = com
    item["remissoes"] = extrair_remissoes(item["resposta"] + "\n" + (item["referencia"] or "")
                                          + "\n" + com)
    return item


RE_REF_INICIAL = re.compile(r"^\s*(\((?:[^()]*?(?:\d|[Vv]er\b|[Vv]ide|[Vv]eja|[Vv]ede))[^()]*\))[ \t]*\n?")

RE_REMISSAO = re.compile(r"\((?:[Vv]ide:?\s*)?(?:[Qq]uest(?:ão|ões)\s*|n\.?[ºo]?\s*)?"
                         r"(\d{1,4}[a-z]?(?:\s*(?:,|e|a|–|-)\s*\d{1,4}[a-z]?)*)(\s*e seguintes)?\.?\)")


def extrair_remissoes(txt):
    """'(720 e 721)' -> ['720','721'];  '(205 a 385)' -> ['205-385'];  '(919a)' -> ['919.a']"""
    out = []
    for m in RE_REMISSAO.finditer(txt):
        corpo = m.group(1)
        for a, b in re.findall(r"(\d{1,4}[a-z]?)\s*(?:a|–|-)\s*(\d{1,4}[a-z]?)", corpo):
            out.append(f"{a}-{b}")
        corpo = re.sub(r"\d{1,4}[a-z]?\s*(?:a|–|-)\s*\d{1,4}[a-z]?", " ", corpo)
        for n, l in re.findall(r"(\d{1,4})([a-z]?)", corpo):
            out.append(f"{n}.{l}" if l else n)
    return list(dict.fromkeys(out))


def parsear_partes(pags, modo_espaco, avisos):
    capitulos = []          # dicts de capítulo
    itens = []              # perguntas em ordem
    textos_k = []           # textos de Kardec sem número (Ke1, Ke2…)
    ultimo_num = 0
    cap = None
    item = None
    parte = 0
    estado = None
    saldo = 0

    def fechar():
        nonlocal item
        if item is not None:
            itens.append(finalizar_item(item))
            item = None

    # junta linhas por capítulo
    grupos = []
    for p in pags:
        if p["regiao"] != "parte":
            continue
        if p["parte_inicio"]:
            parte = p["parte_inicio"]
            continue
        if p["capitulo_inicio"]:
            titulo, secoes, resto = separar_cabecalho_capitulo(p["linhas"], modo_espaco)
            grupos.append({"parte": parte, "numero": p["capitulo_inicio"], "titulo": titulo,
                           "secoes": secoes, "linhas": [(l, p["numero"]) for l in resto],
                           "pagina_inicio": p["numero"], "pagina_fim": p["numero"]})
        elif grupos:
            grupos[-1]["linhas"] += [(l, p["numero"]) for l in p["linhas"]]
            grupos[-1]["pagina_fim"] = p["numero"]

    for g in grupos:
        fechar()
        cid = f"P{g['parte']}C{g['numero']:02d}"
        cap = {"id": cid, "parte": g["parte"], "numero": g["numero"],
               "romano": int_para_romano(g["numero"]), "titulo": g["titulo"],
               "secoes": g["secoes"], "temas": TEMAS_CAPITULO.get(cid, []),
               "pagina_inicio": g["pagina_inicio"], "pagina_fim": g["pagina_fim"],
               "texto_inicial": "", "perguntas": []}
        capitulos.append(cap)
        sec_norm = normalizar(" • ".join(g["secoes"]))
        secao = None
        ke = None            # texto sem número em andamento
        nova_secao = False   # houve título de seção desde a última pergunta?

        def abrir_ke(par):
            nonlocal ke
            ke = {"capitulo": cid, "parte": cap["parte"], "secao": secao,
                  "depois_de": itens[-1]["id"] if itens and itens[-1]["capitulo"] == cid else None,
                  "pagina_inicio": par["p0"], "pagina_fim": par["p1"], "_t": []}
            textos_k.append(ke)

        def e_secao(t):
            return (len(t) <= 95 and not re.search(r"[.?!”:;,]$", t)
                    and not RE_PERGUNTA.match(t) and not RE_SUB.match(t)
                    and not t.startswith("“") and t[:1].isupper()
                    and len(normalizar(t)) >= 4 and normalizar(t) in sec_norm)

        for par in montar_paragrafos(g["linhas"], modo_espaco, e_secao):
            t = par["t"]
            m = RE_PERGUNTA.match(t)
            ms = RE_SUB.match(t)
            # título de seção?
            if e_secao(t) and (item is None or estado != "resposta"):
                secao, ke, nova_secao = t, None, True
                continue
            if m and int(m.group(1)) == ultimo_num + 1:
                ke, nova_secao = None, False
                fechar()
                ultimo_num = int(m.group(1))
                item = {"id": str(ultimo_num), "numero": ultimo_num, "letra": None,
                        "parte": cap["parte"], "capitulo": cid, "secao": secao,
                        "pagina_inicio": par["p0"], "pagina_fim": par["p1"],
                        "_perg": [t[m.end():]], "_resp": [], "_com": []}
                estado, saldo = "pergunta", 0
                continue
            if ms and item is not None and (estado != "resposta" or saldo <= 0):
                letra = ms.group(1)
                esperada = "a" if item["letra"] is None else chr(ord(item["letra"]) + 1)
                if letra == esperada:
                    ke, nova_secao = None, False
                    num = item["numero"]
                    fechar()
                    item = {"id": f"{num}.{letra}", "numero": num, "letra": letra,
                            "parte": cap["parte"], "capitulo": cid, "secao": secao,
                            "pagina_inicio": par["p0"], "pagina_fim": par["p1"],
                            "_perg": [t[ms.end():]], "_resp": [], "_com": []}
                    estado, saldo = "pergunta", 0
                    continue
            # parágrafo antes da 1ª pergunta do capítulo, ou logo após um título de seção:
            # texto de Kardec sem número
            # continuação de título de seção quebrado em duas linhas
            if (nova_secao and ke is None and len(t) < 60 and not re.search(r"[.!?:;]$", t)
                    and normalizar((secao or "") + " " + t) in sec_norm):
                secao = (secao + " " + t) if secao else t
                continue
            if ke is not None or item is None or (nova_secao and estado == "pos"):
                if ke is None:
                    if item is None and len(t) < 60 and not re.search(r"[.!?:]$", t):
                        continue  # resto de título quebrado em duas linhas
                    abrir_ke(par)
                ke["_t"].append(t)
                ke["pagina_fim"] = par["p1"]
                continue
            item["pagina_fim"] = par["p1"]
            if estado == "pergunta":
                perg_txt = " ".join(item["_perg"])
                if t.startswith("“") and len(item["_perg"]) <= 2 and (len(perg_txt) < 600 or perg_txt.rstrip().endswith("?")):
                    estado = "resposta"
                else:
                    item["_perg"].append(t)
                    continue
            if estado == "resposta":
                corte = None
                for pos, ch in enumerate(t):
                    if ch == "“":
                        saldo += 1
                    elif ch == "”":
                        saldo -= 1
                        if saldo <= 0:
                            corte = pos + 1
                            break
                if corte is None:
                    item["_resp"].append(t)
                    continue
                # aspas fecharam: o que vier depois no mesmo parágrafo é comentário
                resto = re.sub(r"^\s*\d{1,2}(,\s?\d{1,2})*", "", t[corte:]).strip()
                item["_resp"].append(t[:corte] + re.match(r"\s*\d{0,2}", t[corte:]).group(0).rstrip())
                estado = "pos"
                if resto and e_secao(resto):
                    secao = resto
                elif resto:
                    item["_com"].append(resto)
                continue
            item["_com"].append(t)
    fechar()
    for it in itens:
        next(c for c in capitulos if c["id"] == it["capitulo"])["perguntas"].append(it["id"])
    # numera os textos sem número na ordem do livro e liga à pergunta seguinte
    ordem = [it["id"] for it in itens]
    for i, k in enumerate(textos_k, 1):
        k["id"] = f"Ke{i}"
        k["texto"] = tirar_refs_rodape("\n".join(k.pop("_t")).strip())
        pos = ordem.index(k["depois_de"]) + 1 if k["depois_de"] else \
            next(j for j, it in enumerate(itens) if it["capitulo"] == k["capitulo"])
        k["antes_de"] = ordem[pos] if pos < len(ordem) else None
    return capitulos, itens, textos_k


# ----------------------------------------------------------------------------
# Introdução, Prolegômenos, Conclusão, Nota Explicativa
# ----------------------------------------------------------------------------
def parsear_textos(pags, modo_espaco):
    textos = {}
    prefixo = {"introducao": "introd", "conclusao": "concl"}
    for reg, nome in [("introducao", "Introdução ao estudo da Doutrina Espírita"),
                      ("prolegomenos", "Prolegômenos"), ("conclusao", "Conclusão"),
                      ("nota_explicativa", "Nota Explicativa")]:
        linhas = [(l, p["numero"]) for p in pags if p["regiao"] == reg for l in p["linhas"]]
        if not linhas:
            continue
        if reg in prefixo:
            blocos, atual = [], None
            for l, pg in linhas:
                t = limpar_linha(l).strip()
                mr = RE_ROMANO_SO.match(t)
                if mr and (atual is None or romano_para_int(mr.group(1)) == atual["n"] + 1):
                    atual = {"n": romano_para_int(mr.group(1)), "linhas": [], "p0": pg}
                    blocos.append(atual)
                elif atual is not None:
                    atual["linhas"].append((l, pg))
            for b in blocos:
                pars = montar_paragrafos(b["linhas"], modo_espaco, estrito=(reg == "introducao"))
                chave = f"{prefixo[reg]}.{int_para_romano(b['n'])}"
                textos[chave] = {"id": chave, "obra_parte": nome, "item": int_para_romano(b["n"]),
                                 "texto": "\n".join(p["t"] for p in pars),
                                 "pagina_inicio": b["p0"],
                                 "pagina_fim": pars[-1]["p1"] if pars else b["p0"],
                                 "paragrafos": pars}
        else:
            pars = montar_paragrafos(linhas, modo_espaco)
            chave = reg
            textos[chave] = {"id": chave, "obra_parte": nome, "item": None,
                             "texto": "\n".join(p["t"] for p in pars),
                             "pagina_inicio": linhas[0][1], "pagina_fim": linhas[-1][1]}
    return textos


def ligar_notas_introducao(introducao, notas):
    """Tira do texto a chamada de nota colada à palavra (Proteu,1 / errante;2) e liga cada nota
    de rodapé ao parágrafo da Introdução em que ela foi chamada."""
    for n in notas.values():
        n.setdefault("introducao", [])
    for it in introducao.values():
        it["notas"] = []
        for k, n in notas.items():
            if it["pagina_inicio"] <= n["pagina"] <= it["pagina_fim"] and n["pagina"] < 50:
                novo = re.sub(rf"(?<=[^\d\s]){k}(?=\s|$)", "", it["texto"])
                if novo != it["texto"]:
                    it["texto"] = novo
                    it["notas"].append(f"N{k}")
                    n["introducao"].append(it["id"])


def montar_introducao(textos):
    """Cada parágrafo da Introdução vira um item I1, I2, ... (ordem do livro), com o item romano
    de origem (I a XVII) e o número do parágrafo dentro dele."""
    intro, n = {}, 0
    for chave in sorted((k for k in textos if k.startswith("introd.")), key=lambda k: romano_para_int(k.split(".")[1])):
        for j, par in enumerate(textos[chave].pop("paragrafos"), 1):
            n += 1
            intro[f"I{n}"] = {"id": f"I{n}", "tipo": "introducao", "item": textos[chave]["item"],
                              "paragrafo": j, "texto": par["t"],
                              "pagina_inicio": par["p0"], "pagina_fim": par["p1"]}
    for k, v in textos.items():
        v.pop("paragrafos", None)
    return intro


# ----------------------------------------------------------------------------
# Índice geral (assunto → perguntas)
# ----------------------------------------------------------------------------
RE_REF_ROMANA = re.compile(r"(introd|concl)\.\s*,?\s*([IVXL]+)")
RE_REF_NUM = re.compile(r"(\d{1,4})([a-z]?)(?:\s*[-–]\s*(\d{1,4})([a-z]?))?")


def parsear_refs(s):
    refs = []
    for m in RE_REF_ROMANA.finditer(s):
        refs.append(f"{m.group(1)}.{m.group(2)}")
    s2 = RE_REF_ROMANA.sub(" ", s)
    if re.search(r"proleg\.", s2):
        refs.append("prolegomenos")
        s2 = re.sub(r"proleg\.", " ", s2)
    for m in RE_REF_NUM.finditer(s2):
        a, la, b, lb = m.groups()
        if b:
            for n in range(int(a), int(b) + 1):
                refs.append(str(n))
        else:
            refs.append(f"{a}.{la}" if la else a)
    return refs


def parsear_indice(pags, modo_espaco):
    linhas = []
    for p in pags:
        if p["regiao"] != "indice":
            continue
        for l in p["linhas"]:
            linhas.append(limpar_linha(l))
    conectivo = re.compile(r"\b(e|de|do|da|dos|das|com|no|na|nos|nas|em|a|o|ao|à|pela|pelo|por|entre|sem|sobre)$")
    entradas = []
    termo, letra, buffer = None, None, ""
    for bruto in linhas:
        t = bruto.strip()
        if not t or re.fullmatch(r"[A-Za-z]", t):
            if t:
                letra = t.upper()
            continue
        if t.startswith("Estudo Sistematizado"):
            continue
        # continuação só de números de referência: "134a, 134b, 139"
        if re.fullmatch(r"[\d][\d\s,;a-z.\-–]*", t) and entradas and not buffer:
            entradas[-1]["refs"] += parsear_refs(t)
            continue
        texto = (buffer + " " + t).strip() if buffer else t
        if re.search(r"\s–\s*(\d|introd|concl|proleg)", texto):
            esquerda, refs = re.split(r"\s–\s*(?=\d|introd|concl|proleg)", texto, maxsplit=1)
            esquerda = esquerda.strip()
            era_buffer = bool(buffer)
            buffer = ""
            novo_termo = (not era_buffer and esquerda[:1].isupper() and letra
                          and not conectivo.search(esquerda)
                          and normalizar(esquerda)[:1] == letra.lower()
                          and (termo is None or normalizar(esquerda) > normalizar(termo)))
            if termo is None or novo_termo:
                termo = esquerda
                entradas.append({"termo": termo, "sub": None, "refs": parsear_refs(refs)})
            else:
                entradas.append({"termo": termo, "sub": esquerda, "refs": parsear_refs(refs)})
            continue
        if not buffer and t[:1].isupper() and " ver " in t:  # remissão: "Doença ver Enfermidade"
            termo, _, alvo = t.partition(" ver ")
            entradas.append({"termo": termo.strip(), "sub": None, "refs": [], "ver": alvo.strip()})
            continue
        if buffer or t[:1].islower() or conectivo.search(t):
            buffer = texto
        else:
            termo = t
    return entradas


# ----------------------------------------------------------------------------
# Principal
# ----------------------------------------------------------------------------
def extrair(caminho):
    paginas = carregar_paginas(caminho)
    modo_espaco = detectar_modo_espaco(paginas)
    pags = classificar(paginas)
    avisos = []
    capitulos, itens, textos_k = parsear_partes(pags, modo_espaco, avisos)
    textos = parsear_textos(pags, modo_espaco)
    introducao = montar_introducao(textos)
    indice = parsear_indice(pags, modo_espaco)

    perguntas = {it["id"]: it for it in itens}
    # índice geral → perguntas
    for e in indice:
        rotulo = e["termo"] + (f": {e['sub']}" if e["sub"] else "")
        for r in e["refs"]:
            alvo = perguntas.get(r) or textos.get(r)
            if alvo is not None:
                alvo.setdefault("indice", []).append(rotulo)
    for it in itens:
        it.setdefault("indice", [])
        it["temas"] = TEMAS_CAPITULO.get(it["capitulo"], [])

    # liga notas de rodapé às perguntas (chamada no texto + mesma página)
    notas_pag = {}
    for p in pags:
        for k in p["notas"]:
            notas_pag[k] = p["numero"]
    for it in itens:
        it["notas"] = sorted((n for n in it.pop("_chamadas")
                              if n in notas_pag and it["pagina_inicio"] <= notas_pag[n] <= it["pagina_fim"]),
                             key=int)

    # páginas
    paginas_out = {}
    for p in pags:
        if p["numero"] is None:
            continue
        pars = montar_paragrafos([(l, p["numero"]) for l in p["linhas"]], modo_espaco)
        paginas_out[str(p["numero"])] = {
            "pagina": p["numero"], "pdf_indice": p["pdf"], "regiao": p["regiao"],
            "cabecalho": p["cabecalho"], "texto": "\n".join(x["t"] for x in pars),
            "notas_rodape": p["notas"], "perguntas": []}
    for it in itens:
        for n in range(it["pagina_inicio"], it["pagina_fim"] + 1):
            if str(n) in paginas_out:
                paginas_out[str(n)]["perguntas"].append(it["id"])
    notas = {}
    for p in pags:
        for k, v in p["notas"].items():
            autor = "Allan Kardec" if v.startswith("Nota de Allan Kardec") else "Editora (FEB)" if v.startswith("N.E.") else "Tradutor"
            notas[k] = {"numero": int(k), "autor": autor, "texto": v, "pagina": p["numero"],
                        "perguntas": [it["id"] for it in itens if k in it["notas"]]}

    ligar_notas_introducao(introducao, notas)

    partes = []
    for i, (ordinal, titulo) in enumerate(PARTES, 1):
        caps = [c for c in capitulos if c["parte"] == i]
        partes.append({"numero": i, "ordinal": ordinal, "titulo": titulo,
                       "capitulos": [c["id"] for c in caps],
                       "pagina_inicio": caps[0]["pagina_inicio"] if caps else None,
                       "pagina_fim": caps[-1]["pagina_fim"] if caps else None})

    # validação
    nums = sorted({it["numero"] for it in itens})
    faltando = sorted(set(range(1, 1020)) - set(nums))
    sem_resp = [it["id"] for it in itens if not it["resposta"]]
    relatorio = {
        "perguntas_principais": len(nums), "subperguntas": sum(1 for it in itens if it["letra"]),
        "total_itens": len(itens), "faltando": faltando, "capitulos": len(capitulos),
        "itens_sem_resposta": sem_resp, "entradas_indice": len(indice),
        "textos": sorted(textos), "paginas": len(paginas_out), "modo_espaco": bool(modo_espaco)}

    db = {
        "meta": {"obra": "O Livro dos Espíritos", "autor": "Allan Kardec",
                 "traducao": "Guillon Ribeiro", "editora": "FEB",
                 "fonte": Path(caminho).name, "versao_esquema": 3},
        "partes": partes,
        "capitulos": {c["id"]: c for c in capitulos},
        "perguntas": perguntas,
        "textos_kardec": {k["id"]: k for k in textos_k},
        "textos": textos,
        "introducao": introducao,
        "paginas": paginas_out,
        "notas_rodape": notas,
        "indice_geral": indice,
    }
    return db, relatorio


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", help="PDF ou TXT de O Livro dos Espíritos")
    ap.add_argument("-o", "--saida", default=str(Path(__file__).with_name("dados") / "livro_dos_espiritos.json"))
    a = ap.parse_args()
    db, rel = extrair(a.entrada)
    saida = Path(a.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Gravado: {saida}")
    resumo = dict(rel)
    resumo["itens_sem_resposta"] = f"{len(rel['itens_sem_resposta'])}: {rel['itens_sem_resposta'][:40]}"
    resumo["faltando"] = f"{len(rel['faltando'])}: {rel['faltando'][:40]}"
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    if rel["faltando"]:
        print("ATENÇÃO: há perguntas faltando — confira o PDF.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
