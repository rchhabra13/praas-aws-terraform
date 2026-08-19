"""Local dev/debug service — runs interactively, verbose logging by default."""
from config_loader import load_config

config = load_config("SERVICE_A")


def run():
    print(f"[service_a] starting with log_level={config.log_level}, workers={config.max_workers}")


if __name__ == "__main__":
    run()
