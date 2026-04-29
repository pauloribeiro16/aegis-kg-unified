#!/usr/bin/env python3
"""Script para continuar o setup do Langfuse. Uso: python scripts/continue_langfuse_setup.py"""

import subprocess
import sys
import time
import requests

PROJECT = "/home/epmq/Desktop/Projects/aegis-kg-unified"

def run(cmd, capture=False):
    print(f"  $ {cmd}")
    if capture:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT)
    subprocess.run(cmd, shell=True, cwd=PROJECT)

def main():
    print("=== Langfuse Setup Diagnostic ===")

    # 1. Check containers
    print("\n1. Estado dos containers:")
    run("docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep aegis", capture=True)

    # 2. Check ClickHouse
    print("\n2. Testar ClickHouse:")
    r = run('docker exec aegis-kg-unified-langfuse-clickhouse-1 clickhouse-client --query "SELECT 1"', capture=True)
    print(r.stdout.strip() if r.returncode == 0 else "ClickHouse não disponível")

    # 3. Testar rede do langfuse para clickhouse
    print("\n3. Testar rede interna:")
    r = run('docker exec aegis-kg-unified-langfuse-1 getent hosts langfuse-clickhouse 2>&1 || echo "Falhou"', capture=True)
    print(r.stdout.strip() if r.returncode == 0 else r.stdout)

    # 4. Testar connectivity clickhouse do langfuse
    print("\n4. Testar HTTP para clickhouse:")
    r = run('docker exec aegis-kg-unified-langfuse-1 wget -qO- http://langfuse-clickhouse:8123 2>&1 | head -5 || echo "HTTP falhou"', capture=True)
    print(r.stdout[:200] if r.returncode == 0 else "Não conectou")

    # 5. Ver logs langfuse
    print("\n5. Logs recentes do langfuse:")
    run("docker logs aegis-kg-unified-langfuse-1 --tail 5 2>&1", capture=True)

    print("\n=== Recomendações ===")
    print("Se step 3/4 falhou: problema de rede Docker")
    print("Se step 2 falhou: ClickHouse não está a funcionar")
    print("Se todos passaram mas langfuse não arranca: verificar variables de ambiente CLICKHOUSE_*")
    print("\nAlternativa: usar Langfuse Cloud em vez de self-hosted")

if __name__ == "__main__":
    main()
