from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Sentence:
    case_id: str
    sentence_id: int
    sentence_text: str
    start_char: int
    end_char: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Token:
    case_id: str
    sentence_id: int
    token_id: int
    token: str
    start_char: int
    end_char: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Entity:
    entity_id: str
    case_id: str
    sentence_id: int | None
    type: str
    original_span: str
    normalized_label: str
    start_char: int | None
    end_char: int | None
    attributes: dict[str, Any]
    rule_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
