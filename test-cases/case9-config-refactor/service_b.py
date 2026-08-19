"""Production API service — quiet by default, structured logging only."""
from config_loader import load_config

config = load_config("SERVICE_B")


def run():
    print(f"[service_b] starting with log_level={config.log_level}, workers={config.max_workers}")


if __name__ == "__main__":
    run()
