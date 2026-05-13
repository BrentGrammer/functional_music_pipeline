from dataclasses import dataclass, field
from typing import Callable

@dataclass(frozen=True)
class Base:
    name: str
    params_spec: str = field(default="default_spec", kw_only=True)

@dataclass(frozen=True)
class Sub(Base):
    transform: Callable

s = Sub("myname", lambda x: x)
print(s.name, s.params_spec, s.transform("worked"))
