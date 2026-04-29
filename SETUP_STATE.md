# Langfuse Setup - Estado Atual e Próximos Passos

## O que foi feito

1. **Projeto criado**: `/home/epmq/Desktop/Projects/aegis-kg-unified/`
   - Copiado de `aegis_kg/` com adaptações
   - KG unificado: AEGIS (GDPR, CRA, DORA, NIS2, AI Act) + NIST CSF 2.0
   - 426 nós, 114 relações MAPS_TO_SUBDOMAIN

2. **Módulo de avaliação criado**: `aegis_eval/` (rename de `eval/` para evitar conflito)
   - `run_eval.py` - runner principal
   - `config.py` - configuração NEO4J, OLLAMA, LANGFUSE
   - `schema_context.py` - contexto do esquema (AEGIS + NIST bidirecional)
   - `text2cypher.py` - geração de Cypher
   - `judge.py` - judge LLM
   - `task_bank.yaml` - 45 tarefas (33 regulatórias + 12 NIST/unified)

3. **docker-compose.yml** configurado:
   - langfuse + postgres (langfuse:latest = v3)
   - SEM ClickHouse (foi o problema)

## O problema

Langfuse v3 (latest) **requer ClickHouse** como storage obrigatório.
Langfuse v2 usava apenas PostgreSQL mas já não está disponível no Docker Hub.

Erro actual:
```
error: failed to open database: database driver: unknown driver http (forgotten import?)
Applying clickhouse migrations failed.
```

## Soluções possíveis

### Opção A: ClickHouse funciona mas Langfuse não conecta
O ClickHouse 23.8 Alpine está a funcionar mas Langfuse não consegue conectar.
Provável causa: driver ClickHouse não incluído na imagem ou problema de rede interno.

**Testar**: Verificar se `CLICKHOUSE_URL` e `CLICKHOUSE_MIGRATION_URL` estão correctos.
Formato Migration URL: `clickhouse://host:9000` (não http)

### Opção B: Usar Langfuse Cloud em vez de self-hosted
A forma mais rápida de continuar é usar Langfuse Cloud em vez de self-hosted.
URL: https://langfuse.com

### Opção C: Voltar à versão anterior do clickhouse
Tentar clickhouse/clickhouse-server:24-alpine ou versão diferente.

## Próximos passos recomendados

1. **Testar a ligação ao ClickHouse** do container langfuse:
```bash
docker exec aegis-kg-unified-langfuse-1 getent hosts langfuse-clickhouse
docker exec aegis-kg-unified-langfuse-1 curl http://langfuse-clickhouse:8123
```

2. **Se ClickHouse funciona**: Corrigir variáveis de ambiente CLICKHOUSE_URL e CLICKHOUSE_MIGRATION_URL

3. **Se não funcionar**: Usar Langfuse Cloud ou outra solução

4. **Após Langfuse funcionar**:
   - Criar projeto na UI, gerar API keys
   - Actualizar `aegis_eval/config.py` com as keys
   - Correr avaliação: `source /home/epmq/Desktop/Projects/shared-venv/bin/activate && cd /home/epmq/Desktop/Projects/aegis-kg-unified/eval && python run_eval.py --tasks task_bank.yaml --task list_all_regulations --trials 1 --verbose`

## Ficheiros importantes

- `/home/epmq/Desktop/Projects/aegis-kg-unified/docker-compose.yml`
- `/home/epmq/Desktop/Projects/aegis-kg-unified/aegis_eval/run_eval.py`
- `/home/epmq/Desktop/Projects/aegis-kg-unified/aegis_eval/config.py`
- `/home/epmq/Desktop/Projects/aegis-kg-unified/aegis_eval/task_bank.yaml`

## Comandos úteis

```bash
# Ver estado dos containers
docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep aegis

# Ver logs do langfuse
docker logs aegis-kg-unified-langfuse-1 --tail 20

# Ver logs do clickhouse
docker logs aegis-kg-unified-langfuse-clickhouse-1 --tail 10

# Testar clickhouse
docker exec aegis-kg-unified-langfuse-clickhouse-1 clickhouse-client --query "SHOW DATABASES"

# Reiniciar tudo
cd /home/epmq/Desktop/Projects/aegis-kg-unified && docker compose down -v && docker compose up -d
```

---

## Prompt para continuar

```
Continua o setup do Langfuse no projeto /home/epmq/Desktop/Projects/aegis-kg-unified/

Problema actual: Langfuse v3 (latest) não arranca porque precisa de ClickHouse mas a ligação falha.

O container clickhouse está a funcionar (confirmado com clickhouse-client).
O erro no langfuse é: "database driver: unknown driver http"

Tenta:
1. Verificar a rede entre langfuse e clickhouse (mesmo network docker-compose)
2. Testar se CLICKHOUSE_MIGRATION_URL=clickhouse://langfuse-clickhouse:9000 funciona
3. Verificar se o driver clickhouse está presente na imagem langfuse

Se não conseguires resolver, a alternativa é usar Langfuse Cloud em vez de self-hosted.

Depois de teres o Langfuse a funcionar:
1. Accede à UI http://localhost:3000
2. Cria um projeto e gera API keys
3. Actualiza aegis_eval/config.py com as keys
4. Corre a avaliação: source /home/epmq/Desktop/Projects/shared-venv/bin/activate && cd /home/epmq/Desktop/Projects/aegis-kg-unified/eval && python run_eval.py --tasks task_bank.yaml --task list_all_regulations --trials 1 --verbose
```
