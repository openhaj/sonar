from collections.abc import Iterator

class Node:
    def __iter__(self) -> Iterator[Node]: ...

class NodeVisitor:
    def visit(self, node: Node | None) -> None: ...
    def generic_visit(self, node: Node) -> None: ...

class FileAST(Node): ...
class FuncDecl(Node): ...

class Typedef(Node):
    name: str | None
    type: Node

class Struct(Node):
    name: str | None

class Union(Node):
    name: str | None

class Enumerator(Node):
    name: str

class EnumeratorList(Node):
    enumerators: list[Enumerator]

class Enum(Node):
    name: str | None
    values: EnumeratorList | None

class Decl(Node):
    name: str | None
    type: Node
