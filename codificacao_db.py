#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codificacao_db — API de consulta local a "O Livro dos Espíritos" (Allan Kardec).

Tudo roda no seu computador, só com a biblioteca padrão do Python. Nenhuma
consulta passa por IA: uma IA (ou você) só gasta tokens com o que pedir para
ver. Use --ids para receber apenas números.

Banco: dados/livro_dos_espiritos.json (gerado por extrair_livro_dos_espiritos.py)

───────────────────────────────── LINHA DE COMANDO ─────────────────────────────────
  python codificacao_db.py pergunta 182.b            uma pergunta (aceita 182b, "182 b")
  python codificacao_db.py perguntas "180-182, 919a"  várias; faixas incluem subperguntas
  python codificacao_db.py capitulo P3C12            capítulo (aceita 3.12, "III XII", "3 12")
  python codificacao_db.py parte 3                   parte com seus capítulos
  python codificacao_db.py secao "si mesmo"          seção (busca pelo nome)
  python codificacao_db.py pagina 120                página impressa (ou faixa "120-125")
  python codificacao_db.py tema Moral                temas (tags) dos capítulos
  python codificacao_db.py temas                     lista de temas e contagem
  python codificacao_db.py indice vocação            Índice geral do livro (assunto → perguntas)
  python codificacao_db.py buscar "livre-arbítrio"   busca no texto (sem acento/maiúscula)
  python codificacao_db.py caminho perguntas/182/resposta   acesso direto por caminho
  python codificacao_db.py chaves capitulos          lista as chaves de um caminho
  python codificacao_db.py texto introd.VI           Introdução, Conclusão, Prolegômenos
  python codificacao_db.py nota 4                    nota de rodapé
  python codificacao_db.py kardec "900-919"          perguntas com comentário de Kardec (--expandir mostra)
  python codificacao_db.py notas_kardec              notas de rodapé escritas por Kardec
  python codificacao_db.py anotacoes "K919.a, N4"    anotações por identificador (K=comentário, N=nota)
  python codificacao_db.py perguntas "928, K919.a, N4"   mistura perguntas e anotações
  python codificacao_db.py exportar capitulos        1 .txt por capítulo com [id], [Kid], [Nn]
  python codificacao_db.py ordenar "919.a,N4,K919.a,1,1"  junta/ordena listas (K após a pergunta)
  python codificacao_db.py remissoes 1000            perguntas para as quais o texto remete
  python codificacao_db.py citada_por 919            quem remete a esta pergunta
  python codificacao_db.py assinadas "São Luís"      respostas assinadas por um Espírito
  python codificacao_db.py vizinhas 919 --antes 2 --depois 2
  python codificacao_db.py aleatoria
  python codificacao_db.py stats
  python codificacao_db.py                           modo interativo (digite os comandos)

Opções comuns:
  --campos pergunta,resposta,assinatura,comentario,notas,remissoes,pagina,capitulo,secao,indice,temas
           (padrão: pergunta,resposta,assinatura,comentario,notas,remissoes; "todos" = tudo)
  --formato texto|json|ids|curto      (ids = só números; curto = 1 linha por item)
  --limite N        --parte N         --capitulo P2C04     --secao "..."
  --modo todas|qualquer|frase|regex   (buscar)   --em pergunta,resposta,comentario
  --sem-subs        (faixas sem subperguntas)

───────────────────────────────── EM PYTHON ─────────────────────────────────
  from codificacao_db import LivroDosEspiritos
  le = LivroDosEspiritos()
  le.pergunta("182b")                 -> dict
  le.perguntas("180-182, 919a")       -> [dict, ...]
  le.capitulo("3.12")["perguntas"]    -> ids
  le.pagina(120)["texto"]
  le.tema("Livre-arbítrio")           -> {"capitulos": [...], "perguntas": [...]}
  le.indice("vocação")                -> [{"termo","sub","refs"}...]
  le.buscar("orgulho egoísmo", modo="todas", parte=3)
  le.obter("perguntas/919.a/resposta")
  le.kardec("900-919")                -> ids com comentário de Kardec
  le.anotacao("K919.a"); le.anotacao("N4"); le.ids_anotacoes(919)
  le.exportar_capitulos("capitulos")
  le.notas_kardec(); le.remissoes(1000); le.citada_por(919); le.assinadas("Agostinho")
  le["182.b"]                         -> atalho para pergunta
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
ARQUIVO_PADRAO = PASTA / "dados" / "livro_dos_espiritos.json"

CAMPOS_PADRAO = ["pergunta", "texto", "resposta", "assinatura", "comentario", "referencia", "nota_editora", "notas", "remissoes"]
TODOS_CAMPOS = ["id", "tipo", "pergunta", "texto", "resposta", "assinatura", "comentario", "referencia", "nota_editora", "notas", "remissoes",
                "pagina", "parte", "capitulo", "capitulo_titulo", "secao", "temas", "indice",
                "resposta_sem_aspas"]


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
        if i + 1 < len(s) and v[s[i + 1]] > v[c]:
            tot -= v[c]
        else:
            tot += v[c]
    return tot


def _num_ou_romano(s):
    s = s.strip().strip(".")
    if s.isdigit():
        return int(s)
    if re.fullmatch(r"[ivxlIVXL]+", s):
        return romano_para_int(s)
    ordinais = {"primeira": 1, "segunda": 2, "terceira": 3, "quarta": 4}
    return ordinais.get(norm(s))


class ErroConsulta(Exception):
    pass


# ───────────────────────────── banco ─────────────────────────────
class LivroDosEspiritos:
    def __init__(self, arquivo=ARQUIVO_PADRAO):
        arquivo = Path(arquivo)
        if not arquivo.exists():
            raise FileNotFoundError(
                f"Banco não encontrado: {arquivo}\n"
                "Gere com: python extrair_livro_dos_espiritos.py Livro-dos-Espiritos.pdf")
        self.db = json.loads(arquivo.read_text(encoding="utf-8"))
        self.P = self.db["perguntas"]
        self.C = self.db["capitulos"]
        self.ordem = list(self.P)                       # ordem do livro
        self.pos = {k: i for i, k in enumerate(self.ordem)}
        self._busca = {k: {c: norm(v.get(c) or "") for c in ("pergunta", "texto", "resposta", "comentario")}
                       for k, v in self.P.items()}
        self._idx_termos = [(norm(e["termo"]), norm(e.get("sub") or ""), e) for e in self.db["indice_geral"]]

    # ---------- identificadores ----------
    def normalizar_id(self, ref):
        """'182', 182, '182b', '182.b', '182 b', '182-b' -> '182.b'"""
        s = str(ref).strip().lower()
        m = re.fullmatch(r"(\d{1,4})\s*[.\-\s]?\s*([a-z])?\)?", s)
        if not m:
            raise ErroConsulta(f"Identificador inválido: {ref!r} (use 182 ou 182.b)")
        return m.group(1) + (f".{m.group(2)}" if m.group(2) else "")

    def subperguntas(self, numero):
        n = str(int(str(numero).split(".")[0]))
        return [k for k in self.ordem if k == n or k.startswith(n + ".")]

    def expandir(self, spec, com_subs=True):
        """'1-5, 182.b, 919a, 1000-1003' -> lista de ids existentes, na ordem do livro."""
        ids = []
        partes = spec if isinstance(spec, (list, tuple)) else re.split(r"[,;|\s]+(?![a-z]\b)", str(spec))
        for parte in partes:
            parte = str(parte).strip()
            if not parte:
                continue
            m = re.fullmatch(r"(\d{1,4})\s*(?:-|–|a|até)\s*(\d{1,4})", parte)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                for n in range(min(a, b), max(a, b) + 1):
                    ids += self.subperguntas(n) if com_subs else ([str(n)] if str(n) in self.P else [])
                continue
            i = self.normalizar_id(parte)
            if i not in self.P:
                raise ErroConsulta(f"Pergunta {i} não existe")
            ids.append(i)
        vistos = set()
        return [i for i in sorted(ids, key=self.pos.get) if not (i in vistos or vistos.add(i))]

    # ---------- perguntas ----------
    def pergunta(self, ref):
        i = self.normalizar_id(ref)
        if i not in self.P:
            raise ErroConsulta(f"Pergunta {i} não existe")
        return self._completa(self.P[i])

    def perguntas(self, spec, com_subs=True):
        return [self._completa(self.P[i]) for i in self.expandir(spec, com_subs)]

    def __getitem__(self, ref):
        return self.pergunta(ref)

    def _completa(self, p):
        d = dict(p)
        cap = self.C[p["capitulo"]]
        d["capitulo_titulo"] = f"Parte {self.db['partes'][p['parte'] - 1]['ordinal']}, Cap. {cap['romano']} – {cap['titulo']}"
        d["pagina"] = p["pagina_inicio"] if p["pagina_inicio"] == p["pagina_fim"] else f"{p['pagina_inicio']}-{p['pagina_fim']}"
        d["notas"] = [f"[{n}] {self.db['notas_rodape'][n]['texto']}" for n in p.get("notas", [])]
        return d

    def vizinhas(self, ref, antes=1, depois=1):
        i = self.pos[self.normalizar_id(ref)]
        return [self._completa(self.P[k]) for k in self.ordem[max(0, i - antes): i + depois + 1]]

    def aleatoria(self):
        return self._completa(self.P[random.choice(self.ordem)])

    # ---------- estrutura ----------
    def capitulo(self, ref):
        """'P3C12', '3.12', '3 12', 'III.XII', 'III XII', (3, 12)"""
        if isinstance(ref, (tuple, list)):
            p, c = ref
        else:
            s = str(ref).strip()
            if s.upper() in self.C:
                return self._cap(self.C[s.upper()])
            m = re.fullmatch(r"(?i)p?\s*([ivxl\d]+|primeira|segunda|terceira|quarta)\s*[.,:/\s c]\s*(?:cap\w*\.?\s*)?([ivxl\d]+)", s)
            if not m:
                achados = [c for c in self.C.values() if norm(s) in norm(c["titulo"])]
                if len(achados) == 1:
                    return self._cap(achados[0])
                raise ErroConsulta(f"Capítulo não encontrado: {ref!r}. Use P3C12 ou 3.12"
                                   + (f". Candidatos: {[c['id'] for c in achados]}" if achados else ""))
            p, c = m.group(1), m.group(2)
        cid = f"P{_num_ou_romano(str(p))}C{_num_ou_romano(str(c)):02d}"
        if cid not in self.C:
            raise ErroConsulta(f"Capítulo {cid} não existe")
        return self._cap(self.C[cid])

    def _cap(self, c):
        d = dict(c)
        d["parte_titulo"] = self.db["partes"][c["parte"] - 1]["titulo"]
        d["faixa"] = f"{c['perguntas'][0]}–{c['perguntas'][-1]}" if c["perguntas"] else ""
        return d

    def capitulos(self):
        return [self._cap(c) for c in self.C.values()]

    def parte(self, n):
        n = _num_ou_romano(str(n))
        if not n or not 1 <= n <= len(self.db["partes"]):
            raise ErroConsulta("Parte deve ser 1 a 4")
        d = dict(self.db["partes"][n - 1])
        d["capitulos"] = [self._cap(self.C[c]) for c in d["capitulos"]]
        return d

    def secao(self, nome, capitulo=None):
        """Perguntas de uma seção (busca parcial pelo nome, sem acento)."""
        alvo = norm(nome)
        grupos = {}
        for k in self.ordem:
            p = self.P[k]
            if p["secao"] and alvo in norm(p["secao"]) and (capitulo is None or p["capitulo"] == self.capitulo(capitulo)["id"]):
                grupos.setdefault((p["capitulo"], p["secao"]), []).append(k)
        return [{"capitulo": c, "secao": s, "perguntas": ids} for (c, s), ids in grupos.items()]

    def secoes(self):
        out, visto = [], set()
        for k in self.ordem:
            p = self.P[k]
            chave = (p["capitulo"], p["secao"])
            if p["secao"] and chave not in visto:
                visto.add(chave)
                out.append({"capitulo": p["capitulo"], "secao": p["secao"]})
        return out

    # ---------- páginas ----------
    def pagina(self, n):
        d = self.db["paginas"].get(str(int(n)))
        if d is None:
            raise ErroConsulta(f"Página {n} não existe (há {min(map(int, self.db['paginas']))}–{max(map(int, self.db['paginas']))})")
        return d

    def paginas(self, spec):
        m = re.fullmatch(r"\s*(\d+)\s*(?:-|–)\s*(\d+)\s*", str(spec))
        nums = range(int(m.group(1)), int(m.group(2)) + 1) if m else [int(x) for x in re.split(r"[,\s]+", str(spec)) if x]
        return [self.db["paginas"][str(n)] for n in nums if str(n) in self.db["paginas"]]

    def pagina_da_pergunta(self, ref):
        p = self.P[self.normalizar_id(ref)]
        return list(range(p["pagina_inicio"], p["pagina_fim"] + 1))

    # ---------- temas e índice ----------
    def temas(self):
        cont = {}
        for c in self.C.values():
            for t in c["temas"]:
                cont.setdefault(t, []).append(c["id"])
        return dict(sorted(cont.items(), key=lambda kv: (-len(kv[1]), norm(kv[0]))))

    def tema(self, nome, exato=False):
        """Capítulos e perguntas com um tema (tag). Busca parcial sem acento, a menos que exato=True."""
        alvo = norm(nome)
        temas = [t for t in self.temas() if (norm(t) == alvo if exato else alvo in norm(t))]
        if not temas:
            raise ErroConsulta(f"Tema não encontrado: {nome!r}. Veja: python codificacao_db.py temas")
        caps = [c["id"] for c in self.C.values() if any(t in c["temas"] for t in temas)]
        ids = [k for k in self.ordem if self.P[k]["capitulo"] in caps]
        return {"temas": temas, "capitulos": caps, "perguntas": ids}

    def indice(self, termo, sub=None):
        """Índice geral do livro. Procura o termo (e opcionalmente o subtermo) sem acento."""
        a, b = norm(termo), norm(sub) if sub else None
        ra = re.compile(rf"\b{re.escape(a)}")
        rb = re.compile(rf"\b{re.escape(b)}") if b else None
        return [e for t, s, e in self._idx_termos
                if (ra.search(t) or (not b and ra.search(s))) and (rb is None or rb.search(s))]

    def indice_ids(self, termo, sub=None):
        ids = []
        for e in self.indice(termo, sub):
            ids += [r for r in e["refs"] if r in self.P]
        vistos = set()
        return [i for i in sorted(ids, key=self.pos.get) if not (i in vistos or vistos.add(i))]

    def termos_indice(self, prefixo=""):
        p = norm(prefixo)
        out = []
        for t, _, e in self._idx_termos:
            if t.startswith(p) and e["termo"] not in out:
                out.append(e["termo"])
        return out

    # ---------- busca ----------
    def buscar(self, consulta, modo="todas", em=("pergunta", "texto", "resposta", "comentario"),
               parte=None, capitulo=None, secao=None, limite=None):
        """modo: 'todas' (todas as palavras), 'qualquer', 'frase' (trecho exato) ou 'regex'.
        Sem acento e sem maiúsculas (exceto regex, que roda no texto normalizado)."""
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
                if modo == "todas":
                    return sum(c) if all(c) else 0
                return sum(c)
        cap_id = self.capitulo(capitulo)["id"] if capitulo else None
        resultados = []
        for k in self.ordem:
            p = self.P[k]
            if parte and p["parte"] != int(parte):
                continue
            if cap_id and p["capitulo"] != cap_id:
                continue
            if secao and norm(secao) not in norm(p["secao"] or ""):
                continue
            pontos, onde = 0, []
            for campo in em:
                n = teste(self._busca[k][campo])
                if n:
                    pontos += n * (3 if campo == "pergunta" else 2 if campo == "resposta" else 1)
                    onde.append(campo)
            if pontos:
                resultados.append({"id": k, "pontos": pontos, "campos": onde})
        resultados.sort(key=lambda r: (-r["pontos"], self.pos[r["id"]]))
        return resultados[:limite] if limite else resultados

    def buscar_ids(self, consulta, ordem_do_livro=True, **kw):
        ids = [r["id"] for r in self.buscar(consulta, **kw)]
        return sorted(ids, key=self.pos.get) if ordem_do_livro else ids

    def buscar_paginas(self, consulta):
        palavras = norm(consulta).split()
        return [int(n) for n, p in self.db["paginas"].items()
                if all(w in norm(p["texto"]) for w in palavras)]

    # ---------- anotações de Kardec ----------
    def kardec(self, spec=None):
        """Ids das perguntas que têm comentário de Kardec (opcional: só dentro de uma lista/faixa)."""
        base = self.expandir(spec) if spec else self.ordem
        return [k for k in base if self.P[k]["comentario"]]

    def notas_kardec(self):
        return [n for n in self.db["notas_rodape"].values() if n.get("autor") == "Allan Kardec"]

    def remissoes(self, ref):
        """Perguntas para as quais Kardec/os Espíritos remetem, ex.: (720 e 721)."""
        p = self.P[self.normalizar_id(ref)]
        ids = []
        for r in p.get("remissoes", []):
            try:
                ids += self.expandir(r)
            except ErroConsulta:
                pass
        return ids

    def citada_por(self, ref):
        """Perguntas que remetem a esta."""
        alvo = self.normalizar_id(ref)
        return [k for k, p in self.P.items() if p.get("remissoes") and alvo in self.remissoes(k)]

    def assinadas(self, nome=""):
        return [k for k in self.ordem if self.P[k].get("assinatura") and norm(nome) in norm(self.P[k]["assinatura"])]

    def anotacao(self, ref):
        """'K919.a' = comentário de Kardec da pergunta 919.a;  'N4' = nota de rodapé 4."""
        r = str(ref).strip()
        if r[:2].upper() == "KE":
            t = self.db.get("textos_kardec", {}).get("Ke" + r[2:].strip())
            if not t:
                raise ErroConsulta(f"Texto {r} não existe")
            return {"id": t["id"], "tipo": "texto_kardec", "capitulo": t["capitulo"], "secao": t["secao"],
                    "antes_de": t["antes_de"], "pagina": t["pagina_inicio"], "texto": t["texto"]}
        if r[:1].upper() == "K":
            i = self.normalizar_id(r[1:])
            p = self.P.get(i)
            if not p or not p["comentario"]:
                raise ErroConsulta(f"{r}: a pergunta {i} não tem comentário de Kardec")
            return {"id": f"K{i}", "tipo": "comentario_kardec", "pergunta": i,
                    "pagina": p["pagina_inicio"], "texto": p["comentario"]}
        if r[:1].upper() == "N":
            n = self.db["notas_rodape"].get(str(int(r[1:])))
            if not n:
                raise ErroConsulta(f"Nota {r} não existe")
            return {"id": f"N{n['numero']}", "tipo": "nota_rodape", "autor": n["autor"],
                    "perguntas": n["perguntas"], "pagina": n["pagina"], "texto": n["texto"]}
        raise ErroConsulta(f"Identificador de anotação inválido: {ref!r} (use K919.a ou N4)")

    def ids_anotacoes(self, pergunta):
        """Identificadores de anotações ligadas a uma pergunta: ['K919.a', 'N24']."""
        p = self.P[self.normalizar_id(pergunta)]
        return ([f"K{p['id']}"] if p["comentario"] else []) + [f"N{n}" for n in p.get("notas", [])]

    def separar_ids(self, spec):
        """'180, 919a, K919.a, N4' -> (ids de perguntas, ids de anotações)"""
        itens = [x.strip() for x in re.split(r"[,;|]+", str(spec)) if x.strip()]
        anot = [x.upper()[0] + x[1:] for x in itens if x[:1].upper() in "KN"]
        perg = [x for x in itens if x[:1].upper() not in "KN"]
        return (self.expandir(perg) if perg else []), anot

    def ordenar(self, spec):
        """Junta, normaliza, remove duplicatas e ordena na ordem do livro.
        Comentário K logo após sua pergunta; nota N após a 1ª pergunta ligada a ela (ou pela página)."""
        chaves = {}
        for x in [x.strip() for x in re.split(r"[,;|\s]+", str(spec)) if x.strip()]:
            if x.upper() == "NENHUMA":
                continue
            t = x[:1].upper()
            if x[:2].upper() == "KE":
                a = self.anotacao(x)
                chaves[a["id"]] = (self.pos[a["antes_de"]], -1) if a["antes_de"] else (len(self.ordem), -1)
            elif t == "K":
                a = self.anotacao(x)
                chaves[a["id"]] = (self.pos[a["pergunta"]], 1)
            elif t == "N":
                a = self.anotacao(x)
                if a["perguntas"]:
                    chaves[a["id"]] = (self.pos[a["perguntas"][0]], 2)
                else:
                    antes = [k for k in self.ordem if self.P[k]["pagina_inicio"] <= a["pagina"]]
                    chaves[a["id"]] = (self.pos[antes[-1]] if antes else -1, 2)
            else:
                for i in self.expandir(x):
                    chaves[i] = (self.pos[i], 0)
        return sorted(chaves, key=chaves.get)

    def exportar_capitulos(self, pasta):
        """Grava um .txt por capítulo com identificadores explícitos, para agentes lerem."""
        pasta = Path(pasta)
        pasta.mkdir(parents=True, exist_ok=True)
        for c in self.C.values():
            linhas = [f"# {c['id']} – Parte {self.db['partes'][c['parte'] - 1]['ordinal']}, "
                      f"Cap. {c['romano']} – {c['titulo']}", ""]
            ke = {}
            for t in self.db.get("textos_kardec", {}).values():
                ke.setdefault(t["antes_de"], []).append(t)
            for i in c["perguntas"]:
                p = self.P[i]
                for t in ke.get(i, []):
                    linhas += [f"[{t['id']}] Kardec (texto sem número): {t['texto']}", ""]
                if p.get("tipo") == "kardec":
                    linhas += [f"[{i}] Kardec (texto numerado): {p['texto']}", ""]
                    continue
                linhas.append(f"[{i}] P: {p['pergunta']}")
                if p["resposta"]:
                    linhas.append(f"R: {p['resposta']}" + (f" — {p['assinatura']}" if p.get("assinatura") else ""))
                if p["comentario"]:
                    linhas.append(f"[K{i}] Kardec: {p['comentario']}")
                for n in p.get("notas", []):
                    linhas.append(f"[N{n}] Nota: {self.db['notas_rodape'][n]['texto']}")
                linhas.append("")
            (pasta / f"{c['id']}.txt").write_text("\n".join(linhas), encoding="utf-8")
        return sorted(str(x) for x in pasta.glob("P*C*.txt"))

    # ---------- textos, notas, caminhos ----------
    def texto(self, chave):
        """'introd.VI', 'concl.III', 'prolegomenos', 'nota_explicativa'"""
        k = chave.strip()
        m = re.fullmatch(r"(?i)(introd|introdução|introducao|concl|conclusão|conclusao)\.?\s*([ivxl]+|\d+)", k)
        if m:
            pre = "introd" if norm(m.group(1)).startswith("introd") else "concl"
            n = _num_ou_romano(m.group(2))
            k = f"{pre}.{['', 'I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV','XVI','XVII'][n]}"
        if k not in self.db["textos"]:
            raise ErroConsulta(f"Texto não encontrado: {chave!r}. Há: {', '.join(self.db['textos'])}")
        return self.db["textos"][k]

    def nota(self, n):
        return self.db["notas_rodape"][str(int(n))]

    def obter(self, caminho):
        """Acesso por caminho: 'perguntas/182.b/resposta', 'capitulos/P3C12/secoes/0',
        'paginas/120/texto', 'partes/2/titulo' (lista: índice a partir de 0)."""
        atual = self.db
        for parte in [x for x in caminho.strip("/").split("/") if x]:
            if isinstance(atual, list):
                atual = atual[int(parte)]
            elif isinstance(atual, dict):
                if parte not in atual and atual is self.P:
                    parte = self.normalizar_id(parte)
                if parte not in atual and atual is self.C:
                    parte = self.capitulo(parte)["id"]
                if parte not in atual:
                    raise ErroConsulta(f"Chave {parte!r} não existe em {caminho!r}")
                atual = atual[parte]
            else:
                raise ErroConsulta(f"{caminho!r}: não dá para entrar em um valor simples")
        return atual

    def chaves(self, caminho=""):
        v = self.obter(caminho) if caminho else self.db
        if isinstance(v, dict):
            return list(v)
        if isinstance(v, list):
            return list(range(len(v)))
        return []

    def estatisticas(self):
        P = self.P.values()
        return {
            "obra": self.db["meta"]["obra"],
            "perguntas_numeradas": len({p["numero"] for p in P}),
            "subperguntas": sum(1 for p in P if p["letra"]),
            "itens": len(self.P),
            "partes": len(self.db["partes"]),
            "capitulos": len(self.C),
            "secoes": len(self.secoes()),
            "paginas": len(self.db["paginas"]),
            "temas": len(self.temas()),
            "entradas_indice_geral": len(self.db["indice_geral"]),
            "comentarios_kardec": sum(1 for p in P if p["comentario"]),
            "itens_texto_kardec": [p["id"] for p in P if p.get("tipo") == "kardec"],
            "textos_kardec_sem_numero": len(self.db.get("textos_kardec", {})),
            "textos": list(self.db["textos"]),
        }


# ───────────────────────────── saída ─────────────────────────────
def fmt_pergunta(p, campos, formato):
    if formato == "ids":
        return p["id"]
    if formato == "curto":
        return f"{p['id']} (p.{p['pagina']}) {(p['pergunta'] or p.get('texto', ''))[:110]}"
    if formato == "json":
        return {c: p.get(c) for c in ["id"] + campos}
    linhas = [f"[{p['id']}]" + (f"  p.{p['pagina']}" if "pagina" in campos else "")
              + (f"  {p['capitulo_titulo']}" if "capitulo" in campos else "")
              + (f"  § {p['secao']}" if "secao" in campos and p.get("secao") else "")]
    rot = {"pergunta": "P", "resposta": "R", "assinatura": "Assinado", "comentario": "Kardec",
           "notas": "Nota", "remissoes": "Ver", "referencia": "Referência", "nota_editora": "N.E.", "texto": "Kardec (texto)"}
    for c in campos:
        if c in ("pagina", "capitulo", "secao", "id"):
            continue
        v = p.get(c)
        if v in (None, "", []):
            continue
        if c == "notas":
            linhas += [f"Nota [N{x[1:].split(']')[0]}]{x.split(']', 1)[1]}" for x in v]
            continue
        if c == "comentario":
            linhas.append(f"Kardec [K{p['id']}]: {v}")
            continue
        if isinstance(v, list):
            v = "; ".join(map(str, v))
        linhas.append(f"{rot.get(c, c)}: {v}")
    return "\n".join(linhas)


def imprimir(obj, formato, campos=None):
    campos = campos or CAMPOS_PADRAO
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "pergunta" in obj[0] and "resposta" in obj[0]:
        if formato == "ids":
            print(", ".join(p["id"] for p in obj))
        elif formato == "json":
            print(json.dumps([fmt_pergunta(p, campos, "json") for p in obj], ensure_ascii=False, indent=1))
        else:
            print(("\n" if formato == "curto" else "\n\n").join(fmt_pergunta(p, campos, formato) for p in obj))
        return
    if isinstance(obj, dict) and "pergunta" in obj and "resposta" in obj:
        out = fmt_pergunta(obj, campos, formato)
        print(json.dumps(out, ensure_ascii=False, indent=1) if formato == "json" else out)
        return
    if formato == "ids" and isinstance(obj, dict) and "perguntas" in obj:
        print(", ".join(obj["perguntas"]))
        return
    if formato == "ids" and isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        print(", ".join(obj))
        return
    if isinstance(obj, str) and formato != "json":
        print(obj)
        return
    print(json.dumps(obj, ensure_ascii=False, indent=1))


# ───────────────────────────── CLI ─────────────────────────────
def construir_parser():
    ap = argparse.ArgumentParser(prog="codificacao_db.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", nargs="?")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--campos", default=None, help="ex.: pergunta,resposta ou 'todos'")
    ap.add_argument("--formato", default="texto", choices=["texto", "json", "ids", "curto"])
    ap.add_argument("--ids", action="store_true", help="atalho para --formato ids")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--parte", type=int)
    ap.add_argument("--capitulo")
    ap.add_argument("--secao")
    ap.add_argument("--modo", default="todas", choices=["todas", "qualquer", "frase", "regex"])
    ap.add_argument("--em", default="pergunta,texto,resposta,comentario")
    ap.add_argument("--sub")
    ap.add_argument("--sem-subs", action="store_true")
    ap.add_argument("--antes", type=int, default=1)
    ap.add_argument("--depois", type=int, default=1)
    ap.add_argument("--exato", action="store_true")
    ap.add_argument("--expandir", action="store_true", help="mostrar o conteúdo das perguntas encontradas")
    ap.add_argument("--banco", default=str(ARQUIVO_PADRAO))
    return ap


def executar(le, a):
    fmt = "ids" if a.ids else a.formato
    campos = TODOS_CAMPOS[1:] if a.campos == "todos" else (a.campos.split(",") if a.campos else CAMPOS_PADRAO)
    arg = " ".join(a.args)
    c = (a.comando or "").lower()

    def lista_perguntas(ids):
        if fmt == "ids" or not a.expandir:
            if fmt in ("ids",):
                print(", ".join(ids))
            else:
                imprimir([le.pergunta(i) for i in ids], "curto" if fmt == "texto" else fmt, campos)
        else:
            imprimir([le.pergunta(i) for i in ids], fmt, campos)

    if c in ("pergunta", "p", "q"):
        imprimir(le.pergunta(arg), fmt, campos)
    elif c in ("perguntas", "ps", "lista"):
        perg, anot = le.separar_ids(arg)
        if perg:
            imprimir([le.pergunta(i) for i in perg], fmt, campos)
        if anot:
            if perg and fmt != "ids":
                print()
            imprimir([le.anotacao(x) for x in anot] if fmt == "json" else
                     ", ".join(anot) if fmt == "ids" else
                     "\n\n".join(f"[{x['id']}] p.{x['pagina']} {x['texto']}" for x in map(le.anotacao, anot)), fmt)
    elif c in ("anotacao", "anotacoes"):
        res = [le.anotacao(x) for x in re.split(r"[,;|\s]+", arg) if x]
        imprimir(res if fmt == "json" else "\n\n".join(f"[{x['id']}] p.{x['pagina']} {x['texto']}" for x in res), fmt)
    elif c == "ordenar":
        print(", ".join(le.ordenar(arg)))
    elif c == "exportar":
        arquivos = le.exportar_capitulos(arg or "capitulos")
        print(f"{len(arquivos)} arquivos em {Path(arg or 'capitulos').resolve()}")
    elif c in ("subs", "subperguntas"):
        imprimir(le.perguntas(le.subperguntas(arg)), fmt, campos)
    elif c in ("vizinhas", "contexto"):
        imprimir(le.vizinhas(arg, a.antes, a.depois), fmt, campos)
    elif c == "aleatoria":
        imprimir(le.aleatoria(), fmt, campos)
    elif c in ("capitulo", "cap"):
        cap = le.capitulo(arg)
        if fmt == "ids":
            print(", ".join(cap["perguntas"]))
        elif a.expandir:
            imprimir(le.perguntas(cap["perguntas"]), fmt, campos)
        else:
            resumo = {k: cap[k] for k in ("id", "parte_titulo", "romano", "titulo", "secoes", "temas",
                                          "pagina_inicio", "pagina_fim", "faixa")}
            resumo["total_perguntas"] = len(cap["perguntas"])
            imprimir(resumo, fmt)
    elif c == "capitulos":
        imprimir([{"id": x["id"], "titulo": x["titulo"], "faixa": x["faixa"],
                   "paginas": f"{x['pagina_inicio']}-{x['pagina_fim']}"} for x in le.capitulos()], fmt)
    elif c == "parte":
        p = le.parte(arg)
        imprimir({"numero": p["numero"], "titulo": p["titulo"],
                  "capitulos": [f"{x['id']} {x['titulo']} ({x['faixa']})" for x in p["capitulos"]]}, fmt)
    elif c == "secao":
        res = le.secao(arg, a.capitulo)
        if a.expandir:
            imprimir(le.perguntas([i for r in res for i in r["perguntas"]]), fmt, campos)
        elif fmt == "ids":
            print(", ".join(i for r in res for i in r["perguntas"]))
        else:
            imprimir(res, fmt)
    elif c == "secoes":
        imprimir(le.secoes(), fmt)
    elif c in ("pagina", "paginas", "pg"):
        pgs = le.paginas(arg)
        if fmt == "ids":
            print(", ".join(dict.fromkeys(i for p in pgs for i in p["perguntas"])))
        else:
            for p in pgs:
                if fmt == "json":
                    imprimir(p, "json")
                else:
                    print(f"── página {p['pagina']} ({p['regiao']}{', ' + p['cabecalho'] if p['cabecalho'] else ''}) ──")
                    print(p["texto"])
                    for k, v in p["notas_rodape"].items():
                        print(f"  [nota {k}] {v}")
                    print()
    elif c == "temas":
        t = le.temas()
        imprimir(t if fmt == "json" else "\n".join(f"{k} ({len(v)}): {', '.join(v)}" for k, v in t.items()), fmt)
    elif c == "tema":
        r = le.tema(arg, a.exato)
        if a.expandir:
            imprimir(le.perguntas(r["perguntas"]), fmt, campos)
        elif fmt == "ids":
            print(", ".join(r["perguntas"]))
        else:
            imprimir({"temas": r["temas"], "capitulos": r["capitulos"], "total_perguntas": len(r["perguntas"])}, fmt)
    elif c in ("indice", "índice"):
        if not arg:
            imprimir(le.termos_indice(), fmt)
            return
        if fmt == "ids" or a.expandir:
            ids = le.indice_ids(arg, a.sub)
            if fmt == "ids":
                print(", ".join(ids))
            else:
                imprimir(le.perguntas(ids), fmt, campos)
        else:
            res = le.indice(arg, a.sub)
            imprimir(res if fmt == "json" else "\n".join(
                f"{e['termo']}{': ' + e['sub'] if e['sub'] else ''} – {', '.join(e['refs']) or 'ver ' + e.get('ver', '')}"
                for e in res) or "(nada)", fmt)
    elif c in ("buscar", "busca", "b"):
        res = le.buscar(arg, modo=a.modo, em=a.em.split(","), parte=a.parte,
                        capitulo=a.capitulo, secao=a.secao, limite=a.limite)
        if fmt == "ids":
            print(", ".join(sorted((r["id"] for r in res), key=le.pos.get)))
        elif a.expandir:
            imprimir([le.pergunta(r["id"]) for r in res], fmt, campos)
        elif fmt == "json":
            imprimir(res, fmt)
        else:
            print(f"{len(res)} resultado(s)")
            for r in res:
                p = le.pergunta(r["id"])
                print(f"{r['id']:>7} [{r['pontos']:>2}] p.{p['pagina']}  {p['pergunta'][:100]}")
    elif c == "buscar_paginas":
        imprimir(", ".join(map(str, le.buscar_paginas(arg))), fmt)
    elif c == "kardec":
        ids = le.kardec(arg or None)
        if fmt == "ids" or not a.expandir:
            print(f"{len(ids)} pergunta(s) com comentário de Kardec:" if fmt != "ids" else "", end="\n" if fmt != "ids" else "")
            print(", ".join(ids))
        else:
            imprimir(le.perguntas(ids), fmt, a.campos.split(",") if a.campos else ["pergunta", "comentario", "notas"])
    elif c in ("notas_kardec", "notas"):
        imprimir(le.notas_kardec(), fmt)
    elif c in ("remissoes", "ver"):
        ids = le.remissoes(arg)
        imprimir(le.perguntas(ids) if a.expandir else ", ".join(ids) or "(nenhuma)", fmt, campos)
    elif c == "citada_por":
        print(", ".join(le.citada_por(arg)) or "(nenhuma)")
    elif c in ("assinadas", "assinatura"):
        ids = le.assinadas(arg)
        imprimir(le.perguntas(ids) if a.expandir else ", ".join(f"{i} ({le.P[i]['assinatura']})" for i in ids), fmt, campos)
    elif c in ("caminho", "obter", "get"):
        imprimir(le.obter(arg), fmt)
    elif c in ("chaves", "keys", "ls"):
        ch = le.chaves(arg)
        imprimir(", ".join(map(str, ch)) if fmt != "json" else ch, fmt)
    elif c == "texto":
        t = le.texto(arg)
        imprimir(t if fmt == "json" else f"── {t['obra_parte']} {t['item'] or ''} (p.{t['pagina_inicio']}-{t['pagina_fim']}) ──\n{t['texto']}", fmt)
    elif c == "nota":
        imprimir(le.nota(arg), fmt)
    elif c in ("stats", "estatisticas"):
        imprimir(le.estatisticas(), fmt)
    elif c in ("ajuda", "help", "?"):
        print(__doc__)
    else:
        raise ErroConsulta(f"Comando desconhecido: {a.comando!r}. Use: python codificacao_db.py ajuda")


def interativo(le, parser):
    print("Livro dos Espíritos — modo interativo. Ex.: pergunta 182.b | buscar orgulho --ids | sair")
    while True:
        try:
            linha = input("le> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if linha in ("sair", "exit", "quit"):
            break
        if not linha:
            continue
        try:
            executar(le, parser.parse_args(shlex.split(linha)))
        except SystemExit:
            pass
        except (ErroConsulta, KeyError, ValueError) as e:
            print("Erro:", e)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # acentos no terminal do Windows
    parser = construir_parser()
    a = parser.parse_args(argv)
    le = LivroDosEspiritos(a.banco)
    if not a.comando:
        interativo(le, parser)
        return
    try:
        executar(le, a)
    except (ErroConsulta, KeyError, ValueError) as e:
        print("Erro:", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
