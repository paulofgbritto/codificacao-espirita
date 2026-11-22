"""Gera os 8 blocos de O Livro dos Espíritos usados pela skill perguntas-livro-espiritos.

Uso: python montar_blocos.py [pasta_saida]   (padrão: blocos/)
Exporta os 29 capítulos com codificacao_db.py e junta-os em 8 arquivos
(bloco1.txt ... bloco8.txt) de tamanho parecido, sem cortar capítulos.
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
    ["P2C08"],
    ["P2C09", "P2C10", "P2C11", "P3C01"],
    ["P3C02", "P3C03", "P3C04", "P3C05", "P3C06", "P3C07", "P3C08"],
    ["P3C09", "P3C10", "P3C11", "P3C12"],
    ["P4C01", "P4C02"],
]


def main():
    saida = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, "blocos"))
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
            print(destino, os.path.getsize(destino))


if __name__ == "__main__":
    main()
