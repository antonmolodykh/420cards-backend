from pathlib import Path

import dynaconf

root_path = Path(__file__).parent / "configs"

print(root_path)

config = dynaconf.Dynaconf(
    environments=True,
    settings_files=[
        root_path / "default.toml",
        root_path / "local.toml",
        root_path / "test.toml",
    ],
    load_dotenv=True,
    merge_enabled=True,
)
