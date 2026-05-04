# AEGIS-KG-UNIFIED: Plano de Implementação — Próximos Passos Incrementais

**Versão:** 1.0 | **Data:** 2026-05-04 | **Status:** Aguardando execução

---

## 🎯 RESUMO

Este plano detalha 4 passos incrementais para melhorar o projeto `aegis-kg-unified`. **Importante:** 2 dos 4 passos podem já estar completos — verificar primeiro.

---

## 🔍 PASSO 0: VERIFICAÇÕES INICIAIS (OBRIGATÓRIO)

> **⚠️ CRÍTICO:** Verificar primeiro se Passos 1 e 3 já estão implementados.

### 0.1 Verificar schema_context.py — já usa DOT separator?

```bash
# CHECKPOINT 1a: Procurar hífens no schema
rg "D-\d{2}-" aegis_eval/schema_context.py
# ESPERADO: 0 resultados

# CHECKPOINT 1b: Confirmar que D-01.1 existe
python3 -c "from aegis_eval.schema_context import SCHEMA_DESCRIPTION; assert 'D-01.1' in SCHEMA_DESCRIPTION; print('OK: schema_context.py já usa D-01.1')"
# ESPERADO: "OK: schema_context.py já usa D-01.1"
```

**Se falhar (encontrar hífens):** Executar **Passo 1**.  
**Se passar:** **Pular Passo 1** — já está correto.

### 0.2 Verificar Health Endpoint da API

```bash
# CHECKPOINT 2a: Testar endpoint
python3 -c "
import requests, sys
r = requests.get('http://localhost:5000/api/health', timeout=5)
print(f'Status: {r.status_code}')
print(f'Response: {r.json()}')
assert r.status_code == 200
assert r.json().get('status') == 'healthy'
print('OK: /api/health funciona')
"
# ESPERADO: {"status": "healthy", "neo4j_version": "5.x.x"}
```

**Se falhar (404 ou não responde):** Executar **Passo 3**.  
**Se passar:** **Pular Passo 3** — já existe.

### 📝 DECISÃO APÓS PASSO 0

| CHECKPOINT | Resultado | Ação |
|------------|-----------|------|
| 1a + 1b | ✅ Passa | **Pular Passo 1** |
| 1a + 1b | ❌ Falha | **Executar Passo 1** |
| 2a | ✅ Passa | **Pular Passo 3** |
| 2a | ❌ Falha | **Executar Passo 3** |

---

## 📊 PASSO 1: Corrigir schema_context.py (SE NECESSÁRIO)

> **Só executar se CHECKPOINT 1a encontrar hífens (`D-01-1`)**

### Implementação

1. Abrir `aegis_eval/schema_context.py`
2. Localizar todas as ocorrências de `D-XX-Y` (hífen)
3. Substituir por `D-XX.Y` (ponto)
4. Verificar comentários e exemplos de queries

### Edições necessárias (se aplicável)

```python
# ANTES (errado):
"D-01-1", "D-02-3", "D-10-2"

# DEPOIS (correto):
"D-01.1", "D-02.3", "D-10.2"
```

### Verificação Final

```bash
# CHECKPOINT 1c: Confirmar correção
python3 -c "
from aegis_eval.schema_context import SCHEMA_DESCRIPTION
assert 'D-01-1' not in SCHEMA_DESCRIPTION, 'Ainda tem hífens!'
assert 'D-01.1' in SCHEMA_DESCRIPTION, 'Falta D-01.1!'
print('OK: schema_context.py corrigido')
"
```

---

## 📊 PASSO 2: Criar Script de Análise de Resultados (SEMPRE EXECUTAR)

> **Objetivo:** Criar `aegis_eval/analyze_results.py` para extrair insights dos ~70 runs acumulados.

### 2.1 Pré-condições

```bash
# CHECKPOINT 4: Verificar diretório de resultados
ls aegis_eval/results/summary_*.json | wc -l
# ESPERADO: >= 1 (idealmente ~70)

# CHECKPOINT 5: Verificar estrutura de um resultado
python3 -c "
import json, glob
files = sorted(glob.glob('aegis_eval/results/summary_*.json'))
assert files, 'Nenhum ficheiro encontrado!'
data = json.load(open(files[0]))
required = ['timestamp', 'by_dimension', 'by_category', 'pass_rate']
for k in required:
    assert k in data, f'Falta chave: {k}'
print(f'OK: Estrutura válida (encontrados {len(files)} ficheiros)')
"
```

### 2.2 Implementação

Criar ficheiro: `aegis_eval/analyze_results.py`

```python
#!/usr/bin/env python3
"""
analyze_results.py — Analyze accumulated evaluation results.

Usage:
    python analyze_results.py --results-dir aegis_eval/results/
    
Output:
    - Tabela markdown no stdout
    - Ficheiro .md em results/analysis_report_YYYYMMDD_HHMMSS.md
"""

import json
import glob
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas tabulate")
    sys.exit(1)


def load_results(results_dir: str) -> list[dict]:
    """Load all summary_*.json files."""
    pattern = Path(results_dir) / "summary_*.json"
    files = sorted(glob.glob(str(pattern)))
    
    if not files:
        print(f"ERROR: No summary_*.json files found in {results_dir}")
        sys.exit(1)
    
    print(f"✓ Found {len(files)} result files")
    
    results = []
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            data["_source_file"] = Path(f).name
            results.append(data)
    
    return results


def compute_trends(results: list[dict]) -> dict:
    """Compute score trends over time by dimension."""
    if not results:
        return {}
    
    trends = defaultdict(list)
    for r in sorted(results, key=lambda x: x.get("timestamp", "")):
        ts = r.get("timestamp", "unknown")
        for dim, scores in r.get("by_dimension", {}).items():
            trends[dim].append({
                "timestamp": ts,
                "overall_avg": scores.get("overall_avg", 0),
                "query_avg": scores.get("query_avg", 0),
                "answer_avg": scores.get("answer_avg", 0)
            })
    
    return dict(trends)


def find_unstable_tasks(results: list[dict], top_n: int = 5) -> list[tuple]:
    """Find categories with highest variance across runs."""
    task_scores = defaultdict(list)
    
    for r in results:
        for cat, data in r.get("by_category", {}).items():
            avg_scores = data.get("avg_scores", {})
            if avg_scores:
                avg = sum(avg_scores.values()) / len(avg_scores)
                task_scores[cat].append(avg)
    
    variances = []
    for cat, scores in task_scores.items():
        if len(scores) > 1:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            variances.append((cat, variance, scores))
    
    return sorted(variances, key=lambda x: x[1], reverse=True)[:top_n]


def detect_regressions(results: list[dict], threshold: float = 0.10) -> list[dict]:
    """Detect dimensions with >threshold drop between consecutive runs."""
    regressions = []
    sorted_results = sorted(results, key=lambda x: x.get("timestamp", ""))
    
    for i in range(1, len(sorted_results)):
        prev = sorted_results[i - 1]
        curr = sorted_results[i]
        
        for dim in prev.get("by_dimension", {}):
            prev_score = prev["by_dimension"][dim].get("overall_avg", 0)
            curr_score = curr["by_dimension"][dim].get("overall_avg", 0)
            
            if prev_score > 0 and (prev_score - curr_score) / prev_score > threshold:
                regressions.append({
                    "timestamp": curr.get("timestamp"),
                    "dimension": dim,
                    "previous": prev_score,
                    "current": curr_score,
                    "drop_pct": (prev_score - curr_score) / prev_score * 100
                })
    
    return regressions


def generate_report(results: list[dict], trends: dict, unstable: list, regressions: list) -> str:
    """Generate markdown report."""
    lines = [
        "# AEGIS Eval Analysis Report",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Period:** {results[0].get('timestamp', 'N/A')} to {results[-1].get('timestamp', 'N/A')}",
        f"**Total Runs:** {len(results)}",
        "",
        "## Dimension Trends (Latest vs First)",
    ]
    
    for dim, data in trends.items():
        if len(data) >= 2:
            first = data[0]["overall_avg"]
            last = data[-1]["overall_avg"]
            change = ((last - first) / first * 100) if first > 0 else 0
            lines.append(f"- **{dim}:** {first:.2f} → {last:.2f} ({change:+.1f}%)")
    
    lines.extend(["", "## Top 5 Unstable Categories"])
    if unstable:
        for cat, var, scores in unstable:
            lines.append(f"- {cat}: variance={var:.3f} (scores: {', '.join(f'{s:.2f}' for s in scores)})")
    else:
        lines.append("- No unstable categories detected")
    
    lines.extend(["", "## Regressions Detected (threshold: 10%)"])
    if regressions:
        for r in regressions:
            lines.append(f"- [{r['timestamp']}] {r['dimension']}: {r['previous']:.2f} → {r['current']:.2f} (-{r['drop_pct']:.1f}%)")
    else:
        lines.append("✅ No regressions detected")
    
    lines.extend(["", "## Pass Rate Evolution"])
    pass_rates = [(r.get("timestamp", "N/A"), r.get("pass_rate", 0)) for r in sorted(results, key=lambda x: x.get("timestamp", ""))]
    for ts, pr in pass_rates:
        lines.append(f"- {ts}: {pr*100:.1f}%")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze AEGIS eval results")
    parser.add_argument("--results-dir", default="aegis_eval/results", help="Directory with summary_*.json files")
    args = parser.parse_args()
    
    if not Path(args.results_dir).exists():
        print(f"ERROR: Directory {args.results_dir} does not exist")
        sys.exit(1)
    
    results = load_results(args.results_dir)
    
    # CHECKPOINT 6: Verificar dados carregados
    assert len(results) > 0, "Nenhum resultado carregado!"
    print(f"✓ Loaded {len(results)} results")
    
    trends = compute_trends(results)
    unstable = find_unstable_tasks(results)
    regressions = detect_regressions(results)
    
    # CHECKPOINT 7: Verificar tendências calculadas
    assert len(trends) > 0, "Nenhuma tendência calculada!"
    print(f"✓ Computed trends for {len(trends)} dimensions")
    
    report = generate_report(results, trends, unstable, regressions)
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    output_file = Path(args.results_dir) / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n📄 Report saved to: {output_file}")


if __name__ == "__main__":
    main()
```

### 2.3 Verificação Final

```bash
# CHECKPOINT 8: Script executa sem erros
python3 aegis_eval/analyze_results.py --results-dir aegis_eval/results/

# ESPERADO:
# ✓ Found X result files
n# ✓ Loaded X results
# ✓ Computed trends for 5 dimensions
# Tabela markdown com:
#   - Dimension Trends
#   - Top 5 Unstable Categories
#   - Regressions Detected
#   - Pass Rate Evolution
# 📄 Report saved to: aegis_eval/results/analysis_report_YYYYMMDD_HHMMSS.md

# CHECKPOINT 9: Ficheiro .md foi criado
ls -la aegis_eval/results/analysis_report_*.md | tail -1
# ESPERADO: Ficheiro .md recente (> 0 bytes)
```

---

## 🔧 PASSO 3: Adicionar Health Endpoint à API (SE NECESSÁRIO)

> **Só executar se CHECKPOINT 2a falhar (endpoint não existe ou não responde)**

### Implementação

No ficheiro `aegis_kg/api/app.py`, adicionar:

```python
@app.route('/api/health')
def health():
    """Health check endpoint — verifies Neo4j connectivity."""
    try:
        r = neo4j_requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        if r.status_code == 200:
            version = r.json().get('neo4j_version', 'unknown')
            return jsonify({
                "status": "healthy",
                "neo4j": "connected",
                "neo4j_version": version,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        return jsonify({
            "status": "degraded",
            "neo4j": f"HTTP {r.status_code}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "neo4j": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503
```

### Verificação Final

```bash
# CHECKPOINT 10: Health endpoint responde corretamente
curl -s http://localhost:5000/api/health | python3 -m json.tool

# ESPERADO (quando Neo4j OK):
# {
#   "status": "healthy",
#   "neo4j": "connected",
#   "neo4j_version": "5.x.x",
#   "timestamp": "2026-05-04T...Z"
# }

# CHECKPOINT 11: Health endpoint incluído no index
python3 -c "
import requests
r = requests.get('http://localhost:5000/')
assert 'GET /api/health' in r.text
print('OK: /api/health documentado no index')
"
```

---

## 🏃 PASSO 4: Criar Baseline de Performance (SEMPRE EXECUTAR)

> **Objetivo:** Correr eval completo (45 tasks × 3 trials = 135 runs) e guardar como referência.

### 4.1 Pré-condições

```bash
# CHECKPOINT 12: Verificar Neo4j
docker ps --format "table {{.Names}}\t{{.Status}}" | grep neo4j
# ESPERADO: d3fend-neo4j (healthy)

# CHECKPOINT 13: Verificar Ollama
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); assert any('ministral' in m['name'] for m in d['models']), 'ministral não encontrado'; print('OK: ministral-3 disponível')"

# CHECKPOINT 14: Verificar Minimax API key
python3 -c "import os; k=os.getenv('MINIMAX_API_KEY',''); assert len(k)>20, 'MINIMAX_API_KEY não configurada!'; print(f'OK: Key configurada ({len(k)} chars)')"

# CHECKPOINT 15: Smoke test (1 task, 1 trial, ~2 min)
cd /home/epmq/Desktop/Projects/aegis-kg-unified
source /home/epmq/Desktop/Projects/shared-venv/bin/activate
python3 aegis_eval/run_eval.py \
  --tasks aegis_eval/task_bank.yaml \
  --task list_all_regulations \
  --trials 1 \
  --verbose
# ESPERADO: [PASS] com scores, sem erros fatais
```

### 4.2 Execução Completa

```bash
# CHECKPOINT 16: Iniciar eval completo (4–6 horas)
cd /home/epmq/Desktop/Projects/aegis-kg-unified
source /home/epmq/Desktop/Projects/shared-venv/bin/activate

# Correr em background e guardar log
python3 aegis_eval/run_eval.py \
  --tasks aegis_eval/task_bank.yaml \
  --trials 3 \
  > baseline_run_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Guardar PID
echo $! > baseline.pid
echo "Baseline started with PID $(cat baseline.pid)"
```

### 4.3 Monitorização (durante execução)

```bash
# CHECKPOINT 17: Verificar progresso (correr periodicamente)
tail -20 baseline_run_*.log
# ESPERADO: Mensagens "[PASS]" ou "[WARN]" a aparecer regularmente
# Se ver "[FAIL]" em todas → investigar erro

# CHECKPOINT 18: Verificar se processo ainda corre
ps aux | grep run_eval | grep -v grep
# ESPERADO: Processo python3 ativo
```

### 4.4 Pós-processamento

```bash
# CHECKPOINT 19: Verificar que resultado foi gerado
latest_summary=$(ls -t aegis_eval/results/summary_task_bank_*.json | head -1)
latest_trials=$(ls -t aegis_eval/results/trials_task_bank_*.jsonl | head -1)
echo "Latest summary: $latest_summary"
echo "Latest trials: $latest_trials"
ls -la "$latest_summary"
# ESPERADO: Ficheiro recente, > 1KB

# CHECKPOINT 20: Copiar para baseline oficial
cp "$latest_summary" aegis_eval/results/baseline_v2.0.json
cp "$latest_trials" aegis_eval/results/baseline_v2.0_trials.jsonl
ls -la aegis_eval/results/baseline_v2.0*
# ESPERADO: Dois ficheiros baseline_v2.0* criados
```

### 4.5 Validação do Baseline

```bash
# CHECKPOINT 21: Verificar métricas do baseline
python3 -c "
import json
b = json.load(open('aegis_eval/results/baseline_v2.0.json'))

print('=== BASELINE VALIDATION ===')
print(f'Total trials: {b[\"total_trials\"]} (esperado: 135)')
assert b['total_trials'] == 135, f'Esperado 135 trials, got {b[\"total_trials\"]}'
print('✓ Total trials correto')

print(f'Pass rate: {b[\"pass_rate\"]*100:.1f}%')
assert b['pass_rate'] >= 0.6, f'Pass rate muito baixo: {b[\"pass_rate\"]*100:.1f}%'
print('✓ Pass rate >= 60%')

for dim, scores in b['by_dimension'].items():
    avg = scores['overall_avg']
    status = '✅' if avg >= 3.0 else '⚠️'
    print(f'{status} {dim}: {avg:.2f}')
    assert avg >= 2.0, f'{dim} muito baixo: {avg}'

latency = b['avg_latency_ms']['total'] / 1000
status = '✅' if latency < 30 else '⚠️'
print(f'{status} Avg latency: {latency:.1f}s')
assert latency < 60, f'Latência excessiva: {latency}s'

print('\n🎉 Baseline válido!')
"

# ESPERADO: Todas as assertivas passam, "Baseline válido!"
```

---

## 📋 CHECKLIST FINAL

Após completar todos os passos aplicáveis, verificar:

| # | Verificação | Comando | Esperado |
|---|-------------|---------|----------|
| 1 | schema_context sem hífens | `rg "D-\d{2}-" aegis_eval/schema_context.py \| wc -l` | 0 |
| 2 | schema_context com pontos | `python3 -c "from aegis_eval.schema_context import SCHEMA_DESCRIPTION; assert 'D-01.1' in SCHEMA_DESCRIPTION"` | sucesso |
| 3 | analyze_results.py existe | `ls aegis_eval/analyze_results.py` | ficheiro existe |
| 4 | analyze_results.py funciona | `python3 aegis_eval/analyze_results.py --results-dir aegis_eval/results/ \| head -5` | "Found X result files" |
| 5 | Report gerado | `ls aegis_eval/results/analysis_report_*.md` | ficheiro existe |
| 6 | Health endpoint OK (se aplicável) | `curl -s http://localhost:5000/api/health \| grep healthy` | "healthy" |
| 7 | Baseline existe | `ls aegis_eval/results/baseline_v2.0.json` | ficheiro existe |
| 8 | Baseline tem 135 trials | `python3 -c "import json; print(json.load(open('aegis_eval/results/baseline_v2.0.json'))['total_trials'])"` | 135 |
| 9 | Baseline pass rate OK | `python3 -c "import json; print(json.load(open('aegis_eval/results/baseline_v2.0.json'))['pass_rate'])"` | > 0.6 |

---

## 🚨 NOTAS IMPORTANTES PARA O AGENTE

1. **Sempre começar pelo PASSO 0** — pode poupar horas de trabalho se Passos 1 e 3 já estiverem feitos.

2. **Passo 2 (Baseline) demora 4–6 horas** — não bloquear o terminal. Correr em background ou agendar.

3. **Se algum CHECKPOINT falhar** — parar, investigar, corrigir, só depois continuar. Não ignorar falhas.

4. **Documentar erros inesperados** em `MEMORY.md` ou `SETUP_STATE.md`.

5. **Nunca commitar secrets** — `.env` está no `.gitignore`, manter assim.

6. **Verificar 2x antes de dizer "está feito"** — usar os CHECKPOINTS para confirmar.

---

## 📞 EM CASO DE DÚVIDA

- Verificar `AGENTS.md` v2.1 — referência canónica do projeto
- Verificar `MEMORY.md` — log de erros e soluções
- Verificar `KG_MANIFEST.md` — estado atual do grafo Neo4j
