# Backup das skills do projeto Espiritismo (24/11/2026)

Cópia das skills como estavam salvas no claude.ai nesta data. Cada pasta tem o `SKILL.md`.

- `espiritismo-init`: prepara o banco e abre os 8 agentes Haiku (H1–H8), um por bloco do livro.
- `copia-pergunta`: acha a pergunta equivalente no livro com uma busca só (`candidatos.py rapido`) e mostra pergunta e resposta.
- `perguntas-livro-espiritos` (parte 1): os 8 agentes dão nota às perguntas e notas para a situação e devolvem a matriz `[['id', tokens, nota], ...]` (30%+), cortada em 20 mil tokens por `selecionar.py`.
- `pergunta-livro-espiritos-2` (parte 2): lê os textos (`consultar_lista.py`) e `docs/estilo_kardec.md`, e responde em blocos com perguntas transcritas e análise cruzada no estilo de Kardec.

Para restaurar uma skill, crie-a no claude.ai com o conteúdo do `SKILL.md` correspondente.
