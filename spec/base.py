from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any, Optional, Sequence
import yaml
import yaml.constructor
import yaml.nodes

if TYPE_CHECKING:
    from IPython.lib.pretty import RepresentationPrinter


class Loader(yaml.SafeLoader):
    pass


class YamlObject:
    def __init_subclass__(
        cls,
        yamltag: Optional[str] = None,
        yamltags: Sequence[str] = [],
        path_resolver: Optional[Sequence] = None,
        path_resolvers: Sequence[Sequence] = [],
        **kwargs,
    ):
        yamltags = list(yamltags)
        if yamltag is not None:
            yamltags.insert(0, yamltag)
        for t in yamltags:
            Loader.add_constructor(t, cls._constructor)

        path_resolvers = list(path_resolvers)
        if path_resolver is not None:
            path_resolvers.append(path_resolver)
        if path_resolvers and not yamltags:
            raise ValueError("Cannot have path_resolver with no yamltag")
        for p in path_resolvers:
            Loader.add_path_resolver(yamltags[0], p)

    def __init__(self, **kwargs):
        pass

    def _pretty_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k[0] != "_"}

    def _repr_pretty_(self, p: RepresentationPrinter, cycle: bool):
        p.text(type(self).__name__)
        if cycle:
            p.text("{...}")
            return
        with p.group(2, "{", "}"):
            for i, (k, v) in enumerate(self._pretty_dict().items()):
                if i:
                    p.text(",")
                    p.breakable()
                p.text(str(k))
                p.text(": ")
                p.pretty(v)

    @classmethod
    def _constructor(
        cls,
        constructor: yaml.constructor.BaseConstructor,
        node: yaml.nodes.Node,
    ):
        if isinstance(node, yaml.nodes.MappingNode):
            value: dict = constructor.construct_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(
                None, None,
                "expected a mapping node, but found %s" % node.id,
                node.start_mark)
        o = cls.__new__(cls)
        yield o
        o.__init__(**value)


class YamlScalar(YamlObject):
    def __init__(self, data: str):
        pass

    @classmethod
    def _constructor(
        cls,
        constructor: yaml.constructor.BaseConstructor,
        node: yaml.nodes.Node,
    ):
        if isinstance(node, yaml.nodes.ScalarNode):
            value: str = str(constructor.construct_scalar(node))
        else:
            raise yaml.constructor.ConstructorError(
                None, None,
                "expected a scalar node, but found %s" % node.id,
                node.start_mark)
        o = cls.__new__(cls)
        yield o
        o.__init__(value)


def load(stream: str | bytes | IO) -> Any:
    return yaml.load(stream, Loader=Loader)
