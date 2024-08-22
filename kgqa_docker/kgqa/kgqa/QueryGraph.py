import abc
from dataclasses import dataclass, field
from typing import Dict, List, Union

import graphviz

from kgqa.kgqa.MatchingUtils import compute_similar_entities, compute_similar_properties
from kgqa.kgqa.QueryParser import (
    Aggregation,
    AggregationType,
    ArgumentType,
    Constant,
    IDConstant,
    ParsedQuery,
    FilterOp,
    StringConstant,
    Variable,
)


@dataclass
class QueryGraphId:
    value: int

    def __repr__(self) -> str:
        return f"GID({self.value})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, QueryGraphId):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


class QueryGraphIdGenerator:
    _current_id: int = 0

    def __call__(self):
        id_ = self._current_id
        self._current_id += 1
        return QueryGraphId(value=id_)


@dataclass
class QueryGraphNode:
    id_: QueryGraphId

    def is_qualifier(self):
        return False

    def mark_executable(self):
        pass


@dataclass
class QueryGraphPropertyNode(QueryGraphNode):
    property: str

    pids: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)

    def mark_executable(self):
        self.pids, self.scores = compute_similar_properties(self.property)

    def score(self, pid):
        return self.scores[self.pids.index(pid)]

    def __eq__(self, other):
        if not isinstance(other, QueryGraphPropertyNode):
            return False
        return self.id_ == other.id_

    def __hash__(self):
        return hash(self.id_.value)


@dataclass
class QueryGraphVariableNode(QueryGraphNode):
    variable: Variable

    def is_qualifier(self):
        return self.variable.type_info() == "qualifier"


@dataclass
class QueryGraphConstantNode(QueryGraphNode):
    constant: Constant


@dataclass
class QueryGraphEntityConstantNode(QueryGraphConstantNode):
    constant: StringConstant

    qids: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)

    def mark_executable(self):
        self.qids, self.scores = compute_similar_entities(self.constant.value)

    def score(self, qid):
        return self.scores[self.qids.index(qid)]


@dataclass
class QueryGraphPropertyConstantNode(QueryGraphConstantNode):
    constant: IDConstant

    pids: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)

    def mark_executable(self):
        self.pids, self.scores = [self.constant.value], [1.0]


@dataclass
class QueryGraphGeneratedNode(QueryGraphNode):
    pass


@dataclass
class QueryGraphEdge(abc.ABC):
    source: QueryGraphNode
    target: QueryGraphNode

    def mark_executable(self):
        pass


QueryGraphPropertyEdgeType = Union[
    QueryGraphPropertyNode, QueryGraphPropertyConstantNode
]


@dataclass
class QueryGraphPropertyEdge(QueryGraphEdge):
    property: QueryGraphPropertyEdgeType
    qualifier: bool

    def __init__(
        self,
        source: QueryGraphNode,
        target: QueryGraphNode,
        property: QueryGraphPropertyEdgeType,
        qualifier: bool = False,
    ):
        self.property = property
        self.qualifier = qualifier
        super().__init__(source, target)

    def is_qualifier(self):
        return self.qualifier


@dataclass
class QueryGraphFilter(QueryGraphEdge):
    op: FilterOp


@dataclass
class QueryGraphAggregate(QueryGraphEdge):
    source: QueryGraphVariableNode
    target: QueryGraphGeneratedNode

    type_: AggregationType
    distinct: bool = False


@dataclass
class ColumnInfo(abc.ABC):
    node: QueryGraphNode

    @abc.abstractmethod
    def __repr__(self) -> str:
        """
        Constructs a serializable name for the column.
        """
        pass

    def __hash__(self):
        return hash(self.node.id_.value)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.node.id_ == other.node.id_


@dataclass
class EntityColumnInfo(ColumnInfo):
    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class VirtualEntityColumnInfo(EntityColumnInfo):
    node: QueryGraphVariableNode

    def __repr__(self) -> str:
        return f"virtual::{self.node.variable.name}"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class HeadVariableColumnInfo(EntityColumnInfo):
    node: QueryGraphVariableNode

    def __repr__(self) -> str:
        return self.node.variable.name

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class AnchorEntityColumnInfo(EntityColumnInfo):
    node: QueryGraphConstantNode

    def __repr__(self) -> str:
        assert isinstance(self.node.constant, StringConstant)
        return f"{self.node.constant.value} (QID)"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class PropertyColumnInfo(ColumnInfo):
    node: QueryGraphPropertyNode

    def __repr__(self) -> str:
        return f"{self.node.property} (PID)"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class AggregateColumnInfo(ColumnInfo):
    aggregate: QueryGraphAggregate

    def __init__(self, aggregate: QueryGraphAggregate):
        self.aggregate = aggregate
        super().__init__(self.aggregate.target)

    def __repr__(self) -> str:
        return f"{self.aggregate.type_.name}({self.aggregate.source.variable.name})"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        return super().__eq__(other)


@dataclass
class QueryGraph:
    query: ParsedQuery

    columns: List[ColumnInfo]

    # NOTE "virtual" columns, i.e., columns that will not appear as part of the result.
    #       This includes variables that exclusively appear as part of aggregates, etc.
    vcolumns: List[ColumnInfo]

    nodes: List[QueryGraphNode]
    edges: List[QueryGraphPropertyEdge]

    # NOTE Filters are simply a special kind of edge.
    #      As the backend uses them differently, we store them separately.
    filters: List[QueryGraphFilter]

    # NOTE Aggregates are simply a special kind of edge/node.
    #      As the backend uses them differently, we store them separately.
    aggregates: List[QueryGraphAggregate]

    executable: bool = False

    def is_executable(self):
        return self.executable

    def is_abstract(self):
        return not self.is_executable()

    def mark_executable(self):
        for node in self.nodes:
            node.mark_executable()

        for edge in self.edges:
            edge.mark_executable()

        self.executable = True


class QueryGraphSerializer:
    def __init__(self, qg: QueryGraph):
        self.qg = qg
        self.dot = None

    def serialize(self, save_graph=False):
        dot = graphviz.Digraph("serialized-query-graph")
        self._add_graph_nodes(dot)
        self._add_edges(dot)
        if save_graph:
            dot.render('./QirK/exploration/streamlit/graph', format='png', cleanup=True)
        return dot.source

    def _add_graph_nodes(self, dot):
        for node in self.qg.nodes:
            if isinstance(node, QueryGraphVariableNode):
                dot.node(self._node_id(node), f"Variable({node.variable.name})")
            elif isinstance(node, QueryGraphEntityConstantNode):
                dot.node(self._node_id(node), f'Entity("{node.constant.value}")')
            elif isinstance(node, QueryGraphPropertyNode):
                dot.node(self._node_id(node), f'Property("{node.property}")')
            elif isinstance(node, QueryGraphPropertyConstantNode):
                dot.node(self._node_id(node), f'Property("{node.constant.value}")')
            else:
                dot.node(self._node_id(node), f'Property("P31")')
                # print(node.__class__.__name__)
                # raise AssertionError

    def _add_edges(self, dot):
        for edge in self.qg.edges:
            dot.edge(self._node_id(edge.source), self._node_id(edge.property))
            dot.edge(self._node_id(edge.property), self._node_id(edge.target))

    def _node_id(self, node: QueryGraphNode) -> str:
        return str(node.id_.value)


def query2aqg(pq: ParsedQuery) -> QueryGraph:
    columns: List[ColumnInfo] = []
    vcolumns: List[ColumnInfo] = []
    nodes: List[QueryGraphNode] = []
    edges: List[QueryGraphPropertyEdge] = []
    filters: List[QueryGraphFilter] = []
    aggregates: List[QueryGraphAggregate] = []

    arg2node: Dict[ArgumentType, QueryGraphNode] = dict()
    new_id = QueryGraphIdGenerator()

    # NOTE Generate nodes/edges of the graph
    for clause in pq.clauses:
        for argument in clause.arguments:
            if isinstance(argument, Variable):
                if argument not in arg2node:
                    nodes.append(
                        QueryGraphVariableNode(
                            id_=new_id(),
                            variable=argument,
                        )
                    )
                    arg2node[argument] = nodes[-1]
            elif isinstance(argument, Constant):
                if argument not in arg2node:
                    if (
                        isinstance(argument, StringConstant)
                        and argument.type_info() == "entity_id"
                    ):
                        nodes.append(
                            QueryGraphEntityConstantNode(
                                id_=new_id(), constant=argument
                            )
                        )
                    else:
                        nodes.append(
                            QueryGraphConstantNode(id_=new_id(), constant=argument)
                        )
                    arg2node[argument] = nodes[-1]

                if (
                    isinstance(argument, StringConstant)
                    and argument.type_info() == "entity_id"
                ):
                    columns.append(AnchorEntityColumnInfo(node=arg2node[argument]))  # type: ignore
            else:
                assert False

        assert len(clause.arguments) == 2
        if clause.qualifier is not None:
            if clause.qualifier not in arg2node:
                nodes.append(
                    QueryGraphVariableNode(id_=new_id(), variable=clause.qualifier)
                )
                arg2node[clause.qualifier] = nodes[-1]
            if isinstance(clause.predicate, Variable):
                if clause.predicate not in arg2node:
                    nodes.append(
                        QueryGraphPropertyNode(
                            id_=new_id(), property=clause.predicate.name
                        )
                    )
                    arg2node[clause.predicate] = nodes[-1]
                    columns.append(PropertyColumnInfo(node=arg2node[clause.predicate]))  # type: ignore
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.arguments[0]],
                        target=arg2node[clause.qualifier],
                        property=arg2node[clause.predicate],  # type: ignore
                    )
                )
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.qualifier],
                        target=arg2node[clause.arguments[1]],
                        property=arg2node[clause.predicate],  # type: ignore
                    )
                )
            elif isinstance(clause.predicate, IDConstant):
                if clause.predicate not in arg2node:
                    nodes.append(
                        QueryGraphPropertyConstantNode(
                            id_=new_id(), constant=clause.predicate
                        )
                    )
                    arg2node[clause.predicate] = nodes[-1]
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.arguments[0]],
                        target=arg2node[clause.qualifier],
                        property=arg2node[clause.predicate],  # type: ignore
                    )
                )
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.qualifier],
                        target=arg2node[clause.arguments[1]],
                        property=arg2node[clause.predicate],  # type: ignore
                    )
                )
            else:
                assert False
        else:
            if isinstance(clause.predicate, Variable):
                if clause.predicate not in arg2node:
                    nodes.append(
                        QueryGraphPropertyNode(
                            id_=new_id(), property=clause.predicate.name
                        )
                    )
                    arg2node[clause.predicate] = nodes[-1]
                    columns.append(PropertyColumnInfo(node=arg2node[clause.predicate]))  # type: ignore
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.arguments[0]],
                        target=arg2node[clause.arguments[1]],
                        property=arg2node[clause.predicate],  # type: ignore
                        qualifier=clause.arguments[0].type_info() == "qualifier",
                    )
                )
            elif isinstance(clause.predicate, IDConstant):
                if clause.predicate not in arg2node:
                    nodes.append(
                        QueryGraphPropertyConstantNode(
                            id_=new_id(), constant=clause.predicate
                        )
                    )
                    arg2node[clause.predicate] = nodes[-1]
                edges.append(
                    QueryGraphPropertyEdge(
                        source=arg2node[clause.arguments[0]],
                        target=arg2node[clause.arguments[1]],
                        property=arg2node[clause.predicate],  # type: ignore
                        qualifier=clause.arguments[0].type_info() == "qualifier",
                    )
                )
            else:
                assert False

    # NOTE Generate filter edges of the graph
    for filter in pq.filters:
        # NOTE Otherwise, the variable(s) would be unbound
        assert filter.lhs in arg2node
        if isinstance(filter.rhs, Variable):
            assert filter.rhs in arg2node
        else:
            # NOTE Constants may be "unbound"
            if filter.rhs not in arg2node:
                nodes.append(QueryGraphConstantNode(id_=new_id(), constant=filter.rhs))
                arg2node[filter.rhs] = nodes[-1]

        filters.append(
            QueryGraphFilter(
                source=arg2node[filter.lhs], target=arg2node[filter.rhs], op=filter.op
            )
        )

    # NOTE Generate aggregation edges of the graph
    # OPTIMIZE We could de-duplicate aggregates.
    for item in pq.head:
        if isinstance(item, Aggregation):
            assert item.var in arg2node
            aggregate_node = QueryGraphGeneratedNode(id_=new_id())
            nodes.append(aggregate_node)
            aggregates.append(
                QueryGraphAggregate(
                    source=arg2node[item.var], target=aggregate_node, type_=item.type_  # type: ignore
                )
            )
            columns.append(AggregateColumnInfo(aggregate=aggregates[-1]))

    for item in pq.head:
        if isinstance(item, Variable):
            columns.append(HeadVariableColumnInfo(node=arg2node[item]))  # type: ignore

    for node in nodes:
        if isinstance(node, QueryGraphVariableNode):
            if node not in columns:
                vcolumns.append(VirtualEntityColumnInfo(node))

    graph = QueryGraph(
        query=pq,
        columns=columns,
        vcolumns=vcolumns,
        nodes=nodes,
        edges=edges,
        filters=filters,
        aggregates=aggregates,
    )

    assert graph.is_abstract()
    return graph


def aqg2wqg(aqg: QueryGraph) -> QueryGraph:
    aqg.mark_executable()
    return aqg
