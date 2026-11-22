"""Digite uma situação e veja as perguntas de O Livro dos Espíritos mais prováveis.

Fica na mesma pasta do repositório (precisa de busca.py, codificacao_db.py e da pasta dados/).
Primeira vez:  pip install -r requirements.txt   e depois   python busca.py indexar
Uso:           python pergunte.py
"""
import time

from busca import Buscador, carregar_itens  # noqa: F401

QUANTOS = 15      # quantos itens mostrar
NOTA_MINIMA = 0   # ex.: 40 para mostrar só os de 40% ou mais

print("Carregando os modelos (só demora na primeira consulta)...")
bus = Buscador()
print("Pronto. Digite a situação e aperte Enter (Enter vazio para sair).")

while True:
    try:
        situacao = input("\nSituação: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not situacao:
        break
    t0 = time.time()
    lista = bus.buscar(situacao, n=QUANTOS, minimo=NOTA_MINIMA)
    print()
    print(bus.formatar(lista, "completo"))
    print(f"\n({len(lista)} itens em {time.time() - t0:.1f} s)")
