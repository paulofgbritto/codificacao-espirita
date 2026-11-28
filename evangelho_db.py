#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evangelho_db — API de consulta local a "O Evangelho segundo o Espiritismo" (Allan Kardec).

Mesmo estilo de codificacao_db.py (O Livro dos Espíritos): só biblioteca padrão do Python,
nenhuma consulta passa por IA. Use --ids para receber apenas identificadores.

Banco: dados/evangelho.json (gerado por extrair_evangelho.py; vem em dados/evangelho.zip)

Identificadores (capítulo:item, como se cita o livro):
  5:4        capítulo V, item 4          (aceita também V:4, V.4, "5 4", "cap. V, item 4")
  0:0        Prefácio                    0:1 a 0:4   Introdução, partes I a IV
  0:4.1 …    Introdução IV, pontos I a XXI de Sócrates e Platão
  N4         nota de rodapé 4 do Evangelho
Listas: "5:4, 5:9 | N4"; faixas: "5:4-8" (no mesmo capítulo), "5:20-6:3" (entre capítulos),
"V" ou "cap 5" dentro de uma lista = capítulo inteiro.

───────────────────────────────── LINHA DE COMANDO ─────────────────────────────────
  python evangelho_db.py item 5:4                 um item (aceita V:4, "cap. V, item 4")
  python evangelho_db.py itens "5:4-8, 10:6, N4"  vários; faixas e capítulos inteiros
  python evangelho_db.py capitulo 5               capítulo (aceita V, "aflitos"); --expandir mostra os itens
  python evangelho_db.py capitulos                lista dos capítulos
  python evangelho_db.py secao "aflições"         itens de uma seção (subtítulo do livro)
  python evangelho_db.py secoes [5]               seções (de um capítulo ou de todos)
  python evangelho_db.py instrucoes 5             itens das Instruções dos Espíritos (de um capítulo ou todos)
  python evangelho_db.py autor Fénelon            comunicações assinadas por um Espírito
  python evangelho_db.py autores                  autores e quantas comunicações
  python evangelho_db.py local Paris              comunicações por local/ano ("Paris", "1862", "Bordeaux, 1861")
  python evangelho_db.py evangelho "Mateus 5"     itens que citam um evangelista/versículo ("Mateus, 5:17", "Lucas")
  python evangelho_db.py grupo "doentes"          capítulo XXVIII: preces de um grupo ("IV – Preces pelos…")
  python evangelho_db.py prefacio | introducao | socrates
  python evangelho_db.py pagina 120               itens de uma página (ou faixa "120-125")
  python evangelho_db.py buscar "caridade orgulho"   busca no texto (sem acento/maiúscula)
  python evangelho_db.py nota 4                   nota de rodapé
  python evangelho_db.py notas                    todas as notas de rodapé
  python evangelho_db.py notas_kardec             itens que têm "Nota –" de Kardec
  python evangelho_db.py vizinhos 5:4 --antes 2 --depois 2
  python evangelho_db.py ordenar "10:6, N4, 5:4, 5:4"   junta, normaliza e põe na ordem do livro
  python evangelho_db.py exportar capitulos_ese   1 .txt por capítulo (CAP00 = Prefácio e Introdução)
  python evangelho_db.py caminho itens/5:4/autor  acesso direto por caminho;  chaves itens/5:4
  python evangelho_db.py aleatorio | stats | ajuda
  python evangelho_db.py                          modo interativo

Opções comuns:
  --campos texto,secao,autor,local_data,nota_kardec,notas,pagina,capitulo,instrucoes  ("todos" = tudo)
  --formato texto|json|ids|curto    --limite N    --capitulo 5    --secao "..."
  --modo todas|qualquer|frase|regex (buscar)      --em texto,nota_kardec,secao,autor
  --instrucoes  (buscar só nas Instruções dos Espíritos)    --autor Nome (buscar só em um autor)

───────────────────────────────── EM PYTHON ─────────────────────────────────
  from evangelho_db import Evangelho
  ev = Evangelho()
  ev.item("V:4")                 -> dict;     ev["5:4"]  (atalho)
  ev.itens("5:4-8, N4")          -> [dict, ...]
  ev.capitulo("aflitos")["itens"]
  ev.secao("aflições"); ev.instrucoes(5); ev.autor("Agostinho"); ev.local("Paris, 1862")
  ev.evangelho("Mateus, 5"); ev.grupo("doentes"); ev.pagina(120)
  ev.buscar("perdão inimigos", modo="todas", capitulo=12, instrucoes=True)
  ev.nota(4); ev.ordenar("10:6, N4, 5:4"); ev.exportar_capitulos("capitulos_ese")
"""
import argparse
import json
import random
import re
import shlex
import sys
import unicodedata
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ARQUIVO_PADRAO = PASTA / "dados" / "evangelho.json"

CAMPOS_PADRAO = ["texto", "nota_kardec", "autor", "local_data", "notas"]
TODOS_CAMPOS = ["id", "capitulo", "capitulo_titulo", "secao", "grupo", "instrucoes", "pagina",
                "texto", "nota_kardec", "autor", "local_data", "notas"]
ROMANOS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV",
           "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI",
           "XXVII", "XXVIII"]


# ───────────────────────────── utilidades ─────────────────────────────
def norm(s):
    """minúsculas, sem acentos, pontuação vira espaço."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def romano_para_int(s):
    v = {"i": 1, "v": 5, "x": 10, "l": 50}
    s = s.lower()
    tot = 0
    for i, c in enumerate(s):
        tot += -v[c] if i + 1 < len(s) and v[s[i + 1]] > v[c] else v[c]
    return tot


def _num(s):
    s = str(s).strip().strip(".")
    if s.isdigit():
        return int(s)
    if re.fullmatch(r"[ivxlIVXL]+", s):
        return romano_para_int(s)
    return None


def tokens_aprox(texto):
    return max(1, round(len(texto) / 3.5))


class ErroConsulta(Exception):
    pass


# ───────────────────────────── banco ─────────────────────────────
class Evangelho:
    def __init__(self, arquivo=ARQUIVO_PADRAO):
        arquivo = Path(arquivo)
        if not arquivo.exists():
            raise FileNotFoundError(
                f"Banco não encontrado: {arquivo}\n"
                "Descompacte dados/evangelho.zip em dados/ ou gere com: "
                "python extrair_evangelho.py O-evangelho-segundo-o-espiritismo.pdf")
        self.db = json.loads(arquivo.read_text(encoding="utf-8"))
        self.I = self.db["itens"]
        self.N = self.db["notas"]
        self.ordem = list(self.db["ordem"])
        self.pos = {k: i for i, k in enumerate(self.ordem)}
        # capítulo 0 virtual: Prefácio e Introdução
        intro = [k for k in self.ordem if k.startswith("0:")]
        self.C = {0: {"numero": 0, "romano": "0", "titulo": "Prefácio e Introdução", "secoes": [],
                      "itens": intro, "pagina": self.I[intro[0]]["pagina_inicio"]}}
        for c in self.db["capitulos"]:
            d = dict(c)
            d["romano"] = ROMANOS[c["numero"]]
            self.C[c["numero"]] = d
        self._busca = {k: {c: norm(v.get(c) or "") for c in ("texto", "nota_kardec", "secao", "autor")}
                       for k, v in self.I.items()}

    # ---------- identificadores ----------
    def normalizar_id(self, ref):
        """'5:4', 'V:4', 'V.4', '5 4', 'cap. V, item 4', '0:4.3', 'prefacio' -> id do banco."""
        s = str(ref).strip()
        n = norm(s)
        if n in ("prefacio", "0"):
            return "0:0"
        t = re.sub(r"\b(cap[ií]tulo|cap|itens|item)\b\.?", " ", s.lower()).replace(",", " ")
        m = re.fullmatch(r"\s*([ivxl]+|\d{1,2})\s*(?::|\.|\s)\s*(\d{1,3})(?:\.(\d{1,2}))?\s*", t)
        if not m:
            raise ErroConsulta(f"Identificador inválido: {ref!r} (use 5:4, V:4 ou 0:4.3)")
        cap, item, sub = _num(m.group(1)), int(m.group(2)), m.group(3)
        return f"{cap}:{item}" + (f".{int(sub)}" if sub else "")

    def _existe(self, iid):
        if iid not in self.I:
            raise ErroConsulta(f"Item {iid} não existe")
        return iid

    def expandir(self, spec):
        """'5:4-8, 5:20-6:3, V, 10:6' -> ids existentes, na ordem do livro, sem repetidos."""
        ids = []
        partes = spec if isinstance(spec, (list, tuple)) else re.split(r"[;|,]+", str(spec))
        for parte in partes:
            p = str(parte).strip()
            if not p:
                continue
            mc = re.fullmatch(r"(?i)(?:cap(?:itulo|ítulo)?\.?\s*)?([ivxl]+|\d{1,2})", p)
            if mc:
                ids += self.capitulo(mc.group(1))["itens"]
                continue
            mf = re.fullmatch(r"(.+?)\s*(?:-|–|até)\s*(.+)", p)
            if mf:
                a = self._existe(self.normalizar_id(mf.group(1)))
                fim = mf.group(2).strip()
                if re.fullmatch(r"\d{1,3}", fim):              # 5:4-8  /  0:4.1-21
                    base = a.rsplit(".", 1)[0] + "." if "." in a else a.split(":")[0] + ":"
                    b = self._existe(base + fim)
                else:
                    b = self._existe(self.normalizar_id(fim))
                i, j = sorted((self.pos[a], self.pos[b]))
                ids += self.ordem[i:j + 1]
                continue
            ids.append(self._existe(self.normalizar_id(p)))
        vistos = set()
        return [i for i in sorted(ids, key=self.pos.get) if not (i in vistos or vistos.add(i))]

    # ---------- itens ----------
    def _completo(self, it):
        d = dict(it)
        c = self.C[it["capitulo"]]
        d["capitulo_titulo"] = (f"Cap. {c['romano']} – {c['titulo']}" if it["capitulo"] else
                                it.get("capitulo_titulo") or "Introdução")
        d["instrucoes"] = it.get("instrucoes_dos_espiritos", False)
        d["pagina"] = it["pagina_inicio"] if it["pagina_inicio"] == it["pagina_fim"] else f"{it['pagina_inicio']}-{it['pagina_fim']}"
        d["notas_ids"] = list(it.get("notas", []))
        d["notas"] = [f"[{n}] {self.N[n]['texto']}" for n in it.get("notas", [])]
        d["citacao"] = self.citacao(it["id"])
        d["tokens"] = tokens_aprox(it["texto"] + (it.get("nota_kardec") or ""))
        return d

    def citacao(self, iid):
        """Rodapé de citação, com o NOME do capítulo em caixa alta:
        'Evangelho segundo o Espiritismo, cap. BEM-AVENTURADOS OS AFLITOS, item 4'."""
        it = self.I[iid]
        if iid == "0:0":
            ref = "PREFÁCIO"
        elif it["capitulo"] == 0 and "." in iid:
            ref = f"INTRODUÇÃO, item IV, ponto {ROMANOS[it['item']]}"
        elif it["capitulo"] == 0:
            ref = f"INTRODUÇÃO, item {ROMANOS[it['item']]}"
        else:
            ref = f"cap. {it['capitulo_titulo'].upper()}, item {it['item']}"
        return f"Evangelho segundo o Espiritismo, {ref}"

    def item(self, ref):
        return self._completo(self.I[self._existe(self.normalizar_id(ref))])

    def itens(self, spec):
        return [self._completo(self.I[i]) for i in self.expandir(spec)]

    def __getitem__(self, ref):
        return self.item(ref)

    def vizinhos(self, ref, antes=1, depois=1):
        i = self.pos[self._existe(self.normalizar_id(ref))]
        return [self._completo(self.I[k]) for k in self.ordem[max(0, i - antes): i + depois + 1]]

    def aleatorio(self):
        return self._completo(self.I[random.choice(self.ordem)])

    # ---------- estrutura ----------
    def capitulo(self, ref):
        """5, 'V', 'cap. V', 'aflitos' (parte do título), 0 = Prefácio e Introdução."""
        s = str(ref).strip()
        n = _num(re.sub(r"(?i)^cap(?:itulo|ítulo)?\.?\s*", "", s))
        if n is None:
            achados = [c for c in self.C.values() if norm(s) and norm(s) in norm(c["titulo"])]
            if len(achados) == 1:
                return achados[0]
            raise ErroConsulta(f"Capítulo não encontrado: {ref!r}. Use 5, V ou parte do título"
                               + (f". Candidatos: {[c['numero'] for c in achados]}" if achados else ""))
        if n not in self.C:
            raise ErroConsulta(f"Capítulo {n} não existe (há 0 a 28)")
        return self.C[n]

    def capitulos(self):
        return [{"numero": c["numero"], "romano": c["romano"], "titulo": c["titulo"],
                 "itens": len(c["itens"]), "faixa": f"{c['itens'][0]}–{c['itens'][-1]}",
                 "pagina": c["pagina"]} for c in self.C.values()]

    def secao(self, nome, capitulo=None):
        alvo = norm(nome)
        cap = self.capitulo(capitulo)["numero"] if capitulo is not None else None
        grupos = {}
        for k in self.ordem:
            it = self.I[k]
            if it["secao"] and alvo in norm(it["secao"]) and (cap is None or it["capitulo"] == cap):
                grupos.setdefault((it["capitulo"], it["secao"]), []).append(k)
        return [{"capitulo": c, "secao": s, "itens": ids} for (c, s), ids in grupos.items()]

    def secoes(self, capitulo=None):
        cap = self.capitulo(capitulo)["numero"] if capitulo not in (None, "") else None
        out = {}
        for k in self.ordem:
            it = self.I[k]
            if cap is not None and it["capitulo"] != cap:
                continue
            chave = (it["capitulo"], it["secao"] or "(início do capítulo)")
            out.setdefault(chave, []).append(k)
        return [{"capitulo": c, "secao": s, "itens": f"{v[0]}–{v[-1]}" if len(v) > 1 else v[0]}
                for (c, s), v in out.items()]

    def instrucoes(self, capitulo=None):
        cap = self.capitulo(capitulo)["numero"] if capitulo not in (None, "") else None
        return [k for k in self.ordem if self.I[k].get("instrucoes_dos_espiritos")
                and (cap is None or self.I[k]["capitulo"] == cap)]

    def autor(self, nome=""):
        alvo = norm(nome)
        return [k for k in self.ordem if self.I[k].get("autor") and alvo in norm(self.I[k]["autor"])]

    def autores(self):
        cont = {}
        for k in self.ordem:
            a = self.I[k].get("autor")
            if a:
                cont.setdefault(a, []).append(k)
        return dict(sorted(cont.items(), key=lambda kv: (-len(kv[1]), norm(kv[0]))))

    def local(self, texto):
        alvo = norm(texto)
        return [k for k in self.ordem if self.I[k].get("local_data") and alvo in norm(self.I[k]["local_data"])]

    @staticmethod
    def _versiculos(spec):
        """'23:16 a 18, 21, 25, 26 e 33' (só a parte depois de ':') -> {16, 17, 18, 21, 25, 26, 33}"""
        out = set()
        for pedaco in re.split(r",|\be\b", spec):
            m = re.match(r"\s*(\d+)(?:\s*(?:a|-|–)\s*(\d+))?", pedaco)
            if m:
                a, b = int(m.group(1)), int(m.group(2) or m.group(1))
                out.update(range(a, b + 1))
        return out

    def referencias(self, iid):
        """Citações bíblicas de um item: [('mateus', 5, {17, 18}), ...]"""
        refs = []
        for tr in re.findall(r"\(([^()]*\d+:\d+[^()]*)\)", self.I[iid]["texto"]):
            livro = None
            for m in re.finditer(r"(?:([A-Za-zÀ-ÿ]+)\s*,\s*(?:(\d)a\s+Epístola\s*,\s*)?)?(\d+):([\d\s,ea–-]*\d)", tr):
                if m.group(1):
                    livro = norm(m.group(1)) + (f" {m.group(2)}a epistola" if m.group(2) else "")
                if livro:                     # "7:5" solto herda o livro anterior; sem livro, ignora
                    refs.append((livro, int(m.group(3)), self._versiculos(m.group(4))))
        return refs

    def evangelho(self, ref):
        """Itens que citam um livro bíblico/versículo: 'Mateus', 'Mateus 5', 'Mateus, 5:17', 'João 3:3'.
        Entende faixas do livro ('3:1 a 12' contém 3:3) e várias citações juntas ('Marcos, 10:19; Lucas, 18:20')."""
        m = re.fullmatch(r"\s*([^\d,:]+?)\s*,?\s*(\d+)?\s*(?::\s*(\d+))?\s*", str(ref))
        if not m:
            raise ErroConsulta("Use: Mateus | Mateus 5 | Mateus, 5:17")
        livro = norm(m.group(1)).split()[-1]
        cap = int(m.group(2)) if m.group(2) else None
        vers = int(m.group(3)) if m.group(3) else None
        return [k for k in self.ordem if any(
            l.startswith(livro) and (cap is None or c == cap) and (vers is None or vers in vs)
            for l, c, vs in self.referencias(k))]

    def grupo(self, nome=""):
        alvo = norm(nome)
        out = {}
        for k in self.ordem:
            g = self.I[k].get("grupo")
            if g and alvo in norm(g):
                out.setdefault(g, []).append(k)
        return [{"grupo": g, "itens": v} for g, v in out.items()]

    def prefacio(self):
        return self.item("0:0")

    def introducao(self):
        return [k for k in self.ordem if re.fullmatch(r"0:[1-4]", k)]

    def socrates(self):
        return [k for k in self.ordem if k.startswith("0:4.")]

    # ---------- páginas ----------
    def pagina(self, spec):
        m = re.fullmatch(r"\s*(\d+)\s*(?:-|–)\s*(\d+)\s*", str(spec))
        a, b = (int(m.group(1)), int(m.group(2))) if m else (int(spec), int(spec))
        return [k for k in self.ordem if self.I[k]["pagina_inicio"] <= b and self.I[k]["pagina_fim"] >= a]

    # ---------- busca ----------
    def buscar(self, consulta, modo="todas", em=("texto", "nota_kardec", "secao"),
               capitulo=None, secao=None, instrucoes=False, autor=None, limite=None):
        """modo: 'todas' (todas as palavras), 'qualquer', 'frase' (trecho exato) ou 'regex'."""
        if modo == "regex":
            rx = re.compile(consulta, re.I)
            teste = lambda txt: len(rx.findall(txt))
        elif modo == "frase":
            f = norm(consulta)
            teste = lambda txt: txt.count(f)
        else:
            palavras = [w for w in norm(consulta).split() if w]
            if not palavras:
                raise ErroConsulta("Consulta vazia")

            def teste(txt):
                c = [len(re.findall(rf"\b{re.escape(w)}", txt)) for w in palavras]
                return (sum(c) if all(c) else 0) if modo == "todas" else sum(c)
        cap = self.capitulo(capitulo)["numero"] if capitulo not in (None, "") else None
        res = []
        for k in self.ordem:
            it = self.I[k]
            if cap is not None and it["capitulo"] != cap:
                continue
            if secao and norm(secao) not in norm(it["secao"] or ""):
                continue
            if instrucoes and not it.get("instrucoes_dos_espiritos"):
                continue
            if autor and norm(autor) not in norm(it.get("autor") or ""):
                continue
            if modo == "todas":                 # todas as palavras no item, em qualquer campo
                txt = " ".join(self._busca[k][c] for c in em)
                pontos = teste(txt)
                onde = [c for c in em if pontos and teste(self._busca[k][c]) or
                        any(re.search(rf"\b{re.escape(w)}", self._busca[k][c]) for w in norm(consulta).split())]
                if pontos:
                    pontos += 2 * teste(self._busca[k]["secao"]) if "secao" in em else 0
            else:
                pontos, onde = 0, []
                for c in em:
                    n = teste(self._busca[k][c])
                    if n:
                        pontos += n * (3 if c == "secao" else 1)
                        onde.append(c)
            if pontos:
                res.append({"id": k, "pontos": pontos, "campos": onde})
        res.sort(key=lambda r: (-r["pontos"], self.pos[r["id"]]))
        return res[:limite] if limite else res

    def buscar_ids(self, consulta, ordem_do_livro=True, **kw):
        ids = [r["id"] for r in self.buscar(consulta, **kw)]
        return sorted(ids, key=self.pos.get) if ordem_do_livro else ids

    # ---------- notas ----------
    def nota(self, n):
        k = "N" + str(int(str(n).upper().lstrip("N")))
        if k not in self.N:
            raise ErroConsulta(f"Nota {k} não existe (há N1 a N{len(self.N)})")
        return self.N[k]

    def notas(self):
        return list(self.N.values())

    def notas_kardec(self):
        return [k for k in self.ordem if self.I[k].get("nota_kardec")]

    def separar_ids(self, spec):
        """'5:4, N4, 10:6' -> (ids de itens, ids de notas)"""
        partes = [x.strip() for x in re.split(r"[,;|]+", str(spec)) if x.strip()]
        notas = ["N" + str(int(x[1:])) for x in partes if re.fullmatch(r"[Nn]\d+", x)]
        itens = [x for x in partes if not re.fullmatch(r"[Nn]\d+", x)]
        return (self.expandir(itens) if itens else []), notas

    def ordenar(self, spec):
        """Junta, normaliza, remove duplicatas e põe na ordem do livro; a nota N vem logo após o seu item."""
        chaves = {}
        for x in [x.strip() for x in re.split(r"[,;|]+", str(spec)) if x.strip()]:
            if x.upper() == "NENHUMA":
                continue
            if re.fullmatch(r"[Nn]\d+", x):
                n = self.nota(x)
                chaves[n["id"]] = (self.pos[n["item"]], 1) if n.get("item") else (len(self.ordem), n["numero"])
            else:
                for i in self.expandir(x):
                    chaves[i] = (self.pos[i], 0)
        return sorted(chaves, key=chaves.get)

    # ---------- exportação para agentes ----------
    def texto_capitulo(self, numero, marcar_tokens=True):
        """Texto de um capítulo inteiro com [id], seções, Instruções, autores e notas, para agentes lerem."""
        c = self.capitulo(numero)
        cab = (f"# CAP{c['numero']:02d} – Prefácio e Introdução" if c["numero"] == 0 else
               f"# CAP{c['numero']:02d} – Capítulo {c['romano']} – {c['titulo']}")
        linhas = [cab, ""]
        secao = grupo = None
        instr = False
        for k in c["itens"]:
            it = self.I[k]
            if it.get("grupo") and it["grupo"] != grupo:
                grupo = it["grupo"]
                linhas += [f"## {grupo}", ""]
            if it.get("instrucoes_dos_espiritos") and not instr:
                instr = True
                linhas += ["## Instruções dos Espíritos", ""]
            if it["secao"] and it["secao"] != secao:
                secao = it["secao"]
                linhas += [f"### {secao}", ""]
            tok = f" (tokens: {tokens_aprox(it['texto'] + (it.get('nota_kardec') or ''))})" if marcar_tokens else ""
            linhas.append(f"[{k}]{tok} " + it["texto"])
            if it.get("autor"):
                linhas.append(f"— {it['autor']}" + (f" ({it['local_data']})" if it.get("local_data") else ""))
            if it.get("nota_kardec"):
                linhas.append(f"Nota de Kardec: {it['nota_kardec'].removeprefix('Nota – ')}")
            for n in it.get("notas", []):
                linhas.append(f"[{n}] Nota de rodapé: {self.N[n]['texto']}")
            linhas.append("")
        return "\n".join(linhas)

    def exportar_capitulos(self, pasta, marcar_tokens=True):
        """Grava CAP00.txt (Prefácio e Introdução) e CAP01.txt … CAP28.txt."""
        pasta = Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        arquivos = []
        for n in self.C:
            f = pasta / f"CAP{n:02d}.txt"
            f.write_text(self.texto_capitulo(n, marcar_tokens), encoding="utf-8")
            arquivos.append(str(f))
        return arquivos

    # ---------- caminhos ----------
    def obter(self, caminho):
        """'itens/5:4/autor', 'notas/N4/texto', 'capitulos/4/titulo' (lista: índice a partir de 0)."""
        atual = self.db
        for parte in [x for x in caminho.strip("/").split("/") if x]:
            if isinstance(atual, list):
                atual = atual[int(parte)]
            elif isinstance(atual, dict):
                if parte not in atual and atual is self.I:
                    parte = self.normalizar_id(parte)
                if parte not in atual:
                    raise ErroConsulta(f"Chave {parte!r} não existe em {caminho!r}")
                atual = atual[parte]
            else:
                raise ErroConsulta(f"{caminho!r}: não dá para entrar em um valor simples")
        return atual

    def chaves(self, caminho=""):
        v = self.obter(caminho) if caminho else self.db
        return list(v) if isinstance(v, dict) else list(range(len(v))) if isinstance(v, list) else []

    def estatisticas(self):
        it = self.I.values()
        return {
            "obra": self.db["meta"]["titulo"],
            "capitulos": len(self.db["capitulos"]),
            "itens": len(self.I),
            "itens_dos_capitulos": sum(len(c["itens"]) for c in self.db["capitulos"]),
            "introducao": len(self.introducao()), "pontos_socrates": len(self.socrates()),
            "secoes": sum(1 for s in self.secoes() if not s["secao"].startswith("(")),
            "instrucoes_dos_espiritos": len(self.instrucoes()),
            "comunicacoes_assinadas": sum(1 for x in it if x.get("autor")),
            "autores": len(self.autores()),
            "notas_de_rodape": len(self.N),
            "notas_de_kardec": len(self.notas_kardec()),
            "paginas": f"{min(x['pagina_inicio'] for x in it)}-{max(x['pagina_fim'] for x in it)}",
            "tokens_aprox": sum(tokens_aprox(x["texto"] + (x.get("nota_kardec") or "")) for x in it),
        }


# ───────────────────────────── saída ─────────────────────────────
def fmt_item(d, campos, formato):
    if formato == "ids":
        return d["id"]
    if formato == "curto":
        return f"{d['id']:>7} (p.{d['pagina']}) {d['texto'][:110].replace(chr(10), ' ')}"
    if formato == "json":
        return {c: d.get(c) for c in ["id"] + campos + ["citacao"]}
    cab = f"[{d['id']}]"
    if "pagina" in campos:
        cab += f"  p.{d['pagina']}"
    if "capitulo" in campos:
        cab += f"  {d['capitulo_titulo']}"
    if "secao" in campos and d.get("secao"):
        cab += f"  § {d['secao']}"
    if "instrucoes" in campos and d.get("instrucoes"):
        cab += "  (Instruções dos Espíritos)"
    linhas = [cab]
    if "texto" in campos:
        linhas.append(d["texto"])
    if "autor" in campos and d.get("autor"):
        linhas.append(f"— {d['autor']}" + (f" ({d['local_data']})" if d.get("local_data") and "local_data" in campos else ""))
    if "nota_kardec" in campos and d.get("nota_kardec"):
        linhas.append(f"Nota de Kardec: {d['nota_kardec'].removeprefix('Nota – ')}")
    if "notas" in campos:
        linhas += [f"Nota de rodapé {x}" for x in d.get("notas", [])]
    linhas.append(d["citacao"])
    return "\n".join(linhas)


def imprimir_itens(lista, formato, campos):
    if formato == "ids":
        print(", ".join(d["id"] for d in lista))
    elif formato == "json":
        print(json.dumps([fmt_item(d, campos, "json") for d in lista], ensure_ascii=False, indent=1))
    else:
        print(("\n" if formato == "curto" else "\n\n").join(fmt_item(d, campos, formato) for d in lista))


def imprimir(obj, formato):
    if isinstance(obj, str) and formato != "json":
        print(obj)
    elif formato == "ids" and isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        print(", ".join(obj))
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=1))


# ───────────────────────────── CLI ─────────────────────────────
def construir_parser():
    ap = argparse.ArgumentParser(prog="evangelho_db.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", nargs="?")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--campos", default=None, help="ex.: texto,autor ou 'todos'")
    ap.add_argument("--formato", default="texto", choices=["texto", "json", "ids", "curto"])
    ap.add_argument("--ids", action="store_true", help="atalho para --formato ids")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--capitulo")
    ap.add_argument("--secao")
    ap.add_argument("--modo", default="todas", choices=["todas", "qualquer", "frase", "regex"])
    ap.add_argument("--em", default="texto,nota_kardec,secao")
    ap.add_argument("--instrucoes", action="store_true")
    ap.add_argument("--autor")
    ap.add_argument("--antes", type=int, default=1)
    ap.add_argument("--depois", type=int, default=1)
    ap.add_argument("--expandir", action="store_true", help="mostrar o conteúdo dos itens encontrados")
    ap.add_argument("--sem-tokens", action="store_true", help="exportar: sem '(tokens: N)' após o id")
    ap.add_argument("--banco", default=str(ARQUIVO_PADRAO))
    return ap


def executar(ev, a):
    fmt = "ids" if a.ids else a.formato
    campos = TODOS_CAMPOS[1:] if a.campos == "todos" else (a.campos.split(",") if a.campos else CAMPOS_PADRAO)
    arg = " ".join(a.args)
    c = (a.comando or "").lower()

    def lista(ids, rotulo=None):
        """Lista de ids: com --expandir (ou formato json) mostra os itens; senão, 1 linha por item."""
        if fmt == "ids":
            print(", ".join(ids))
        elif a.expandir or fmt == "json":
            imprimir_itens([ev.item(i) for i in ids], fmt, campos)
        else:
            if rotulo:
                print(rotulo)
            imprimir_itens([ev.item(i) for i in ids], "curto", campos)

    if c in ("item", "i"):
        imprimir_itens([ev.item(arg)], fmt, campos)
    elif c in ("itens", "lista"):
        its, nts = ev.separar_ids(arg)
        if its:
            imprimir_itens(ev.itens(its), fmt, campos)
        if nts:
            if its and fmt != "ids":
                print()
            imprimir(", ".join(nts) if fmt == "ids" else [ev.nota(n) for n in nts] if fmt == "json" else
                     "\n\n".join(f"[{n['id']}] p.{n['pagina']} (item {n['item']}) {n['texto']}" for n in map(ev.nota, nts)), fmt)
    elif c in ("capitulo", "cap"):
        cap = ev.capitulo(arg)
        if fmt == "ids" or a.expandir:
            lista(cap["itens"])
        else:
            imprimir({"numero": cap["numero"], "romano": cap["romano"], "titulo": cap["titulo"],
                      "secoes": cap["secoes"], "itens": len(cap["itens"]),
                      "faixa": f"{cap['itens'][0]}–{cap['itens'][-1]}",
                      "instrucoes": ev.instrucoes(cap["numero"]), "pagina": cap["pagina"]}, fmt)
    elif c == "capitulos":
        cs = ev.capitulos()
        imprimir(cs if fmt == "json" else "\n".join(
            f"{x['numero']:>2} {x['romano']:>7}  {x['titulo']:<60} {x['itens']:>3} itens  ({x['faixa']}, p.{x['pagina']})"
            for x in cs), fmt)
    elif c == "secao":
        res = ev.secao(arg, a.capitulo)
        if fmt == "ids" or a.expandir:
            lista([i for r in res for i in r["itens"]])
        else:
            imprimir(res if fmt == "json" else "\n".join(
                f"cap. {r['capitulo']} § {r['secao']}: {', '.join(r['itens'])}" for r in res) or "(nada)", fmt)
    elif c == "secoes":
        res = ev.secoes(arg or a.capitulo)
        imprimir(res if fmt == "json" else "\n".join(f"{r['capitulo']:>2}  {r['itens']:<13} {r['secao']}" for r in res), fmt)
    elif c in ("instrucoes", "instruções"):
        lista(ev.instrucoes(arg or a.capitulo), "Instruções dos Espíritos:")
    elif c == "autor":
        ids = ev.autor(arg)
        lista(ids) if (fmt == "ids" or a.expandir) else print(
            "\n".join(f"{i:>6}  {ev.I[i]['autor']}" + (f" ({ev.I[i]['local_data']})" if ev.I[i]['local_data'] else "")
                      for i in ids) or "(nenhuma)")
    elif c == "autores":
        au = ev.autores()
        imprimir(au if fmt == "json" else "\n".join(f"{len(v):>3}  {k}: {', '.join(v)}" for k, v in au.items()), fmt)
    elif c == "local":
        ids = ev.local(arg)
        lista(ids) if (fmt == "ids" or a.expandir) else print(
            "\n".join(f"{i:>6}  {ev.I[i]['autor']} ({ev.I[i]['local_data']})" for i in ids) or "(nenhuma)")
    elif c in ("evangelho", "versiculo", "versículo"):
        lista(ev.evangelho(arg), f"Itens que citam {arg}:")
    elif c == "grupo":
        res = ev.grupo(arg)
        if fmt == "ids" or a.expandir:
            lista([i for r in res for i in r["itens"]])
        else:
            imprimir(res if fmt == "json" else "\n".join(f"{r['grupo']}: {', '.join(r['itens'])}" for r in res) or "(nada)", fmt)
    elif c in ("prefacio", "prefácio"):
        imprimir_itens([ev.prefacio()], fmt, campos)
    elif c in ("introducao", "introdução"):
        lista(ev.introducao(), "Introdução (partes I a IV):")
    elif c in ("socrates", "sócrates"):
        lista(ev.socrates(), "Introdução IV — Sócrates e Platão:")
    elif c in ("pagina", "paginas", "pg"):
        lista(ev.pagina(arg), f"Página {arg}:")
    elif c in ("buscar", "busca", "b"):
        res = ev.buscar(arg, modo=a.modo, em=a.em.split(","), capitulo=a.capitulo, secao=a.secao,
                        instrucoes=a.instrucoes, autor=a.autor, limite=a.limite)
        if fmt == "ids":
            print(", ".join(sorted((r["id"] for r in res), key=ev.pos.get)))
        elif a.expandir:
            imprimir_itens([ev.item(r["id"]) for r in res], fmt, campos)
        elif fmt == "json":
            imprimir(res, fmt)
        else:
            print(f"{len(res)} resultado(s)")
            for r in res:
                d = ev.item(r["id"])
                print(f"{r['id']:>7} [{r['pontos']:>2}] p.{d['pagina']}  {d['texto'][:100]}")
    elif c == "nota":
        n = ev.nota(arg)
        imprimir(n if fmt == "json" else f"[{n['id']}] p.{n['pagina']} (item {n['item']}) {n['texto']}", fmt)
    elif c == "notas":
        ns = ev.notas()
        imprimir(ns if fmt == "json" else ", ".join(n["id"] for n in ns) if fmt == "ids" else
                 "\n".join(f"[{n['id']}] item {n['item']}: {n['texto'][:110]}" for n in ns), fmt)
    elif c == "notas_kardec":
        lista(ev.notas_kardec(), "Itens com nota de Kardec:")
    elif c in ("vizinhos", "contexto"):
        imprimir_itens(ev.vizinhos(arg, a.antes, a.depois), fmt, campos)
    elif c in ("aleatorio", "aleatório"):
        imprimir_itens([ev.aleatorio()], fmt, campos)
    elif c == "ordenar":
        print(", ".join(ev.ordenar(arg)))
    elif c == "exportar":
        arqs = ev.exportar_capitulos(arg or "capitulos_ese", not a.sem_tokens)
        print(f"{len(arqs)} arquivos em {Path(arg or 'capitulos_ese').resolve()}")
    elif c in ("caminho", "obter", "get"):
        imprimir(ev.obter(arg), fmt)
    elif c in ("chaves", "keys", "ls"):
        ch = ev.chaves(arg)
        imprimir(", ".join(map(str, ch)) if fmt != "json" else ch, fmt)
    elif c in ("stats", "estatisticas"):
        imprimir(ev.estatisticas(), fmt)
    elif c in ("ajuda", "help", "?"):
        print(__doc__)
    else:
        raise ErroConsulta(f"Comando desconhecido: {a.comando!r}. Use: python evangelho_db.py ajuda")


def interativo(ev, parser):
    print("O Evangelho segundo o Espiritismo — modo interativo. Ex.: item 5:4 | buscar caridade --ids | sair")
    while True:
        try:
            linha = input("ese> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if linha in ("sair", "exit", "quit"):
            break
        if not linha:
            continue
        try:
            executar(ev, parser.parse_args(shlex.split(linha)))
        except SystemExit:
            pass
        except (ErroConsulta, KeyError, ValueError) as e:
            print("Erro:", e)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # acentos no terminal do Windows
    parser = construir_parser()
    a = parser.parse_args(argv)
    ev = Evangelho(a.banco)
    if not a.comando:
        interativo(ev, parser)
        return
    try:
        executar(ev, a)
    except (ErroConsulta, KeyError, ValueError) as e:
        print("Erro:", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
