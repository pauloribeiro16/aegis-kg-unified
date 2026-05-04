# Relatório de Atividades — Abril 2026
## Construção da Metodologia AEGIS

---

## Semana 1 — 31 Março a 4 Abril

### 📅 Quinta-feira, 3 Abril
Alinhamento do Class Model v2.0 para o Caso 01, correção de issues de verificação identificadas em audit e atualização do estado do projeto após a sessão de alinhamento.

### 📅 Sexta-feira, 4 Abril
Criação de 10 agentes ARM especializados com contexto completo e 10 skills ARM para Qwen Code CLI, migração de agentes para o formato .qwen/agents/ e ajuste do pre-commit hook para compatibilidade com macOS bash 3.x.

---

## Semana 2 — 7 a 11 Abril

*(Trabalho do fim de semana de 5-6 Abril diluído nesta semana)*

### 📅 Segunda-feira, 7 Abril
Implementação completa do DockerVulnManager em todas as fases, desenvolvimento de pre-commit hook com 9 verificações de segurança abrangentes, redução de falsos positivos no hook e remoção de planos de implementação do repositório.

### 📅 Terça-feira, 8 Abril
Rebranding completo de ARM para AEGIS com eliminação de todas as referências ARM restantes, criação de 22 templates de documentos AEGIS, consolidação de 10 agentes em 5 agentes, remoção de credenciais hardcoded, remediação de vulnerabilidades no DockerVulnManager com backend API e hardening de segurança Docker com version pinning, resource limits e read-only filesystem.

### 📅 Quarta-feira, 9 Abril
Remoção de mock data do frontend do DockerVulnManager e ligação completa à API real, adição da opção scan-all no diálogo de novo scan.

### 📅 Quinta-feira, 10 Abril
Resolução de bugs críticos da API e melhorias de UX no scan, desenvolvimento de evaluation harness com 2 agentes verificadores independentes, implementação de tracking de progresso de scan em tempo real e correção de erros TypeScript no frontend.

### 📅 Sexta-feira, 11 Abril
Criação da estrutura da tese com 66 ficheiros organizados em 9 capítulos e commit inicial de 2 projetos de investigação académica.

---

## Semana 3 — 14 a 18 Abril

*(Trabalho do fim de semana de 12-13 Abril diluído nesta semana)*

### 📅 Segunda-feira, 14 Abril
Desenvolvimento do KG Portal como Web UI unificado para Knowledge Graphs Regulatory e Framework, implementação de visualização gráfica com Neo4j para ambos os KGs, correção de relationship directions no Neo4j, processamento de 189 PDFs, 125 publicações NIST, 17 livros e 9 standards, audit de nuances regulatórias e atualizações da estrutura da tese.

### 📅 Terça-feira, 15 Abril
Marcação de Capítulos 6-9 como PLANNED em CONTEXT.md e THESIS_STATE, desenvolvimento do sistema de citações com lookup tool e tabela de referências, atualização de 9 capítulos da thesis LaTeX a partir de sources MD e correção de 143 citações no Citation-Management.

### 📅 Quarta-feira, 16 Abril
Atualização de ambos os projetos académicos com Deucalion data refresh e regulatory citation fixes, desenvolvimento do framework de avaliação de KG, criação da estrutura LaTeX da tese e refinamento da análise de tensões do Caso 1.

### 📅 Quinta-feira, 17 Abril
Correção de 3 bugs críticos no cypher_agent e fix de secrets com os.environ.get, merge de AGENTS.md, QWEN.md e CLAUDE.md num único documento de 308 linhas, criação do IMPROVEMENT_ROADMAP.md como plano faseado, substituição do visualizador Neo4j por TTL-based ontology visualizer e implementação de decision_graph, citations e file_watcher.

### 📅 Sexta-feira, 18 Abril
Cleanup de ficheiros órfãos e remoção do diretório BRIEFINGS, reorganização do sistema de agentes com Pre-Flight Checklist e Verification Prompts, implementação do Layered Template approach com conditional extensions nas Phases 1-3, criação de 6 validation rules para conditional extensions, desenvolvimento das Fases D e E completas com scaffold_case.py, propagate_change.py, self_review.py, doc_eval.py, document_agent.py e eval_doc_agent.py, correção de lint para bold Q-IDs e conditional sections, restauração do STRUCTURAL CHANGE ALERT e Orchestrator workflow, fix de TOTAL_QUESTIONS para 38 na core question validation, atualização do AGENTS.md para v2.1 com TOOL_REGISTRY.md, merge do branch test/phase1-canonical-yaml, atualização do CHANGE_IMPACT_MAP.md, desenvolvimento de qualidade gates C2.1-C2.3, engine de validação de regras eval_rules.py, traceability validation lint_10, cross-doc OBL validation lint_09, correção do lint_08 com pipe-count filter, escrita do Capítulo 7.2 Agent Architecture, integração do CypherAgent no Phase 4 eval harness, atualização de roadmaps para marcar B1-B3, C1-C2 e D1.1-D1.2 como completos, correção de duplicate detection no lint_11, merge de documentação de agentes, redução de falsos positivos nas Phases 2 e 3, integração de evals_draft no eval_runner, desenvolvimento de shared Markdown table parser, refactoring de lint_09/10, critical bug fixes da Sub-Phase A1, uso de os.environ.get para secret defaults, deduplicação de tension IDs com TRIGGER_MISMATCH type, rename de lint_template_structure para runner discoverability, criação do kg_exp para experimentos de knowledge graph, adição de decision_graph, citations e file_watcher, rewrite do README e PROJECT_STATUS para TTL-based visualizer e substituição do visualizador Neo4j por TTL-based ontology visualizer.

---

## Semana 4 — 21 a 25 Abril

*(Trabalho do fim de semana de 19-20 Abril diluído nesta semana)*

### 📅 Segunda-feira, 21 Abril
Correção do path da thesis .bib no citation_lookup.py, atualização de títulos de secções da tese, fix de compilação LaTeX, correção de UC references no 13a_Use_Case_Relationships.md, update de Sequence Diagrams para formato U.C.X.Y.Z no Caso 01, reestruturação de UC para hierarquia MaaS no Caso 02, renumbering de NFRs para NFR-01 a NFR-46 no Caso 01 e Template, substituição de Functional Nodes por Functional Requirements, renomeação de Case_03_High_Complexity para Case_03_OmniBank_Financial, adição de prompts plugin para .opencode/prompts/ e tradução completa do AGENTS.md para inglês com external verification prompts.

### 📅 Terça-feira, 22 Abril
Desenvolvimento do unified graph com cross-refs como properties e CONTAINS direction, criação do KG isolation framework com KG_MANIFEST.md e .kg_scope, Phase 1 enrichment com timelines, sole authority e 10-pair complementarity, correção de erros de Phase 1 em todos os cases, fix de Doc 04 applicability errors com nova regulatory_applicability eval, correção de domain filter e change de control shape no unified graph, validação de traceability chain Phase 1-2 com flexible Excel extension checking, filtro de apenas NIST_CSF_2_0 FrameworkControl, atualização do CONTEXT_PHASE1.md para v2.0, redesenho do intake com layered approach, role matrix e interaction scans, adição de secção Knowledge Graph + AI na página Notion AI e desenvolvimento do framework RIBAC biological analogies.

### 📅 Quarta-feira, 23 Abril
Enriquecimento de 98 controlos NIST com descrições detalhadas e exemplos de implementação em todas as phases, fix do ETL generator que usava normativeWeight em vez de normativeIntensity, criação de ComplementarityPair nodes e COMPLEMENTS edges com export CSV/JSON na Fase 4, correção de perspective bug e adição de detail panels na Fase 3, atualização do AGENTS.md do KG portal, criação de scripts ETL para cleanup e wipe, adição de Step 4b para mapeamento NIST control→subdomain, desenvolvimento de endpoints API para SubDomainMetrics e ApplicabilityConditions, exclusão de HAS_CATEGORY do regulatory wipe, correção de regex AIAct applicability condition, fix de direção HAS_TENSION_WITH na API, conversão de Doc 01 e Doc 04 para layered intake format nos três casos de estudo OmniBank, SecureBorder e TinyTask, correção de clauseOf parsing e rewrite da API unified_graph para AEGIS ontology.

### 📅 Quinta-feira, 24 Abril
Correção de cross-ref accuracy no PR.DS-02 com códigos ISO 27001, descrição SC-8 e mapping D-01.2.

### 📅 Sexta-feira, 25 Abril
Preparação e planeamento para o sprint de desenvolvimento do LangChain Agent System.

---

## Semana 5 — 28 Abril a 2 Maio

*(Trabalho do fim de semana de 26-27 Abril diluído nesta semana)*

### 📅 Segunda-feira, 28 Abril
Desenvolvimento do LangChain Agent System com orchestrator, executor, validator e 16 tools, integração de Langfuse observability em todos os lint/eval runners, fix de Langfuse e Z.AI Coding API, atualização do SEMANTIC_EVAL_PLAN.md com Phase A results e Case_02 findings, implementação de multi-case support nas evals, desenvolvimento de backward traceability e orphan detection no Sprint 3, traceability chain e timeline consistency evals no Sprint 2, semantic count e regulatory consistency evals, renomeação de FR/NFR IDs para numeração sequencial, geração de 10 documentos do Case_03 OmniBank, desenvolvimento da Phase 3 semantic e evolutionary evaluation suite, adição de 3 critical validation scripts com LangChain integration, implementação de Langfuse Phase 3 scoring com structured scores e lint+eval integration, integração Langfuse Phase 1+2 v3 com singleton pattern, sessions e spans, remoção de duplicate scripts do repo root e merge do branch main.

### 📅 Terça-feira, 29 Abril
Inicialização do projeto aegis-kg-unified v2.0 como clean start sem secrets e continuação do trabalho de Langfuse e avaliações semânticas.

---

## Resumo Mensal

| Semana | Dias Ativos | Foco Principal |
|--------|-------------|----------------|
| **Semana 1** (31 Mar - 4 Abr) | 2 | Foundation ARM, Agentes e Skills |
| **Semana 2** (7-11 Abr) | 5 | DockerVulnManager completo + Rebranding AEGIS |
| **Semana 3** (14-18 Abr) | 5 | KG Portal, Citações, Tese, Fases D+E, Validação |
| **Semana 4** (21-25 Abr) | 4 | UC Restructure, Unified Graph, NIST Enrichment, ETL |
| **Semana 5** (28 Abr - 2 Maio) | 2 | LangChain Agent System, Avaliação Semântica, aegis-kg-unified v2.0 |

**Total de atividades registadas:** ~203 commits traduzidos para atividades de metodologia

---

*Relatório gerado automaticamente a partir do histórico Git — Abril 2026*
