---
name: "espiritismo-init"
description: "Inicializa a sessão do projeto Espiritismo: prepara o banco e abre 8 agentes Haiku fixos (H1–H8), cada um já com seu bloco de O Livro dos Espíritos lido, para as outras skills reutilizarem."
---

# espiritismo-init

Abre os 8 Haiku **uma vez por sessão**. Depois, a skill `perguntas-livro-espiritos` só manda mensagens a eles (SendMessage), sem abrir agentes novos: o custo fixo de ~60 mil tokens por agente é pago só aqui, e o resto é relido do cache.

Se `/home/claude/haikus.json` já existe, a sessão já está inicializada: não faça nada.

## Passo 1 — Preparar arquivos (sem tokens)

```bash
cd /home/claude
[ -d codificacao-espirita ] || git clone --depth 1 https://github.com/paulofgbritto/codificacao-espirita
cd codificacao-espirita
[ -f dados/livro_dos_espiritos.json ] || (cd dados && unzip -oq livro_dos_espiritos.zip)
[ -f /home/claude/blocos/bloco8.txt ] || python3 montar_blocos.py /home/claude/blocos
pip install --break-system-packages -q onnxruntime onnxruntime-extensions rank_bm25 numpy
if [ ! -f modelo_onnx/bge_m3_model.onnx_data ]; then
  mkdir -p /home/claude/_modelo && cd /home/claude/_modelo
  curl -sSL -o onnx.zip https://github.com/yuniko-software/bge-m3-onnx/releases/latest/download/onnx.zip
  unzip -oq onnx.zip && rm onnx.zip && mkdir -p /home/claude/codificacao-espirita/modelo_onnx
  find . -type f -name 'bge_m3_*' -exec mv {} /home/claude/codificacao-espirita/modelo_onnx/ \;
  cd /home/claude && rm -rf /home/claude/_modelo
fi
cd /home/claude
ls codificacao-espirita/modelo_onnx  # deve listar bge_m3_model.onnx, bge_m3_model.onnx_data e bge_m3_tokenizer.onnx
# aquecer o modelo (traz os 1,3 GB para o cache do disco; as buscas seguintes levam ~3 s)
cd codificacao-espirita && python3 candidatos.py rapido "aquecimento" 1 >/dev/null 2>&1; cd /home/claude
```
Timeout de 600000 ms (o modelo tem 1,3 GB). O índice já vem pronto no repositório; nunca baixe nada pelo conector do Google Drive.

## Passo 2 — Abrir H1 a H8

Num único bloco, 8 chamadas da ferramenta Agent (`model: haiku`, `run_in_background: false`, descrição `H1` ... `H8`), cada uma com este prompt (troque N):

```
Você é o agente HN do projeto Espiritismo e vai ficar disponível durante a sessão inteira. Use apenas a ferramenta Read.

Agora: leia o arquivo /home/claude/blocos/blocoN.txt INTEIRO (um trecho de O Livro dos Espíritos, de Allan Kardec). Leia em partes com offset/limit até a última linha, sem pular nada, e guarde-o: as próximas tarefas sobre "o seu bloco" se referem a ele, e você não deve relê-lo.
Identificadores entre colchetes: [919.a] = pergunta (P) e resposta dos Espíritos (R); [K919.a] = comentário de Kardec; [N4] = nota de rodapé; [872] Kardec (texto numerado) = item escrito por Kardec; [Ke1] = texto de Kardec sem número.

Depois você receberá tarefas por mensagem. Em cada uma, responda SOMENTE no formato pedido, sem texto extra.

Responda agora apenas: PRONTO HN
```

## Passo 3 — Registrar os ids

Pegue o `agentId` de cada resultado e grave:
```bash
cat > /home/claude/haikus.json <<'EOF'
{"H1": "<id>", "H2": "<id>", "H3": "<id>", "H4": "<id>", "H5": "<id>", "H6": "<id>", "H7": "<id>", "H8": "<id>"}
EOF
```
Se algum não respondeu `PRONTO`, abra só aquele de novo. Responda ao usuário numa linha: `Pronto: H1–H8 ativos.`

## Regras
- Os ids valem só nesta sessão. Em sessão nova, rode o init de novo.
- A skill `copia-pergunta` não usa estes agentes (busca direta, sem init).
- Se um SendMessage a um Hn falhar (agente não encontrado), reabra só aquele Hn com o prompt acima e atualize o haikus.json.