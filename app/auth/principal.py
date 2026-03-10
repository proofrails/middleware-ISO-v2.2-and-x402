from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Principal:
    """Authenticated request principal.

    role:
      - public: no key
      - project: project-scoped
      - project_admin: project-scoped admin
      - admin: global admin
    """

    role: str = "public"
    project_id: Optional[str] = None
    api_key_id: Optional[str] = None

    @property
    def is_public(self) -> bool:
        return self.role == "public"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_project_scoped(self) -> bool:
        return self.project_id is not None
