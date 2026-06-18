from __future__ import annotations

import json
import subprocess
import sys
import os

from pathlib import Path
from datetime import datetime
from groq import Groq


def encontrar_ultimo_trace(traces_dir: Path) -> list | None:
    """
    Lê o trace mais recente do canary.
    """

    arquivos = sorted(
        traces_dir.glob("canary_*.json"),
        reverse=True
    )

    if not arquivos:
        return None

    return json.loads(
        arquivos[0].read_text(
            encoding="utf-8"
        )
    )


def detectar_necessidade_rollback(trace: list) -> tuple[bool, dict]:
    """
    Verifica se alguma fase ultrapassou os thresholds.
    """

    THRESHOLD_CPU = 80
    THRESHOLD_MEMORIA = 85
    THRESHOLD_ERRO = 5.0
    THRESHOLD_LATENCIA = 800

    for fase in trace:

        if (
            fase.get("cpu_pct", 0) >= THRESHOLD_CPU
            or fase.get("memory_pct", 0) >= THRESHOLD_MEMORIA
            or fase.get("error_rate_pct", 0) >= THRESHOLD_ERRO
            or fase.get("latency_ms", 0) >= THRESHOLD_LATENCIA
        ):
            return True, fase

    fases_aprovadas = [
        f["percentual_trafego"]
        for f in trace
        if f.get("fase_aprovada")
    ]

    if 100 not in fases_aprovadas:
        return True, trace[-1] if trace else {}

    return False, {}


def executar_rollback_simulado(
    versao_anterior: str = "v1.0.0"
) -> str:
    """
    Simula rollback.
    """

    print(
        f"\nExecutando rollback para {versao_anterior}..."
    )

    timestamp = datetime.now().isoformat()

    print(
        f"✓ Rollback concluído em {timestamp}"
    )

    return timestamp


def gerar_relatorio_ia(
    trace: list,
    metricas_falha: dict,
    timestamp_rollback: str
) -> str:
    """
    Gera relatório usando Groq.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return (
            "GROQ_API_KEY não encontrada. "
            "Não foi possível gerar relatório com IA."
        )

    client = Groq(api_key=api_key)

    prompt = f"""
Você é um engenheiro SRE (Site Reliability Engineer).

Analise o incidente abaixo e produza um relatório técnico.

TRACE DO CANARY:

{json.dumps(trace, indent=2, ensure_ascii=False)}

FASE QUE GEROU O ROLLBACK:

{json.dumps(metricas_falha, indent=2, ensure_ascii=False)}

ROLLBACK EXECUTADO EM:

{timestamp_rollback}

Escreva em português.

Estruture em:

1. Resumo do incidente
2. Causa identificada
3. Impacto estimado
4. Ação tomada
5. Recomendações

Máximo de 300 palavras.
"""

    resposta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_completion_tokens=600,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return resposta.choices[0].message.content


def abrir_issue_github(
    titulo: str,
    corpo: str,
    labels: list = None
):
    """
    Cria Issue usando gh CLI.
    """

    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        titulo,
        "--body",
        corpo
    ]

    if labels:
        for label in labels:
            cmd.extend(
                [
                    "--label",
                    label
                ]
            )

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:

            print(
                f"✓ Issue criado: "
                f"{result.stdout.strip()}"
            )

        else:

            print(
                "\n✗ gh CLI não disponível "
                "ou não autenticado."
            )

            print(
                "\n--- ISSUE QUE SERIA CRIADA ---\n"
            )

            print(f"Título: {titulo}")
            print()
            print(corpo)

    except FileNotFoundError:

        print(
            "\n✗ gh CLI não encontrado."
        )

        print(
            "\n--- ISSUE QUE SERIA CRIADA ---\n"
        )

        print(f"Título: {titulo}")
        print()
        print(corpo)


def main():

    raiz = Path(__file__).parent.parent

    traces_dir = raiz / "traces"

    print(
        "\n=== ROLLBACK TRIGGER ===\n"
    )

    trace = encontrar_ultimo_trace(
        traces_dir
    )

    if not trace:

        print(
            "Nenhum trace encontrado."
        )

        sys.exit(0)

    precisa_rollback, metricas_falha = (
        detectar_necessidade_rollback(trace)
    )

    if not precisa_rollback:

        print(
            "✓ Deploy estável."
        )

        print(
            "✓ Rollback não necessário."
        )

        sys.exit(0)

    print(
        f"✗ Problema detectado "
        f"na fase "
        f"{metricas_falha.get('percentual_trafego')}%"
    )

    print(
        f"CPU: "
        f"{metricas_falha.get('cpu_pct')}%"
    )

    print(
        f"Memória: "
        f"{metricas_falha.get('memory_pct')}%"
    )

    print(
        f"Error Rate: "
        f"{metricas_falha.get('error_rate_pct')}%"
    )

    print(
        f"Latência: "
        f"{metricas_falha.get('latency_ms')}ms"
    )

    # 1. Rollback

    timestamp_rollback = (
        executar_rollback_simulado()
    )

    # 2. IA

    print(
        "\nGerando relatório com IA..."
    )

    relatorio = gerar_relatorio_ia(
        trace,
        metricas_falha,
        timestamp_rollback
    )

    print(
        "\n--- RELATÓRIO GERADO ---\n"
    )

    print(relatorio)

    # 3. GitHub Issue

    titulo = (
        "[ROLLBACK] Deploy falhou em "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} "
        f"- Fase "
        f"{metricas_falha.get('percentual_trafego')}%"
    )

    corpo = f"""
## Rollback Automático

{relatorio}

---

Relatório gerado automaticamente pelo pipeline DevOps + IA.
"""

    abrir_issue_github(
        titulo=titulo,
        corpo=corpo,
        labels=[
            "bug",
            "rollback",
            "automated"
        ]
    )

    sys.exit(1)


if __name__ == "__main__":
    main()
