from app.configs import load_config


def load_import_profiles() -> dict:
    cfg = load_config("import_profiles")
    return cfg["profiles"]
