import abc
from dataclasses import dataclass, field

from kgqa.kgqa.QueryGraph import (
    ColumnInfo,
    QueryGraph,
    QueryGraphId,
)


@dataclass
class VariableEdgeOccurrence:
    edge_index: int
    is_subj: bool


@dataclass
class QueryString:
    value: str

    col2name: dict[ColumnInfo, str] = field(default_factory=dict)


class QueryBackend(abc.ABC):
    graph: QueryGraph
    col2name: dict[ColumnInfo, str]

    def __init__(self, wqg: QueryGraph):
        self.graph = wqg
        self.col2name = dict()

    @abc.abstractmethod
    def to_query(self, emit_labels: bool = False) -> QueryString:
        """
        Generates an executable query string through the QueryBackend.
        """
        pass

    def requires_filters(self) -> bool:
        return len(self.graph.filters) > 0

    def requires_aggregation(self) -> bool:
        return len(self.graph.aggregates) > 0

    def _column_by_node_id(self, node_id: QueryGraphId) -> ColumnInfo:
        for column in self.graph.columns:
            if column.node.id_ == node_id:
                return column

        for column in self.graph.vcolumns:
            if column.node.id_ == node_id:
                return column
        raise AssertionError("attempting to get column info for invalid node")
