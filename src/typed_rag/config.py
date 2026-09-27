"""Loading and validation of the experiment configuration.

Stage 1 keeps this deliberately small: a JSON file, a few required keys,
and path resolution relative to the project root.
Stage 2 adds the dataset section and the pilot size.
Stage 4 adds the LLM section (OpenAI Responses API settings); the API key is
never part of the configuration file.
Stage 5 adds the controller section (retry budget, policy version).
Stage 7 adds the pilot section (repeat count, branches, batch directories).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_RELPATH = Path("config") / "experiment.json"

# Keys expected under "paths"; each one becomes a working directory.
REQUIRED_PATH_KEYS = ("data_raw", "data_processed", "artifacts", "results")

REQUIRED_RETRIEVAL_KEYS = (
    "model_name",
    "model_revision",
    "index_dirname",
    "model_cache_dirname",
)

REQUIRED_LLM_KEYS = (
    "model",
    "temperature",
    "max_output_tokens",
    "timeout_seconds",
    "max_retries",
    "store",
)

REQUIRED_DATASET_KEYS = (
    "name",
    "split",
    "setting",
    "version",
    "filename",
    "processed_dirname",
    "url",
)


class ConfigError(Exception):
    """Raised when the configuration file is missing, malformed or incomplete."""


@dataclass(frozen=True)
class DatasetConfig:
    """Identity and download locations of the source dataset."""

    name: str
    split: str
    setting: str
    version: str
    filename: str
    processed_dirname: str
    url: str
    mirror_urls: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{self.name}/{self.split}/{self.setting}/{self.version}"


@dataclass(frozen=True)
class RetrievalConfig:
    """Embedding model identity and pilot retrieval parameters."""

    model_name: str
    model_revision: str
    index_dirname: str
    model_cache_dirname: str
    batch_size: int
    top_k: int


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI Responses API settings shared by the grader and the generator.

    Technical-check settings only; the parameters of the main experiment are
    fixed separately. The key itself comes from the environment or `.env`.
    """

    provider: str
    api: str
    model: str
    temperature: float
    max_output_tokens: int
    timeout_seconds: float
    max_retries: int
    store: bool
    prompts_dirname: str
    runs_dirname: str
    dry_runs_dirname: str
    api_key_env: str
    env_filename: str


@dataclass(frozen=True)
class ControllerConfig:
    """Branch-independent controller limits for stage 5."""

    max_search_retries: int
    policy_version: str
    runs_dirname: str
    dry_runs_dirname: str


DEFAULT_CONTROLLER = ControllerConfig(
    max_search_retries=1,
    policy_version="stage5-v1",
    runs_dirname="controlled_runs",
    dry_runs_dirname="controlled_dry_runs",
)


@dataclass(frozen=True)
class PilotConfig:
    """Design of the stage 7 technical pilot batch: repeats, branches, directories."""

    repeats: int
    branches: tuple[str, ...]
    plan_dirname: str
    runs_dirname: str
    dry_runs_dirname: str
    mock_runs_dirname: str


DEFAULT_PILOT = PilotConfig(
    repeats=5,
    branches=("A", "B", "C", "D"),
    plan_dirname="pilot_plan",
    runs_dirname="pilot_runs",
    dry_runs_dirname="pilot_dry_runs",
    mock_runs_dirname="pilot_mock_runs",
)


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated configuration with absolute, project-root-relative paths."""

    experiment_name: str
    seed: int
    pilot_size: int
    dataset: DatasetConfig
    retrieval: RetrievalConfig
    llm: LLMConfig
    project_root: Path
    config_path: Path
    paths: dict[str, Path]
    controller: ControllerConfig = DEFAULT_CONTROLLER
    pilot: PilotConfig = DEFAULT_PILOT

    def ensure_directories(self) -> list[Path]:
        """Create every configured working directory; return them in key order."""
        created = []
        for key in REQUIRED_PATH_KEYS:
            path = self.paths[key]
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
        return created

    @property
    def raw_dataset_path(self) -> Path:
        """Location of the downloaded source file."""
        return self.paths["data_raw"] / self.dataset.filename

    @property
    def index_dir(self) -> Path:
        """Directory holding the vector index."""
        return self.paths["artifacts"] / self.retrieval.index_dirname

    @property
    def model_cache_dir(self) -> Path:
        """Local cache for the embedding model."""
        return self.paths["artifacts"] / self.retrieval.model_cache_dirname

    @property
    def processed_dir(self) -> Path:
        """Directory holding the prepared files for this dataset."""
        return self.paths["data_processed"] / self.dataset.processed_dirname

    @property
    def prompts_dir(self) -> Path:
        """Directory with the LLM prompt text files."""
        return self.project_root / self.llm.prompts_dirname

    @property
    def rag_runs_dir(self) -> Path:
        """Directory receiving one sub-directory per real RAG run."""
        return self.paths["results"] / self.llm.runs_dirname

    @property
    def rag_dry_runs_dir(self) -> Path:
        """Directory for dry runs: prepared requests only, no API traffic."""
        return self.paths["results"] / self.llm.dry_runs_dirname

    @property
    def controlled_runs_dir(self) -> Path:
        """Directory receiving one sub-directory per real controlled run (stage 5)."""
        return self.paths["results"] / self.controller.runs_dirname

    @property
    def controlled_dry_runs_dir(self) -> Path:
        return self.paths["results"] / self.controller.dry_runs_dirname

    @property
    def pilot_plan_dir(self) -> Path:
        """Frozen plan and manifest of the stage 7 technical pilot."""
        return self.paths["results"] / self.pilot.plan_dirname

    @property
    def pilot_runs_dir(self) -> Path:
        """Real batch executions of the technical pilot, one sub-directory per plan."""
        return self.paths["results"] / self.pilot.runs_dirname

    @property
    def pilot_dry_runs_dir(self) -> Path:
        """Batch dry runs: plan validation and prepared requests, no API traffic."""
        return self.paths["results"] / self.pilot.dry_runs_dirname

    @property
    def pilot_mock_runs_dir(self) -> Path:
        """Batches executed with a fake transport (tests); never real results."""
        return self.paths["results"] / self.pilot.mock_runs_dirname

    @property
    def env_file_path(self) -> Path:
        """Location of the local `.env` file (never versioned, never printed)."""
        return self.project_root / self.llm.env_filename


def find_project_root(start: Path | None = None) -> Path:
    """Walk upwards from `start` until a directory containing pyproject.toml."""
    start = (start or Path(__file__)).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ConfigError(
        "Project root not found: no pyproject.toml above " f"{start}"
    )


def _require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Key '{label}' must be a non-empty string")
    return value.strip()


def _require_positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"Key '{label}' must be a positive integer")
    return value


def _parse_dataset(raw: object) -> DatasetConfig:
    if not isinstance(raw, dict):
        raise ConfigError("Key 'dataset' must be a JSON object")

    missing = [key for key in REQUIRED_DATASET_KEYS if key not in raw]
    if missing:
        raise ConfigError(f"Missing keys in 'dataset': {', '.join(missing)}")

    values = {key: _require_text(raw[key], f"dataset.{key}") for key in REQUIRED_DATASET_KEYS}

    filename = values["filename"]
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise ConfigError("Key 'dataset.filename' must be a plain file name")

    mirrors = raw.get("mirror_urls", [])
    if not isinstance(mirrors, list) or not all(isinstance(item, str) and item.strip() for item in mirrors):
        raise ConfigError("Key 'dataset.mirror_urls' must be a list of non-empty strings")

    return DatasetConfig(mirror_urls=tuple(item.strip() for item in mirrors), **values)


def _parse_retrieval(raw: object) -> RetrievalConfig:
    if not isinstance(raw, dict):
        raise ConfigError("Key 'retrieval' must be a JSON object")

    missing = [key for key in REQUIRED_RETRIEVAL_KEYS if key not in raw]
    if missing:
        raise ConfigError(f"Missing keys in 'retrieval': {', '.join(missing)}")

    values = {key: _require_text(raw[key], f"retrieval.{key}") for key in REQUIRED_RETRIEVAL_KEYS}

    revision = values["model_revision"]
    if revision in {"main", "master", "HEAD"}:
        raise ConfigError(
            "Key 'retrieval.model_revision' must pin a commit SHA, not a moving branch"
        )

    for key in ("index_dirname", "model_cache_dirname"):
        if "/" in values[key] or "\\" in values[key]:
            raise ConfigError(f"Key 'retrieval.{key}' must be a plain directory name")

    return RetrievalConfig(
        batch_size=_require_positive_int(raw.get("batch_size", 32), "retrieval.batch_size"),
        top_k=_require_positive_int(raw.get("top_k", 5), "retrieval.top_k"),
        **values,
    )


def _plain_name(value: str, label: str) -> str:
    if "/" in value or "\\" in value or value in {".", ".."}:
        raise ConfigError(f"Key '{label}' must be a plain file or directory name")
    return value


def _parse_llm(raw: object) -> LLMConfig:
    if not isinstance(raw, dict):
        raise ConfigError("Key 'llm' must be a JSON object")

    missing = [key for key in REQUIRED_LLM_KEYS if key not in raw]
    if missing:
        raise ConfigError(f"Missing keys in 'llm': {', '.join(missing)}")

    provider = _require_text(raw.get("provider", "openai"), "llm.provider")
    api = _require_text(raw.get("api", "responses"), "llm.api")
    if provider != "openai" or api != "responses":
        raise ConfigError("Only llm.provider='openai' with llm.api='responses' is supported")

    model = _require_text(raw["model"], "llm.model")

    temperature = raw["temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ConfigError("Key 'llm.temperature' must be a number")
    if not 0 <= temperature <= 2:
        raise ConfigError("Key 'llm.temperature' must lie in [0, 2]")

    timeout = raw["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("Key 'llm.timeout_seconds' must be a positive number")

    max_retries = raw["max_retries"]
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise ConfigError("Key 'llm.max_retries' must be a non-negative integer")

    store = raw["store"]
    if not isinstance(store, bool):
        raise ConfigError("Key 'llm.store' must be a boolean")

    return LLMConfig(
        provider=provider,
        api=api,
        model=model,
        temperature=float(temperature),
        max_output_tokens=_require_positive_int(raw["max_output_tokens"], "llm.max_output_tokens"),
        timeout_seconds=float(timeout),
        max_retries=max_retries,
        store=store,
        prompts_dirname=_plain_name(
            _require_text(raw.get("prompts_dirname", "prompts"), "llm.prompts_dirname"),
            "llm.prompts_dirname",
        ),
        runs_dirname=_plain_name(
            _require_text(raw.get("runs_dirname", "rag_runs"), "llm.runs_dirname"),
            "llm.runs_dirname",
        ),
        dry_runs_dirname=_plain_name(
            _require_text(raw.get("dry_runs_dirname", "rag_dry_runs"), "llm.dry_runs_dirname"),
            "llm.dry_runs_dirname",
        ),
        api_key_env=_require_text(raw.get("api_key_env", "OPENAI_API_KEY"), "llm.api_key_env"),
        env_filename=_plain_name(
            _require_text(raw.get("env_filename", ".env"), "llm.env_filename"),
            "llm.env_filename",
        ),
    )


def _parse_controller(raw: object) -> ControllerConfig:
    if raw is None:
        raise ConfigError("Missing key 'controller'")
    if not isinstance(raw, dict):
        raise ConfigError("Key 'controller' must be a JSON object")
    max_retries = raw.get("max_search_retries")
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise ConfigError("Key 'controller.max_search_retries' must be a non-negative integer")
    return ControllerConfig(
        max_search_retries=max_retries,
        policy_version=_require_text(raw.get("policy_version"), "controller.policy_version"),
        runs_dirname=_plain_name(
            _require_text(raw.get("runs_dirname", "controlled_runs"), "controller.runs_dirname"),
            "controller.runs_dirname",
        ),
        dry_runs_dirname=_plain_name(
            _require_text(
                raw.get("dry_runs_dirname", "controlled_dry_runs"), "controller.dry_runs_dirname"
            ),
            "controller.dry_runs_dirname",
        ),
    )


def _parse_pilot(raw: object) -> PilotConfig:
    if raw is None:
        return DEFAULT_PILOT
    if not isinstance(raw, dict):
        raise ConfigError("Key 'pilot' must be a JSON object")
    branches = raw.get("branches", list(DEFAULT_PILOT.branches))
    if (
        not isinstance(branches, list)
        or not branches
        or not all(isinstance(b, str) and b.strip() for b in branches)
        or len(set(branches)) != len(branches)
    ):
        raise ConfigError("Key 'pilot.branches' must be a non-empty list of distinct branch names")
    names = {}
    for key in ("plan_dirname", "runs_dirname", "dry_runs_dirname", "mock_runs_dirname"):
        names[key] = _plain_name(_require_text(raw.get(key, getattr(DEFAULT_PILOT, key)), f"pilot.{key}"), f"pilot.{key}")
    return PilotConfig(
        repeats=_require_positive_int(raw.get("repeats", DEFAULT_PILOT.repeats), "pilot.repeats"),
        branches=tuple(b.strip().upper() for b in branches),
        **names,
    )


def load_config(config_path: Path | None = None, project_root: Path | None = None) -> ExperimentConfig:
    """Read, validate and normalise the experiment configuration."""
    root = project_root or find_project_root()
    path = Path(config_path) if config_path else root / DEFAULT_CONFIG_RELPATH
    if not path.is_absolute():
        path = (root / path).resolve()

    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Configuration file is not valid JSON: {path} ({exc})") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Configuration root must be a JSON object: {path}")

    name = _require_text(raw.get("experiment_name"), "experiment_name")

    seed = raw.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError("Key 'seed' must be an integer")

    pilot_size = _require_positive_int(raw.get("pilot_size"), "pilot_size")
    dataset = _parse_dataset(raw.get("dataset"))
    retrieval = _parse_retrieval(raw.get("retrieval"))
    llm = _parse_llm(raw.get("llm"))
    controller = _parse_controller(raw.get("controller"))

    raw_paths = raw.get("paths")
    if not isinstance(raw_paths, dict):
        raise ConfigError("Key 'paths' must be a JSON object")

    missing = [key for key in REQUIRED_PATH_KEYS if key not in raw_paths]
    if missing:
        raise ConfigError(f"Missing path keys in 'paths': {', '.join(missing)}")

    paths: dict[str, Path] = {}
    for key in REQUIRED_PATH_KEYS:
        value = raw_paths[key]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"Path '{key}' must be a non-empty string")
        candidate = Path(value)
        if candidate.is_absolute():
            raise ConfigError(f"Path '{key}' must be relative to the project root: {value}")
        paths[key] = (root / candidate).resolve()

    return ExperimentConfig(
        experiment_name=name,
        seed=seed,
        pilot_size=pilot_size,
        dataset=dataset,
        retrieval=retrieval,
        llm=llm,
        project_root=root,
        config_path=path,
        paths=paths,
        controller=controller,
        pilot=_parse_pilot(raw.get("pilot")),
    )
