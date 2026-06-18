import time
import json
from pathlib import Path
from datetime import datetime


def carregar_metricas(arquivo: Path) -> dict:
    """
    Carrega as métricas geradas pela aplicação.
    """

    with open(arquivo, "r", encoding="utf-8") as f:
        dados = json.load(f)

    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_pct": dados["cpu"],
        "memory_pct": dados["memory"],
        "latency_ms": dados["latency_ms"],
        "error_rate_pct": dados["error_rate"]
    }


def avaliar_fase(metricas: dict) -> bool:
    """
    Retorna True se a fase passou nos thresholds.
    """

    THRESHOLD_CPU = 80
    THRESHOLD_MEMORIA = 85
    THRESHOLD_ERRO = 5.0
    THRESHOLD_LATENCIA = 800

    return (
        metricas["cpu_pct"] < THRESHOLD_CPU and
        metricas["memory_pct"] < THRESHOLD_MEMORIA and
        metricas["error_rate_pct"] < THRESHOLD_ERRO and
        metricas["latency_ms"] < THRESHOLD_LATENCIA
    )


def executar_canary(arquivo_metricas: Path, salvar_em: Path = None):

    fases = [10, 50, 100]
    historico = []

    print("\n=== CANARY DEPLOY INICIADO ===\n")

    for percentual in fases:

        print(f"→ Fase {percentual}%: aguardando estabilização...")
        time.sleep(1)

        metricas = carregar_metricas(arquivo_metricas)

        metricas["percentual_trafego"] = percentual

        passou = avaliar_fase(metricas)

        metricas["fase_aprovada"] = passou

        historico.append(metricas)

        status = "✓ OK" if passou else "✗ FALHA"

        print(
            f"   CPU: {metricas['cpu_pct']}% | "
            f"Memória: {metricas['memory_pct']}% | "
            f"Erro: {metricas['error_rate_pct']}% | "
            f"Latência: {metricas['latency_ms']}ms | "
            f"{status}"
        )

        if not passou:

            print(
                f"\n✗ Fase {percentual}% falhou nos thresholds."
            )

            print("✗ Rollback necessário.\n")

            if salvar_em:
                salvar_em.write_text(
                    json.dumps(historico, indent=2)
                )

            return False, historico

        print(
            f"   Fase {percentual}% aprovada. Avançando...\n"
        )

    print("✓ Deploy 100% concluído com sucesso.\n")

    if salvar_em:
        salvar_em.write_text(
            json.dumps(historico, indent=2)
        )

    return True, historico


if __name__ == "__main__":

    raiz = Path(__file__).parent.parent

    arquivo_metricas = raiz / "metrics" / "system-reprovado.json"

    if not arquivo_metricas.exists():
        print(
            f"Arquivo de métricas não encontrado: "
            f"{arquivo_metricas}"
        )
        exit(1)

    traces_dir = raiz / "traces"
    traces_dir.mkdir(exist_ok=True)

    saida = (
        traces_dir /
        f"canary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    sucesso, historico = executar_canary(
        arquivo_metricas=arquivo_metricas,
        salvar_em=saida
    )

    print(f"Trace salvo em: {saida}")

    import sys
    sys.exit(0 if sucesso else 1)