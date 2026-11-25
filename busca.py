"""Busca semântica em O Livro dos Espíritos (perguntas, comentários de Kardec e notas).

Combina três técnicas, todas rodando no seu computador (sem IA na nuvem, sem tokens):
  1. Busca por significado (embeddings densos; padrão: BAAI/bge-m3).
  2. BM25 (palavras em comum, valorizando as raras).
  3. Reordenação com cross-encoder (padrão: BAAI/bge-reranker-v2-m3), que dá a nota final 0-100%.

Primeiro uso (demora alguns minutos, só uma vez):
    pip install -r requirements.txt
    python busca.py indexar

Consultas (exemplos):
    python busca.py buscar "meu pai morreu num acidente e brigamos na véspera"
    python busca.py buscar "..." --duvida "o pai está sofrendo?" --duvida "dá para pedir perdão?"
    python busca.py buscar "..." -n 50 --formato completo
    python busca.py buscar "..." --min 40 --ordem livro --formato ids
    python busca.py ranking "..."                 # todas as perguntas, da mais à menos provável
    python busca.py nota "..." --ids "163, K163, 935"
    python busca.py interativo

Formatos de saída (--formato):
    ids        163 | K163 | 935                      (padrão: o mesmo formato da skill)
    ids-nota   163 (87%) | K163 (61%) | ...
    linhas     uma linha por item: id, nota e começo do texto
    completo   pergunta e resposta inteiras, separadas por linhas de traços
    json       lista de objetos (para programas)

Tipos de item: pergunta/subpergunta (163, 182.b), item numerado de Kardec (872),
comentário de Kardec (K163), nota de rodapé (N4) e texto de Kardec sem número (Ke1).
Use --tipos para filtrar, por exemplo --tipos pergunta,comentario.
"""
import argparse
import json
import math
import re
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from codificacao_db import LivroDosEspiritos  # noqa: E402

PASTA_INDICE = AQUI / "indice"
MODELO_PADRAO = "BAAI/bge-m3"
RERANKER_PADRAO = "BAAI/bge-reranker-v2-m3"
TRACOS = "-" * 54

TIPOS = {
    "pergunta": "pergunta",       # perguntas e subperguntas
    "kardec": "kardec",           # itens numerados escritos por Kardec (59, 100-113, 222, 872...)
    "comentario": "comentario",   # K163
    "nota": "nota",               # N4
    "texto_kardec": "texto_kardec",  # Ke1
    "introducao": "introducao",   # I1 a I125 (parágrafos da Introdução)
}

# ───────────────────────────── texto ─────────────────────────────
STOP = set("""a o e é de do da dos das em no na nos nas um uma uns umas que se por para com como mas ou
ao aos à às pelo pela pelos pelas seu sua seus suas ele ela eles elas isso isto esse essa este esta
não sim já mais muito muita também quando onde qual quais quem lhe lhes me te nos vos meu minha
teu tua nosso nossa ser foi são está estar era há tem ter sobre entre até sem mesmo pois porque
assim então ainda só cada todo toda todos todas outro outra outros outras vós eu tu nós""".split())


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 and t not in STOP]


def trechos(texto, tamanho=1200, sobra=200):
    """Corta textos longos (ex.: o item 222, com 21 mil caracteres) em pedaços com sobreposição."""
    if len(texto) <= tamanho:
        return [texto]
    partes, i = [], 0
    while i < len(texto):
        fim = min(len(texto), i + tamanho)
        if fim < len(texto):
            espaco = texto.rfind(" ", i + tamanho - sobra, fim)
            fim = espaco if espaco > i else fim
        partes.append(texto[i:fim].strip())
        if fim >= len(texto):
            break
        i = max(fim - sobra, i + 1)
    return partes


# ───────────────────────────── itens do livro ─────────────────────────────
def carregar_itens(le):
    """Lista de itens buscáveis, na ordem do livro."""
    itens = []
    for i in le.I.values():                       # a Introdução vem antes da 1ª pergunta
        itens.append({"id": i["id"], "tipo": "introducao", "pergunta": "", "resposta": i["texto"],
                      "secao": f"Introdução, item {i['item']}"})
    for pid in le.ordem:
        p = le.P[pid]
        if p["tipo"] == "pergunta":
            itens.append({"id": pid, "tipo": "pergunta", "pergunta": p["pergunta"] or "",
                          "resposta": p["resposta"] or "", "secao": p.get("secao") or ""})
        else:
            itens.append({"id": pid, "tipo": "kardec", "pergunta": "",
                          "resposta": p.get("texto") or "", "secao": p.get("secao") or ""})
        if p.get("comentario"):
            itens.append({"id": f"K{pid}", "tipo": "comentario", "pergunta": "",
                          "resposta": p["comentario"], "secao": p.get("secao") or "", "de": pid})
    for n in le.db.get("notas_rodape", {}).values():
        itens.append({"id": f"N{n['numero']}", "tipo": "nota", "pergunta": "",
                      "resposta": n["texto"], "secao": n.get("autor") or ""})
    for t in le.db.get("textos_kardec", {}).values():
        itens.append({"id": t["id"], "tipo": "texto_kardec", "pergunta": "",
                      "resposta": t["texto"], "secao": t.get("secao") or ""})
    return itens


def texto_item(it):
    if it["pergunta"]:
        return f"Pergunta: {it['pergunta']}\nResposta: {it['resposta']}"
    return it["resposta"]


# ───────────────────────────── modelos ─────────────────────────────
def _prefixos(modelo):
    m = modelo.lower()
    if "e5" in m:
        return "query: ", "passage: "
    return "", ""


class EmbedderONNX:
    """bge-m3 rodando por ONNX Runtime (sem HuggingFace, sem PyTorch).

    Os arquivos vêm do release 'onnx.zip' de github.com/yuniko-software/bge-m3-onnx:
    bge_m3_tokenizer.onnx, bge_m3_model.onnx e bge_m3_model.onnx_data na mesma pasta.
    Só o vetor denso (1024 números, já normalizado) é usado.
    """

    def __init__(self, pasta):
        import onnxruntime as ort
        from onnxruntime_extensions import get_library_path
        pasta = Path(pasta)
        opt_tok = ort.SessionOptions()
        opt_tok.register_custom_ops_library(get_library_path())
        self.tok = ort.InferenceSession(str(pasta / "bge_m3_tokenizer.onnx"), sess_options=opt_tok,
                                        providers=["CPUExecutionProvider"])
        opt = ort.SessionOptions()
        opt.log_severity_level = 3
        provedores = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider")
                      if p in ort.get_available_providers()]
        self.mod = ort.InferenceSession(str(pasta / "bge_m3_model.onnx"), sess_options=opt,
                                        providers=provedores)

    def _um(self, texto):
        ids, _, pos = self.tok.run(None, {"inputs": np.array([texto])})
        ordem = np.argsort(pos)
        ids = np.array([ids[ordem]], dtype=np.int64)
        saida = self.mod.run(None, {"input_ids": ids, "attention_mask": np.ones_like(ids)})
        v = saida[0][0].astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-12)

    def encode(self, textos, batch_size=8, normalize_embeddings=True, show_progress_bar=False,
               convert_to_numpy=True):
        saida = []
        for i, t in enumerate(textos):
            saida.append(self._um(t))
            if show_progress_bar and (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(textos)}", flush=True)
        return np.array(saida, dtype=np.float32)


def _pasta_onnx(modelo):
    """'onnx' ou 'onnx:/caminho' -> pasta com os arquivos .onnx (ou variável BGE_M3_ONNX)."""
    import os
    caminho = modelo.split(":", 1)[1] if ":" in modelo else ""
    return Path(caminho or os.environ.get("BGE_M3_ONNX") or AQUI / "modelo_onnx")


def carregar_embedder(modelo):
    if modelo.lower().startswith("onnx"):
        return EmbedderONNX(_pasta_onnx(modelo))
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(modelo)


def carregar_reranker(modelo):
    """O reranker é opcional: sem ele (ex.: HuggingFace bloqueado) as notas ficam relativas."""
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(modelo, max_length=1024)
    except Exception as erro:  # noqa: BLE001
        print(f"[aviso] reranker indisponível ({type(erro).__name__}); usando nota relativa.",
              file=sys.stderr)
        return None


# ───────────────────────────── índice ─────────────────────────────
def indexar(modelo=MODELO_PADRAO, pasta=PASTA_INDICE, lote=8):
    le = LivroDosEspiritos()
    itens = carregar_itens(le)
    _, pref_doc = _prefixos(modelo)
    docs, dono = [], []
    for i, it in enumerate(itens):
        for tr in trechos(texto_item(it)):
            docs.append(pref_doc + tr)
            dono.append(i)
    print(f"{len(itens)} itens, {len(docs)} trechos. Gerando vetores com {modelo} "
          "(pode levar vários minutos; só é feito uma vez)...")
    t0 = time.time()
    emb = carregar_embedder(modelo)
    vet = emb.encode(docs, batch_size=lote, normalize_embeddings=True, show_progress_bar=True,
                     convert_to_numpy=True).astype(np.float32)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    np.save(pasta / "vetores.npy", vet)
    (pasta / "meta.json").write_text(json.dumps(
        {"modelo": modelo, "dono": dono, "ids": [it["id"] for it in itens], "criado": time.ctime()},
        ensure_ascii=False), encoding="utf-8")
    print(f"Índice salvo em {pasta} ({time.time() - t0:.0f} s).")


class Buscador:
    """Carrega o índice uma vez; cada consulta depois é rápida."""

    def __init__(self, pasta=PASTA_INDICE, reranker=RERANKER_PADRAO, usar_reranker=True):
        pasta = Path(pasta)
        if not (pasta / "meta.json").exists():
            raise SystemExit("Índice não encontrado. Rode primeiro: python busca.py indexar")
        meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
        self.le = LivroDosEspiritos()
        self.itens = carregar_itens(self.le)
        if [it["id"] for it in self.itens] != meta["ids"]:
            raise SystemExit("O banco mudou desde a indexação. Rode de novo: python busca.py indexar")
        self.pos = {it["id"]: i for i, it in enumerate(self.itens)}
        self.modelo = meta["modelo"]
        self.pref_q, _ = _prefixos(self.modelo)
        self.vet = np.load(pasta / "vetores.npy")
        self.dono = np.array(meta["dono"])
        self.emb = carregar_embedder(self.modelo)
        from rank_bm25 import BM25Okapi
        self.bm25 = BM25Okapi([tokens(texto_item(it)) or ["_"] for it in self.itens])
        self.rer = carregar_reranker(reranker) if usar_reranker else None

    # ---------- notas de cada etapa ----------
    def _denso(self, consultas):
        q = self.emb.encode([self.pref_q + c for c in consultas], normalize_embeddings=True,
                            convert_to_numpy=True).astype(np.float32)
        sim = q @ self.vet.T                                  # consultas x trechos
        por_item = np.full((len(consultas), len(self.itens)), -1.0, dtype=np.float32)
        for j in range(len(consultas)):
            np.maximum.at(por_item[j], self.dono, sim[j])     # item = melhor trecho
        return por_item

    def _bm25(self, consultas):
        return np.array([self.bm25.get_scores(tokens(c) or ["_"]) for c in consultas])

    @staticmethod
    def _rrf(*matrizes, k=60):
        """Fusão por posição (Reciprocal Rank Fusion), por consulta."""
        total = 0
        for m in matrizes:
            ordem = np.argsort(-m, axis=1)
            pos = np.empty_like(ordem)
            linhas = np.arange(m.shape[0])[:, None]
            pos[linhas, ordem] = np.arange(m.shape[1])[None, :]
            total = total + 1.0 / (k + pos + 1)
        return total

    def pontuar(self, situacao, duvidas=(), candidatos=60, rerank=True, ids=None):
        """Devolve {id: nota 0-100} (com reranker) ou {id: nota relativa 0-100} (sem reranker).
        Cada dúvida é buscada separadamente e o item fica com a MAIOR nota entre elas."""
        consultas = [situacao] + [d for d in duvidas if d.strip()]
        fus = self._rrf(self._denso(consultas), self._bm25(consultas))       # consultas x itens
        melhor = fus.max(axis=0)
        if ids is not None:
            escolhidos = [self.pos[i] for i in ids]
        else:
            n = len(self.itens) if candidatos <= 0 else candidatos
            escolhidos = list(np.argsort(-melhor)[:n])
        if rerank and self.rer is not None:
            pares = [(c, texto_item(self.itens[i])[:4000]) for i in escolhidos for c in consultas]
            bruto = np.array(self.rer.predict(pares, batch_size=16, show_progress_bar=False),
                             dtype=np.float64).reshape(len(escolhidos), len(consultas))
            if bruto.min() < 0 or bruto.max() > 1:          # logits -> probabilidade
                bruto = 1 / (1 + np.exp(-bruto))
            notas = bruto.max(axis=1) * 100
        else:
            v = melhor[escolhidos]
            lo, hi = melhor.min(), melhor.max()
            notas = (v - lo) / (hi - lo + 1e-12) * 100
        return {self.itens[i]["id"]: float(n) for i, n in zip(escolhidos, notas)}

    # ---------- consultas prontas ----------
    def buscar(self, situacao, duvidas=(), n=20, candidatos=60, minimo=0, ordem="nota",
               tipos=None, rerank=True):
        notas = self.pontuar(situacao, duvidas, candidatos=max(candidatos, n), rerank=rerank)
        res = [(i, s) for i, s in notas.items()
               if s >= minimo and (not tipos or self.itens[self.pos[i]]["tipo"] in tipos)]
        res.sort(key=lambda x: -x[1])
        res = res[:n] if n > 0 else res
        if ordem == "livro":
            res.sort(key=lambda x: self.pos[x[0]])
        return res

    def ranking(self, situacao, duvidas=(), rerank_top=100, tipos=None):
        """Todos os itens do livro, do mais ao menos provável.
        Os `rerank_top` primeiros recebem a nota do reranker; os demais seguem a ordem da busca."""
        topo = self.pontuar(situacao, duvidas, candidatos=rerank_top, rerank=True) if rerank_top > 0 else {}
        resto = self.pontuar(situacao, duvidas, candidatos=0, rerank=False)
        lista = sorted(topo.items(), key=lambda x: -x[1])
        lista += sorted(((i, s) for i, s in resto.items() if i not in topo), key=lambda x: -x[1])
        if tipos:
            lista = [x for x in lista if self.itens[self.pos[x[0]]]["tipo"] in tipos]
        return lista

    def nota(self, situacao, ids, duvidas=()):
        ids = [self._id(x) for x in re.split(r"[,;|\s]+", ids) if x.strip()]
        faltam = [i for i in ids if i not in self.pos]
        if faltam:
            print(f"Aviso: não existem no banco: {', '.join(faltam)}", file=sys.stderr)
        ids = [i for i in ids if i in self.pos]
        return sorted(self.pontuar(situacao, duvidas, ids=ids).items(), key=lambda x: -x[1])

    def _id(self, x):
        x = x.strip()
        if x[:2].upper() == "KE":
            return "Ke" + x[2:]
        if re.fullmatch(r"[Ii]\d+", x):
            return "I" + x[1:]
        if x[:1].upper() in "KN":
            return x[:1].upper() + (self.le.normalizar_id(x[1:]) if x[:1].upper() == "K" else x[1:])
        return self.le.normalizar_id(x)

    # ---------- saída ----------
    def formatar(self, lista, formato="ids"):
        if formato == "ids":
            return " | ".join(i for i, _ in lista)
        if formato == "ids-nota":
            return " | ".join(f"{i} ({s:.0f}%)" for i, s in lista)
        if formato == "json":
            return json.dumps([dict(self.itens[self.pos[i]], nota=round(s, 1)) for i, s in lista],
                              ensure_ascii=False, indent=2)
        if formato == "linhas":
            out = []
            for i, s in lista:
                t = re.sub(r"\s+", " ", texto_item(self.itens[self.pos[i]]))
                out.append(f"{i:>7}  {s:5.1f}%  {t[:110]}")
            return "\n".join(out)
        if formato == "completo":
            blocos = []
            for i, s in lista:
                it = self.itens[self.pos[i]]
                cab = {"pergunta": f"[{i}]", "kardec": f"[{i}] Kardec",
                       "comentario": f"[{i}] Comentário de Kardec à pergunta {it.get('de', '')}",
                       "nota": f"[{i}] Nota de rodapé ({it['secao']})",
                       "texto_kardec": f"[{i}] Texto de Kardec",
                       "introducao": f"[{i}] {it['secao']}"}[it["tipo"]]
                linhas = [f"{cab}  —  relevância {s:.0f}%"]
                if it["pergunta"]:
                    linhas += [f"P: {it['pergunta']}", f"R: {it['resposta']}"]
                else:
                    linhas.append(it["resposta"])
                blocos.append("\n".join(linhas))
            return f"\n{TRACOS}\n".join(blocos)
        raise SystemExit(f"Formato desconhecido: {formato}")


# ───────────────────────────── linha de comando ─────────────────────────────
def parser():
    ap = argparse.ArgumentParser(description="Busca semântica em O Livro dos Espíritos.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("indexar", help="gera os vetores (uma vez só)")
    i.add_argument("--modelo", default=MODELO_PADRAO)
    i.add_argument("--lote", type=int, default=8)

    def comuns(p, n=True):
        p.add_argument("situacao")
        p.add_argument("--duvida", action="append", default=[],
                       help="dúvida separada (pode repetir); o item fica com a maior nota")
        p.add_argument("--formato", default="ids", choices=["ids", "ids-nota", "linhas", "completo", "json"])
        p.add_argument("--tipos", default="", help="ex.: pergunta,comentario,nota,kardec,texto_kardec,introducao")
        p.add_argument("--reranker", default=RERANKER_PADRAO)
        p.add_argument("--sem-reranker", action="store_true", help="mais rápido, nota só relativa")

    b = sub.add_parser("buscar", help="itens mais prováveis")
    comuns(b)
    b.add_argument("-n", type=int, default=20, help="quantos itens (0 = todos os candidatos)")
    b.add_argument("--candidatos", type=int, default=60, help="quantos vão para o reranker")
    b.add_argument("--min", type=float, default=0, help="nota mínima (0-100)")
    b.add_argument("--ordem", default="nota", choices=["nota", "livro"])

    r = sub.add_parser("ranking", help="todas as perguntas, da mais à menos provável")
    comuns(r)
    r.add_argument("--rerank-top", type=int, default=100)

    t = sub.add_parser("nota", help="nota de itens específicos")
    comuns(t)
    t.add_argument("--ids", required=True)

    it = sub.add_parser("interativo", help="digita situações uma atrás da outra")
    it.add_argument("-n", type=int, default=15)
    it.add_argument("--formato", default="completo", choices=["ids", "ids-nota", "linhas", "completo", "json"])
    it.add_argument("--sem-reranker", action="store_true")
    it.add_argument("--reranker", default=RERANKER_PADRAO)
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    if a.cmd == "indexar":
        return indexar(a.modelo, lote=a.lote)
    bus = Buscador(reranker=a.reranker, usar_reranker=not a.sem_reranker)
    if a.cmd == "interativo":
        print("Digite a situação (Enter vazio para sair).")
        while True:
            try:
                s = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not s:
                break
            t0 = time.time()
            print(bus.formatar(bus.buscar(s, n=a.n, rerank=not a.sem_reranker), a.formato))
            print(f"\n({time.time() - t0:.1f} s)")
        return
    tipos = set(x.strip() for x in a.tipos.split(",") if x.strip()) or None
    if a.cmd == "buscar":
        lista = bus.buscar(a.situacao, a.duvida, n=a.n, candidatos=a.candidatos, minimo=a.min,
                           ordem=a.ordem, tipos=tipos, rerank=not a.sem_reranker)
    elif a.cmd == "ranking":
        lista = bus.ranking(a.situacao, a.duvida, rerank_top=0 if a.sem_reranker else a.rerank_top, tipos=tipos)
    else:
        lista = bus.nota(a.situacao, a.ids, a.duvida)
    print(bus.formatar(lista, a.formato))


if __name__ == "__main__":
    main()
