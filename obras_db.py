#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obras_db — API de consulta local a O Livro dos Médiuns, O Céu e o Inferno e A Gênese (Allan Kardec).

Mesmo estilo de evangelho_db.py: só biblioteca padrão do Python, nenhuma consulta passa por IA.
O primeiro argumento é o livro:  mediuns (lm) | ceu (ci) | genese (ag).  --ids devolve só identificadores.

Bancos (gerados por extrair_obras.py; vêm compactados nos .zip de dados/):
  dados/livro_dos_mediuns.json   dados/ceu_e_inferno.json   dados/genese.json

Identificadores
  O Livro dos Médiuns
    159        item 159 (itens 1 a 350 numerados no livro inteiro; aceita "item 159")
    I3         Introdução, parágrafo 3
    R5         cap. XXX, Regulamento, art. 5º (aceita "art 5"); R0 = preâmbulo
    D12        cap. XXXI, Dissertações espíritas, dissertação XII (aceita "D XII"); D0 = abertura
    V3         cap. XXXII, Vocabulário espírita, 3º verbete (aceita "verbete Agênere")
  O Céu e o Inferno
    7:3        Primeira Parte, cap. VII, item 3 (aceita VII:3, "cap. VII, item 3"); 7:0 = texto antes do item 1
    E1:3       Segunda Parte, cap. I (O passamento), item 3
    E2:1       Segunda Parte, cap. II, exemplo 1; E2:1.2 = exemplo 1, comunicação II
               (um exemplo dividido, como E2:1, vale pelas comunicações todas numa lista)
  A Gênese
    6:12       cap. VI, item 12 (aceita VI:12, "cap. VI, item 12"); 6:0 = texto antes do item 1
    I3         Introdução, parágrafo 3
  Nos três: N4 = nota de rodapé.
Listas: "159-162, R5 | N4"; faixas: "6:3-8", "E2:1-4"; capítulo inteiro numa lista: "cap 14",
"XIV", "2.14" (parte.capítulo) ou, no Céu e Inferno, "E4" (Segunda Parte, cap. IV).

───────────────────────────────── LINHA DE COMANDO ─────────────────────────────────
  python obras_db.py mediuns item 159              um item
  python obras_db.py ceu itens "E2:1, 7:3-5, N4"   vários; faixas e capítulos inteiros
  python obras_db.py genese capitulo 14            capítulo (aceita XIV, 2.14 ou parte do título);
                                                   --expandir mostra os itens
  python obras_db.py <livro> capitulos | partes
  python obras_db.py <livro> secao "obsessão"      itens de uma seção (subtítulo do livro)
  python obras_db.py <livro> secoes [14]
  python obras_db.py <livro> autor "São Luís"      comunicações assinadas;  autores
  python obras_db.py <livro> local Paris           por local/data da assinatura
  python obras_db.py <livro> pagina 120            itens de uma página (ou "120-125")
  python obras_db.py <livro> buscar "obsessão orgulho"   busca no texto (sem acento/maiúscula)
  python obras_db.py <livro> nota 4 | notas
  python obras_db.py <livro> vizinhos 159 --antes 2 --depois 2
  python obras_db.py <livro> ordenar "R5, 159, N4, 159"   junta, normaliza e põe na ordem do livro
  python obras_db.py <livro> exportar pasta        1 .txt por capítulo (P0C00 = Introdução)
  python obras_db.py <livro> caminho itens/159/texto;   chaves itens
  python obras_db.py <livro> aleatorio | stats | ajuda
  python obras_db.py <livro>                       modo interativo
  Próprios de cada livro:
    mediuns  introducao | regulamento | dissertacoes | vocabulario [termo]
    ceu      exemplo "Sanson" | exemplos [cap] | codigo_penal
    genese   introducao | grupo "fluidos"

Opções: --campos texto,secao,autor,local_data,notas,pagina,capitulo ("todos")   --formato texto|json|ids|curto
        --limite N   --capitulo 14   --secao "..."   --modo todas|qualquer|frase|regex   --em texto,secao,autor
        --autor Nome   --antes N --depois N   --expandir   --sem-tokens   --banco arquivo.json

───────────────────────────────── EM PYTHON ─────────────────────────────────
  from obras_db import Obra
  lm = Obra("mediuns"); lm.item("159"); lm.itens("159-162, R5, N4"); lm.buscar("obsessão")
  ci = Obra("ceu");     ci.exemplo("Sanson"); ci.item("E2:1.2")["citacao"]
  ag = Obra("genese");  ag.capitulo("XIV")["itens"]; ag.grupo("fluidos")
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

LIVROS = {
    "mediuns": {"arquivo": "livro_dos_mediuns.json", "zip": "livro_dos_mediuns.zip", "prompt": "lm"},
    "ceu": {"arquivo": "ceu_e_inferno.json", "zip": "ceu_e_inferno.zip", "prompt": "ci"},
    "genese": {"arquivo": "genese.json", "zip": "genese.zip", "prompt": "ag"},
}
APELIDOS = {"lm": "mediuns", "medium": "mediuns", "mediuns": "mediuns", "livro dos mediuns": "mediuns",
            "livro_dos_mediuns": "mediuns", "ci": "ceu", "ceu": "ceu", "inferno": "ceu",
            "ceu e inferno": "ceu", "ceu_e_inferno": "ceu", "o ceu e o inferno": "ceu",
            "ag": "genese", "gen": "genese", "genese": "genese", "a genese": "genese"}

CAMPOS_PADRAO = ["texto", "autor", "local_data", "notas"]
TODOS_CAMPOS = ["id", "capitulo", "secao", "grupo", "pagina", "texto", "autor", "local_data", "notas"]


# ───────────────────────────── utilidades ─────────────────────────────
def norm(s):
    """minúsculas, sem acentos, pontuação vira espaço."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def romano_para_int(s):
    v = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    s = s.lower()
    tot = 0
    for i, c in enumerate(s):
        tot += -v[c] if i + 1 < len(s) and v[s[i + 1]] > v[c] else v[c]
    return tot


def romano(n):
    tab = [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s = ""
    for v, r in tab:
        while n >= v:
            s += r
            n -= v
    return s or "0"


def _num(s):
    s = str(s).strip().strip(".")
    if s.isdigit():
        return int(s)
    if re.fullmatch(r"[ivxlcIVXLC]+", s):
        return romano_para_int(s)
    return None


def tokens_aprox(texto):
    return max(1, round(len(texto) / 3.5))


def livro_chave(nome):
    n = norm(nome).replace("_", " ")
    if n in APELIDOS:
        return APELIDOS[n]
    raise ErroConsulta(f"Livro desconhecido: {nome!r}. Use mediuns (lm), ceu (ci) ou genese (ag)")


class ErroConsulta(Exception):
    pass


# ───────────────────────────── banco ─────────────────────────────
class Obra:
    def __init__(self, livro="mediuns", arquivo=None):
        self.livro = livro_chave(livro)
        cfg = LIVROS[self.livro]
        arquivo = Path(arquivo) if arquivo else PASTA / "dados" / cfg["arquivo"]
        if not arquivo.exists():
            raise FileNotFoundError(f"Banco não encontrado: {arquivo}\n"
                                    f"Descompacte dados/{cfg['zip']} em dados/ ou gere com extrair_obras.py")
        self.db = json.loads(arquivo.read_text(encoding="utf-8"))
        self.I = self.db["itens"]
        self.N = self.db["notas"]
        self.ordem = list(self.db["ordem"])
        self.pos = {k: i for i, k in enumerate(self.ordem)}
        self.titulo = self.db["meta"]["titulo"]
        self.curto = self.db["meta"]["titulo_curto"]
        self.P = {p["numero"]: p for p in self.db["partes"]}
        self.C = {}
        intro = [k for k in self.ordem if self.I[k]["tipo"] == "introducao"]
        if intro:
            self.C["0.0"] = {"chave": "0.0", "parte": 0, "numero": 0, "romano": "0", "titulo": "Introdução",
                             "secoes": [], "itens": intro, "pagina": self.I[intro[0]]["pagina_inicio"]}
        for c in self.db["capitulos"]:
            d = dict(c)
            d["romano"] = romano(c["numero"])
            self.C[c["chave"]] = d
        self.grupos_id = {}                         # "E2:1" -> ["E2:1.1", "E2:1.2", ...]
        for k in self.ordem:
            m = re.fullmatch(r"(E\d+:\d+)\.\d+", k)
            if m:
                self.grupos_id.setdefault(m.group(1), []).append(k)
        self._busca = {k: {c: norm(v.get(c) or "") for c in ("texto", "secao", "autor", "local_data", "grupo")}
                       for k, v in self.I.items()}

    # ---------- identificadores ----------
    def normalizar_id(self, ref):
        s = str(ref).strip()
        n = norm(s)
        m = re.fullmatch(r"(?:n|nota)\s*(\d{1,3})", n)
        if m:
            return "N" + str(int(m.group(1)))
        if self.livro == "mediuns":
            m = re.fullmatch(r"(?:item\s*)?(\d{1,3})", n)
            if m:
                return str(int(m.group(1)))
            m = re.fullmatch(r"([irdv])\s*(\d{1,3})", n)
            if m:
                return m.group(1).upper() + str(int(m.group(2)))
            m = re.fullmatch(r"(?:introducao|intro|paragrafo)\s*(\d{1,3})", n)
            if m:
                return "I" + str(int(m.group(1)))
            m = re.fullmatch(r"art(?:igo)?\s*(\d{1,2})\s*[oº]?", n)
            if m:
                return "R" + str(int(m.group(1)))
            m = re.fullmatch(r"(?:d|dissertacao)\s*([ivxl]+)", n)
            if m:
                return "D" + str(romano_para_int(m.group(1)))
            m = re.fullmatch(r"verbete\s+(.+)", n)
            if m:
                achados = self.vocabulario(m.group(1))
                if len(achados) == 1:
                    return achados[0]
            raise ErroConsulta(f"Identificador inválido: {ref!r} (use 159, I3, R5, D12, V3 ou N4)")
        if self.livro == "genese":
            m = re.fullmatch(r"(?i)(?:i|introdu[cç][aã]o|intro)\s*(\d{1,3})", s)   # I3 (I:3 = cap. I, item 3)
            if m:
                return "I" + str(int(m.group(1)))
        t = re.sub(r"\b(cap[ií]tulo|cap|itens|item)\b\.?", " ", s.lower()).replace(",", " ")
        m = re.fullmatch(r"\s*(e\s*)?([ivxl]+|\d{1,2})\s*(?::|\.|\s)\s*(\d{1,3})(?:\.(\d{1,2}))?\s*", t)
        if not m or (m.group(1) and self.livro != "ceu"):
            dica = "7:3, VII:3, E2:1 ou E2:1.2" if self.livro == "ceu" else "6:12, VI:12 ou I3"
            raise ErroConsulta(f"Identificador inválido: {ref!r} (use {dica})")
        pre = "E" if m.group(1) else ""
        return f"{pre}{_num(m.group(2))}:{int(m.group(3))}" + (f".{int(m.group(4))}" if m.group(4) else "")

    def _existe(self, iid):
        if iid not in self.I and iid not in self.grupos_id:
            raise ErroConsulta(f"{iid} não existe em {self.titulo}")
        return iid

    def _primeiro(self, iid):
        return self.grupos_id[iid][0] if iid in self.grupos_id else self._existe(iid)

    def _ultimo(self, iid):
        return self.grupos_id[iid][-1] if iid in self.grupos_id else self._existe(iid)

    def _ref_capitulo(self, p):
        """Chave do capítulo se p for referência de capítulo numa lista; senão None."""
        q = p.strip()
        if re.fullmatch(r"\d\.\d{1,2}", q) and q in self.C:
            return q
        m = re.fullmatch(r"(?i)cap(?:[ií]tulo)?\.?\s*(e\s*)?([ivxlc]+|\d{1,2})", q)
        if not m:
            m = re.fullmatch(r"(?i)(e)\s*([ivxlc]+|\d{1,2})", q) if self.livro == "ceu" else None
        if not m:
            m = re.fullmatch(r"()([IVXLC]+)", q)
            if not m and self.livro != "mediuns":
                m = re.fullmatch(r"()(\d{1,2})", q)
        if not m:
            return None
        num = _num(m.group(2))
        parte = 2 if (m.group(1) or "").strip() else None
        return self.capitulo(num if parte is None else f"2.{num}")["chave"]

    def expandir(self, spec):
        """'159-162, R5, cap 14' / 'E2:1, 7:3-5' -> ids existentes, na ordem do livro, sem repetidos."""
        ids = []
        partes = spec if isinstance(spec, (list, tuple)) else re.split(r"[;|,]+", str(spec))
        for parte in partes:
            p = str(parte).strip()
            if not p:
                continue
            chave = self._ref_capitulo(p)
            if chave:
                ids += self.C[chave]["itens"]
                continue
            mf = re.fullmatch(r"(.+?)\s*(?:-|–|até)\s*(.+)", p)
            if mf:
                a = self._primeiro(self.normalizar_id(mf.group(1)))
                fim = mf.group(2).strip()
                if re.fullmatch(r"\d{1,3}", fim):
                    if re.fullmatch(r"\d+", a):
                        b = fim
                    elif ":" in a and "." in a.split(":")[1]:
                        b = a.rsplit(".", 1)[0] + "." + fim
                    elif ":" in a:
                        b = a.split(":")[0] + ":" + fim
                    else:
                        b = re.match(r"[A-Z]+", a).group(0) + fim
                else:
                    b = self.normalizar_id(fim)
                b = self._ultimo(b)
                i, j = sorted((self.pos[a], self.pos[b]))
                ids += self.ordem[i:j + 1]
                continue
            iid = self._existe(self.normalizar_id(p))
            ids += self.grupos_id.get(iid) or [iid]
        vistos = set()
        return [i for i in sorted(ids, key=self.pos.get) if not (i in vistos or vistos.add(i))]

    # ---------- itens ----------
    def rotulo_capitulo(self, it):
        if it["tipo"] == "introducao":
            return "Introdução"
        c = self.C[it["capitulo_chave"]]
        parte = (it.get("parte_titulo") or "").split(" – ")[0]
        return (f"{parte}, " if parte else "") + f"cap. {c['romano']} – {c['titulo']}"

    def _completo(self, it):
        d = dict(it)
        d["capitulo_rotulo"] = self.rotulo_capitulo(it)
        d["pagina"] = (it["pagina_inicio"] if it["pagina_inicio"] == it["pagina_fim"]
                       else f"{it['pagina_inicio']}-{it['pagina_fim']}")
        d["notas_ids"] = list(it.get("notas", []))
        d["notas"] = [f"[{n}] {self.N[n]['texto']}" for n in it.get("notas", [])]
        d["tokens"] = tokens_aprox(it["texto"])
        return d

    def citacao(self, iid):
        return self.I[self._existe(iid)]["citacao"]

    def item(self, ref):
        iid = self._existe(self.normalizar_id(ref))
        if iid in self.grupos_id:
            raise ErroConsulta(f"{iid} está dividido em {', '.join(self.grupos_id[iid])}: use itens {iid}")
        return self._completo(self.I[iid])

    def itens(self, spec):
        return [self._completo(self.I[i]) for i in self.expandir(spec)]

    def __getitem__(self, ref):
        return self.item(ref)

    def vizinhos(self, ref, antes=1, depois=1):
        i = self.pos[self._primeiro(self.normalizar_id(ref))]
        return [self._completo(self.I[k]) for k in self.ordem[max(0, i - antes): i + depois + 1]]

    def aleatorio(self):
        return self._completo(self.I[random.choice(self.ordem)])

    # ---------- estrutura ----------
    def capitulo(self, ref):
        """'2.14' (parte.capítulo), 14, 'XIV', 'cap. XIV', 'E4' (Céu e Inferno), parte do título; 0 = Introdução."""
        s = str(ref).strip()
        if s in self.C:
            return self.C[s]
        m = re.fullmatch(r"(?i)(?:cap(?:[ií]tulo)?\.?\s*)?(e\s*)?([ivxlc]+|\d{1,2})", s)
        if m:
            n = _num(m.group(2))
            cands = [c for c in self.C.values() if c["numero"] == n and (not m.group(1) or c["parte"] == 2)]
            if cands:
                return cands[0]
            raise ErroConsulta(f"Capítulo {s} não existe em {self.titulo}")
        achados = [c for c in self.C.values() if norm(s) and norm(s) in norm(c["titulo"])]
        if len(achados) == 1:
            return achados[0]
        raise ErroConsulta(f"Capítulo não encontrado: {ref!r}. Use 2.14, XIV ou parte do título"
                           + (f". Candidatos: {[c['chave'] for c in achados]}" if achados else ""))

    def capitulos(self):
        return [{"chave": c["chave"], "parte": c["parte"], "numero": c["numero"], "romano": c["romano"],
                 "titulo": c["titulo"], "itens": len(c["itens"]), "faixa": f"{c['itens'][0]}–{c['itens'][-1]}",
                 "pagina": c["pagina"], "tokens": sum(tokens_aprox(self.I[k]["texto"]) for k in c["itens"])}
                for c in self.C.values()]

    def partes(self):
        return [{"numero": p["numero"], "titulo": p["titulo"], "pagina": p["pagina"],
                 "capitulos": [c["chave"] for c in self.C.values() if c["parte"] == p["numero"]]}
                for p in self.P.values()]

    def secao(self, nome, capitulo=None):
        alvo = norm(nome)
        chave = self.capitulo(capitulo)["chave"] if capitulo is not None else None
        grupos = {}
        for k in self.ordem:
            it = self.I[k]
            if it.get("secao") and alvo in norm(it["secao"]) and (chave is None or it.get("capitulo_chave") == chave):
                grupos.setdefault((it.get("capitulo_chave"), it["secao"]), []).append(k)
        return [{"capitulo": c, "secao": s, "itens": ids} for (c, s), ids in grupos.items()]

    def secoes(self, capitulo=None):
        chave = self.capitulo(capitulo)["chave"] if capitulo else None
        vistos = {}
        for k in self.ordem:
            it = self.I[k]
            if chave and it.get("capitulo_chave") != chave:
                continue
            ch = (it.get("capitulo_chave") or "0.0", it.get("secao") or "(sem seção)")
            vistos.setdefault(ch, []).append(k)
        return [{"capitulo": c, "secao": s, "itens": f"{ids[0]}–{ids[-1]}" if len(ids) > 1 else ids[0]}
                for (c, s), ids in vistos.items()]

    def autor(self, nome=""):
        alvo = norm(nome)
        return [k for k in self.ordem if self.I[k].get("autor") and alvo in norm(self.I[k]["autor"])]

    def autores(self):
        res = {}
        for k in self.ordem:
            if self.I[k].get("autor"):
                res.setdefault(self.I[k]["autor"], []).append(k)
        return dict(sorted(res.items(), key=lambda kv: (-len(kv[1]), kv[0])))

    def local(self, texto):
        alvo = norm(texto)
        return [k for k in self.ordem if alvo and alvo in self._busca[k]["local_data"]]

    def pagina(self, spec):
        a, _, b = str(spec).partition("-")
        a, b = int(a), int(b or a)
        return [k for k in self.ordem if self.I[k]["pagina_inicio"] <= b and self.I[k]["pagina_fim"] >= a]

    def buscar(self, consulta, modo="todas", em=("texto", "secao"), capitulo=None, secao=None, autor=None,
               limite=None, **_):
        chave = self.capitulo(capitulo)["chave"] if capitulo is not None else None
        if modo == "regex":
            rx = re.compile(consulta, re.I)

            def teste(txt):
                return len(rx.findall(txt))
        else:
            termos = [norm(consulta)] if modo == "frase" else norm(consulta).split()

            def teste(txt):
                achou = [t for t in termos if t in txt]
                if modo == "todas" and len(achou) < len(termos):
                    return 0
                return sum(txt.count(t) for t in achou)
        res = []
        for k in self.ordem:
            it = self.I[k]
            if chave and it.get("capitulo_chave") != chave:
                continue
            if secao and norm(secao) not in norm(it.get("secao") or ""):
                continue
            if autor and norm(autor) not in norm(it.get("autor") or ""):
                continue
            pts = 0
            for campo in em:
                txt = (it.get(campo) or "") if modo == "regex" else self._busca[k].get(campo, "")
                pts += teste(txt)
            if pts:
                res.append({"id": k, "pontos": pts, "capitulo": it.get("capitulo_chave"), "secao": it.get("secao")})
        res.sort(key=lambda r: (-r["pontos"], self.pos[r["id"]]))
        return res[:limite] if limite else res

    def buscar_ids(self, consulta, ordem_do_livro=True, **kw):
        ids = [r["id"] for r in self.buscar(consulta, **kw)]
        return sorted(ids, key=self.pos.get) if ordem_do_livro else ids

    def nota(self, n):
        nid = self.normalizar_id(n if str(n).upper().startswith("N") else f"N{n}")
        if nid not in self.N:
            raise ErroConsulta(f"Nota {nid} não existe")
        return self.N[nid]

    def notas(self):
        return list(self.N.values())

    def separar_ids(self, spec):
        partes = [p.strip() for p in re.split(r"[;|,]+", str(spec)) if p.strip()]
        notas = [self.normalizar_id(p) for p in partes if re.fullmatch(r"(?i)n\s*\d{1,3}|nota\s*\d{1,3}", p)]
        resto = [p for p in partes if not re.fullmatch(r"(?i)n\s*\d{1,3}|nota\s*\d{1,3}", p)]
        return resto, notas

    def ordenar(self, spec):
        """Junta, normaliza, tira repetidos e põe na ordem do livro (notas no fim, em ordem numérica)."""
        its, nts = self.separar_ids(spec)
        notas = sorted(set(nts), key=lambda x: int(x[1:]))
        return (self.expandir(its) if its else []) + [n for n in notas if n in self.N]

    # ---------- próprios de cada livro ----------
    def introducao(self):
        return [k for k in self.ordem if self.I[k]["tipo"] == "introducao"]

    def regulamento(self):
        return [k for k in self.ordem if k.startswith("R")]

    def dissertacoes(self):
        return [k for k in self.ordem if k.startswith("D")]

    def vocabulario(self, termo=None):
        vs = [k for k in self.ordem if self.I[k]["tipo"] == "verbete"]
        if termo:
            alvo = norm(termo)
            exatos = [k for k in vs if norm(self.I[k]["termo"]) == alvo]
            return exatos or [k for k in vs if alvo in norm(self.I[k]["termo"])]
        return vs

    def exemplo(self, nome):
        alvo = norm(nome)
        return [k for k in self.ordem if self.I[k].get("exemplo") and alvo in norm(self.I[k]["exemplo"])]

    def exemplos(self, capitulo=None):
        chave = self.capitulo(capitulo)["chave"] if capitulo else None
        res = {}
        for k in self.ordem:
            it = self.I[k]
            if it.get("exemplo") and (chave is None or it["capitulo_chave"] == chave):
                res.setdefault((it["capitulo_chave"], it["exemplo"]), []).append(k)
        return [{"capitulo": c, "exemplo": e, "itens": ids} for (c, e), ids in res.items()]

    def codigo_penal(self):
        return [k for k in self.ordem if self.I[k].get("capitulo_chave") == "1.7" and self.I[k]["tipo"] == "item"]

    def grupo(self, nome=""):
        alvo = norm(nome)
        res = {}
        for k in self.ordem:
            g = self.I[k].get("grupo")
            if g and alvo in norm(g):
                res.setdefault(g, []).append(k)
        return [{"grupo": g, "itens": ids} for g, ids in res.items()]

    # ---------- texto corrido (blocos dos agentes) ----------
    def texto_capitulo(self, ref, marcar_tokens=True):
        """Capítulo inteiro com [id], seções, assinaturas e notas, para agentes lerem."""
        c = self.capitulo(ref)
        if c["chave"] == "0.0":
            cab = "# P0C00 – Introdução"
        else:
            parte = self.P[c["parte"]]["titulo"] if c["parte"] in self.P else ""
            cab = f"# P{c['parte']}C{c['numero']:02d} – " + (f"{parte} – " if parte else "") + \
                  f"Capítulo {c['romano']} – {c['titulo']}"
        linhas = [cab, ""]
        secao = grupo = None
        for k in c["itens"]:
            it = self.I[k]
            if it.get("grupo") and it["grupo"] != grupo:
                grupo = it["grupo"]
                linhas += [f"## {grupo}", ""]
            if it.get("secao") and it["secao"] != secao:
                secao = it["secao"]
                linhas += [f"### {secao}", ""]
            if it.get("sessao") or it["tipo"] in ("dissertacao", "artigo") and it.get("item"):
                linhas += [f"#### {it['rotulo']}", ""]
            tok = f" (tokens: {tokens_aprox(it['texto'])})" if marcar_tokens else ""
            linhas.append(f"[{k}]{tok} " + it["texto"])
            if it.get("autor"):
                linhas.append(f"— {it['autor']}" + (f" ({it['local_data']})" if it.get("local_data") else ""))
            for n in it.get("notas", []):
                linhas.append(f"[{n}] Nota de rodapé: {self.N[n]['texto']}")
            linhas.append("")
        return "\n".join(linhas)

    def exportar_capitulos(self, pasta, marcar_tokens=True):
        pasta = Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        arquivos = []
        for c in self.C.values():
            f = pasta / f"P{c['parte']}C{c['numero']:02d}.txt"
            f.write_text(self.texto_capitulo(c["chave"], marcar_tokens), encoding="utf-8")
            arquivos.append(str(f))
        return arquivos

    # ---------- caminhos ----------
    def obter(self, caminho):
        """'itens/159/autor', 'notas/N4/texto', 'capitulos/4/titulo' (lista: índice a partir de 0)."""
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
        it = list(self.I.values())
        tipos = {}
        for x in it:
            tipos[x["tipo"]] = tipos.get(x["tipo"], 0) + 1
        return {
            "obra": self.titulo,
            "partes": len(self.P),
            "capitulos": len(self.db["capitulos"]),
            "unidades": len(self.I),
            "por_tipo": tipos,
            "secoes": len({(x.get("capitulo_chave"), x["secao"]) for x in it if x.get("secao")}),
            "comunicacoes_assinadas": sum(1 for x in it if x.get("autor")),
            "autores": len(self.autores()),
            "notas_de_rodape": len(self.N),
            "paginas": f"{min(x['pagina_inicio'] for x in it)}-{max(x['pagina_fim'] for x in it)}",
            "tokens_aprox": sum(tokens_aprox(x["texto"]) for x in it),
        }


# ───────────────────────────── saída ─────────────────────────────
def fmt_item(d, campos, formato):
    if formato == "ids":
        return d["id"]
    if formato == "curto":
        return f"{d['id']:>8} (p.{d['pagina']}) {d['texto'][:110].replace(chr(10), ' ')}"
    if formato == "json":
        return {c: d.get(c) for c in ["id"] + campos + ["citacao"]}
    cab = f"[{d['id']}]"
    if "pagina" in campos:
        cab += f"  p.{d['pagina']}"
    if "capitulo" in campos:
        cab += f"  {d['capitulo_rotulo']}"
    if "secao" in campos and d.get("secao"):
        cab += f"  § {d['secao']}"
    if "grupo" in campos and d.get("grupo"):
        cab += f"  ({d['grupo']})"
    linhas = [cab]
    if "texto" in campos:
        linhas.append(d["texto"])
    if "autor" in campos and d.get("autor"):
        linhas.append(f"— {d['autor']}" + (f" ({d['local_data']})" if d.get("local_data") and "local_data" in campos else ""))
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
    ap = argparse.ArgumentParser(prog="obras_db.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("livro", help="mediuns (lm) | ceu (ci) | genese (ag)")
    ap.add_argument("comando", nargs="?")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--campos", default=None, help="ex.: texto,autor ou 'todos'")
    ap.add_argument("--formato", default="texto", choices=["texto", "json", "ids", "curto"])
    ap.add_argument("--ids", action="store_true", help="atalho para --formato ids")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--capitulo")
    ap.add_argument("--secao")
    ap.add_argument("--modo", default="todas", choices=["todas", "qualquer", "frase", "regex"])
    ap.add_argument("--em", default="texto,secao")
    ap.add_argument("--autor")
    ap.add_argument("--antes", type=int, default=1)
    ap.add_argument("--depois", type=int, default=1)
    ap.add_argument("--expandir", action="store_true", help="mostrar o conteúdo dos itens encontrados")
    ap.add_argument("--sem-tokens", action="store_true", help="exportar: sem '(tokens: N)' após o id")
    ap.add_argument("--banco", default=None)
    return ap


def executar(ob, a):
    fmt = "ids" if a.ids else a.formato
    campos = TODOS_CAMPOS[1:] if a.campos == "todos" else (a.campos.split(",") if a.campos else CAMPOS_PADRAO)
    arg = " ".join(a.args)
    c = (a.comando or "").lower()

    def lista(ids, rotulo=None):
        if fmt == "ids":
            print(", ".join(ids))
        elif a.expandir or fmt == "json":
            imprimir_itens([ob._completo(ob.I[i]) for i in ids], fmt, campos)
        else:
            if rotulo:
                print(rotulo)
            imprimir_itens([ob._completo(ob.I[i]) for i in ids], "curto", campos)

    if c in ("item", "i"):
        imprimir_itens([ob.item(arg)], fmt, campos)
    elif c in ("itens", "lista"):
        its, nts = ob.separar_ids(arg)
        if its:
            imprimir_itens(ob.itens(its), fmt, campos)
        if nts:
            if its and fmt != "ids":
                print()
            imprimir(", ".join(nts) if fmt == "ids" else [ob.nota(n) for n in nts] if fmt == "json" else
                     "\n\n".join(f"[{n['id']}] p.{n['pagina']} (item {n['item']}) {n['texto']}" for n in map(ob.nota, nts)), fmt)
    elif c in ("capitulo", "cap"):
        cap = ob.capitulo(arg)
        if fmt == "ids" or a.expandir:
            lista(cap["itens"])
        else:
            imprimir({"chave": cap["chave"], "numero": cap["numero"], "romano": cap["romano"], "titulo": cap["titulo"],
                      "secoes": cap["secoes"], "itens": len(cap["itens"]),
                      "faixa": f"{cap['itens'][0]}–{cap['itens'][-1]}", "pagina": cap["pagina"]}, fmt)
    elif c == "capitulos":
        cs = ob.capitulos()
        imprimir(cs if fmt == "json" else "\n".join(
            f"{x['chave']:>5} {x['romano']:>7}  {x['titulo']:<58} {x['itens']:>3} unid.  ({x['faixa']}, p.{x['pagina']}, ~{x['tokens']} tokens)"
            for x in cs), fmt)
    elif c == "partes":
        imprimir(ob.partes(), "json" if fmt == "json" else fmt) if fmt == "json" else print(
            "\n".join(f"{p['numero']}  {p['titulo']}  (p.{p['pagina']}; caps. {', '.join(p['capitulos'])})" for p in ob.partes()))
    elif c == "secao":
        res = ob.secao(arg, a.capitulo)
        if fmt == "ids" or a.expandir:
            lista([i for r in res for i in r["itens"]])
        else:
            imprimir(res if fmt == "json" else "\n".join(
                f"cap. {r['capitulo']} § {r['secao']}: {', '.join(r['itens'])}" for r in res) or "(nada)", fmt)
    elif c == "secoes":
        res = ob.secoes(arg or a.capitulo)
        imprimir(res if fmt == "json" else "\n".join(f"{r['capitulo']:>5}  {r['itens']:<15} {r['secao']}" for r in res), fmt)
    elif c == "autor":
        ids = ob.autor(arg)
        lista(ids) if (fmt == "ids" or a.expandir) else print(
            "\n".join(f"{i:>8}  {ob.I[i]['autor']}" + (f" ({ob.I[i]['local_data']})" if ob.I[i]['local_data'] else "")
                      for i in ids) or "(nenhuma)")
    elif c == "autores":
        au = ob.autores()
        imprimir(au if fmt == "json" else "\n".join(f"{len(v):>3}  {k}: {', '.join(v)}" for k, v in au.items()), fmt)
    elif c == "local":
        lista(ob.local(arg), f"Local/data {arg}:")
    elif c in ("pagina", "paginas", "pg"):
        lista(ob.pagina(arg), f"Página {arg}:")
    elif c in ("buscar", "busca", "b"):
        res = ob.buscar(arg, modo=a.modo, em=a.em.split(","), capitulo=a.capitulo, secao=a.secao,
                        autor=a.autor, limite=a.limite)
        if fmt == "ids":
            print(", ".join(sorted((r["id"] for r in res), key=ob.pos.get)))
        elif a.expandir:
            imprimir_itens([ob._completo(ob.I[r["id"]]) for r in res], fmt, campos)
        elif fmt == "json":
            imprimir(res, fmt)
        else:
            print(f"{len(res)} resultado(s)")
            for r in res:
                d = ob._completo(ob.I[r["id"]])
                print(f"{r['id']:>8} [{r['pontos']:>2}] p.{d['pagina']}  {d['texto'][:100]}")
    elif c == "nota":
        n = ob.nota(arg)
        imprimir(n if fmt == "json" else f"[{n['id']}] p.{n['pagina']} (item {n['item']}) {n['texto']}", fmt)
    elif c == "notas":
        ns = ob.notas()
        imprimir(ns if fmt == "json" else ", ".join(n["id"] for n in ns) if fmt == "ids" else
                 "\n".join(f"[{n['id']}] item {n['item']}: {n['texto'][:110]}" for n in ns), fmt)
    elif c in ("vizinhos", "contexto"):
        imprimir_itens(ob.vizinhos(arg, a.antes, a.depois), fmt, campos)
    elif c in ("aleatorio", "aleatório"):
        imprimir_itens([ob.aleatorio()], fmt, campos)
    elif c == "ordenar":
        print(", ".join(ob.ordenar(arg)))
    elif c == "exportar":
        pasta = arg or f"capitulos_{ob.livro}"
        arqs = ob.exportar_capitulos(pasta, not a.sem_tokens)
        print(f"{len(arqs)} arquivos em {Path(pasta).resolve()}")
    elif c in ("caminho", "obter", "get"):
        imprimir(ob.obter(arg), fmt)
    elif c in ("chaves", "keys", "ls"):
        ch = ob.chaves(arg)
        imprimir(", ".join(map(str, ch)) if fmt != "json" else ch, fmt)
    elif c in ("stats", "estatisticas"):
        imprimir(ob.estatisticas(), fmt)
    elif c in ("introducao", "introdução"):
        lista(ob.introducao(), "Introdução:")
    elif c == "regulamento":
        lista(ob.regulamento(), "Regulamento da Sociedade Parisiense de Estudos Espíritas (cap. XXX):")
    elif c in ("dissertacoes", "dissertações"):
        lista(ob.dissertacoes(), "Dissertações espíritas (cap. XXXI):")
    elif c == "vocabulario":
        lista(ob.vocabulario(arg or None), "Vocabulário espírita (cap. XXXII):")
    elif c == "exemplo":
        lista(ob.exemplo(arg), f"Exemplo {arg}:")
    elif c == "exemplos":
        res = ob.exemplos(arg or a.capitulo)
        imprimir(res if fmt == "json" else "\n".join(
            f"{r['capitulo']:>5}  {r['exemplo']:<45} {', '.join(r['itens'])}" for r in res) or "(nenhum)", fmt)
    elif c in ("codigo_penal", "codigo"):
        lista(ob.codigo_penal(), "Código penal da vida futura (Primeira Parte, cap. VII):")
    elif c == "grupo":
        res = ob.grupo(arg)
        if fmt == "ids" or a.expandir:
            lista([i for r in res for i in r["itens"]])
        else:
            imprimir(res if fmt == "json" else "\n".join(f"{r['grupo']}: {', '.join(r['itens'])}" for r in res) or "(nada)", fmt)
    elif c in ("ajuda", "help", "?"):
        print(__doc__)
    else:
        raise ErroConsulta(f"Comando desconhecido: {a.comando!r}. Use: python obras_db.py {ob.livro} ajuda")


def interativo(ob, parser):
    p = LIVROS[ob.livro]["prompt"]
    print(f"{ob.titulo} — modo interativo. Ex.: item ... | buscar obsessão --ids | sair")
    while True:
        try:
            linha = input(f"{p}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if linha in ("sair", "exit", "quit"):
            break
        if not linha:
            continue
        try:
            executar(ob, parser.parse_args([ob.livro] + shlex.split(linha)))
        except SystemExit:
            pass
        except (ErroConsulta, KeyError, ValueError) as e:
            print("Erro:", e)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # acentos no terminal do Windows
    parser = construir_parser()
    a = parser.parse_args(argv)
    try:
        ob = Obra(a.livro, a.banco)
    except ErroConsulta as e:
        print("Erro:", e, file=sys.stderr)
        sys.exit(2)
    if not a.comando:
        interativo(ob, parser)
        return
    try:
        executar(ob, a)
    except (ErroConsulta, KeyError, ValueError) as e:
        print("Erro:", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
