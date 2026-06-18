import json
import sys
from pathlib import Path

from groq import Groq


def carregar_contexto(raiz: Path) -> dict:
    """
    Lê os artefatos gerados pelos testes.
    """
    contexto = {}

    coverage_path = raiz / "coverage.json"

    if coverage_path.exists():
        dados = json.loads(coverage_path.read_text(encoding="utf-8"))
        contexto["cobertura_pct"] = (
            dados.get("totals", {})
            .get("percent_covered", 0)
        )
    else:
        contexto["cobertura_pct"] = 0

    log_path = raiz / "logs"

    if log_path.exists():
        logs = []

        for arquivo in log_path.glob("*.log"):
            try:
                conteudo = arquivo.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                logs.append(
                    f"Arquivo: {arquivo.name}\n"
                    f"{conteudo[:500]}"
                )

            except Exception as e:
                logs.append(
                    f"Erro ao ler {arquivo.name}: {str(e)}"
                )

        contexto["logs"] = (
            "\n\n------------------\n\n".join(logs)
            if logs
            else "sem logs"
        )

    else:
        contexto["logs"] = "sem logs"

    return contexto


def rodar_deploy_gate(raiz: Path) -> str:
    """
    Consulta um modelo hospedado no Groq e
    retorna APPROVE ou BLOCK.
    """

    ctx = carregar_contexto(raiz)

    prompt = f"""
Você é um engenheiro DevOps sênior.

Sua tarefa é decidir se um build pode ser promovido para deploy.

REGRAS OBRIGATÓRIAS:

1. Se a cobertura de testes for menor que 80%, responda BLOCK.
2. Se os logs indicarem falhas críticas, exceções graves ou erros recorrentes, responda BLOCK.
3. Caso contrário, responda APPROVE.

Dados do build:

Cobertura de testes:
{ctx['cobertura_pct']:.1f}%

Logs:

{ctx['logs']}

Retorne APENAS um JSON válido.

Formato obrigatório:

{{
  "decision": "APPROVE",
  "reason": "explicação curta",
  "risk_score": 10
}}

ou

{{
  "decision": "BLOCK",
  "reason": "explicação curta",
  "risk_score": 90
}}
"""

    client = Groq()

    print("\n===== PROMPT ENVIADO =====")
    print(prompt)
    print("==========================\n")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_completion_tokens=256,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    texto = response.choices[0].message.content.strip()

    # Remove possíveis blocos markdown
    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")
    texto = texto.strip()

    try:
        resultado = json.loads(texto)

    except json.JSONDecodeError:
        print("\n[Deploy Gate] Erro ao interpretar resposta do modelo:")
        print(texto)

        return "BLOCK"

    print("\n===== DEPLOY GATE =====")
    print(f"Decision : {resultado['decision']}")
    print(f"Reason   : {resultado['reason']}")
    print(f"Risk     : {resultado['risk_score']}/100")
    print("=======================\n")

    return resultado["decision"]


if __name__ == "__main__":

    raiz = Path(__file__).parent.parent

    decisao = rodar_deploy_gate(raiz)

    # 0 = sucesso
    # 1 = falha
    sys.exit(0 if decisao == "APPROVE" else 1)