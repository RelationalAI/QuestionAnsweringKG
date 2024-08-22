from enum import Enum, auto
from typing import Dict, List, Literal, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import re

from termcolor import colored

from kgqa.kgqa.QueryLexer import (
    AggregationFunction,
    Identifier,
    LiteralToken,
    NumericLiteral,
    QueryLexer,
    QueryLexerException,
    QuoteType,
    SourceLocation,
    StringLiteral,
    Token,
    TokenType,
)

PrimitiveType = Literal[
    "entity_id", "string", "date", "numeric", "coordinate", "qualifier"
]
PrimitiveTypes: List[PrimitiveType] = [
    "entity_id",
    "string",
    "date",
    "numeric",
    "coordinate",
    "qualifier",
]


class TypeInfo:
    _token: Token
    _options: Set[PrimitiveType]

    def __init__(self, token, *args):
        self._token = token
        if len(list(args)) == 0:
            self._options = set(PrimitiveTypes)
        else:
            self._options = set(list(args))

    def __call__(self) -> Optional[PrimitiveType]:
        if len(self._options) == 1:
            return next(iter(self._options))
        return None

    def can(self, type_) -> bool:
        return type_ in self._options

    def set(self, type_) -> bool:
        if type_ is None:
            return False
        if type_ not in self._options:
            raise QueryParserException(
                self._token,
                f"attempting to infer type {type_}, but expected ({' | '.join(self._options)})",
            )
        if len(self._options) == 1:
            return False
        self._options = set([type_])
        return True

    def erase(self, type_) -> bool:
        if type_ not in self._options:
            return False
        if len(self._options) == 0:
            raise QueryParserException(
                self._token, f"attempting to remove only valid type {self()}"
            )
        self._options.remove(type_)
        return True

    def try_set(self, type_) -> bool:
        if len(self._options) == 1:
            return False
        return self.set(type_)

    def __getattr__(self, type_) -> bool:
        return type_ in self._options


@dataclass
class Variable:
    token: Identifier
    name: str
    type_info: TypeInfo

    def __init__(self, token, name):
        self.token = token
        self.name = name
        self.type_info = TypeInfo(token)

    def source_name(self) -> str:
        return self.name

    def query_name(self) -> str:
        return self.name.replace("_", " ")

    def __repr__(self) -> str:
        if self.type_info() is None:
            return f"Variable({self.name})"
        return f"Variable({self.name} / {self.type_info()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Variable):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


@dataclass
class Constant:
    token: Union[LiteralToken, Identifier]
    type_info: TypeInfo


@dataclass
class StringConstant(Constant):
    token: StringLiteral
    value: str
    type_info: TypeInfo

    def __init__(self, token, value):
        if token.quote_type == QuoteType.SINGLE_QUOTE:
            self.type_info = TypeInfo(token, "string", "date")
        else:
            self.type_info = TypeInfo(token, "entity_id")
        super().__init__(token, self.type_info)
        self.token = token
        self.value = value

    def __repr__(self) -> str:
        if self.type_info() is None:
            return f"Constant('{self.value}')"
        return f"Constant('{self.value}' / {self.type_info()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, StringConstant):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def try_parse_date(self, explicit_cast=False):
        try:
            return datetime.strptime(self.value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        try:
            return datetime.strptime(self.value, "%Y-%m-%d")
        except ValueError:
            pass
        if not explicit_cast:
            return None
        try:
            return datetime.strptime(self.value, "%Y-%m")
        except ValueError:
            pass
        try:
            return datetime.strptime(self.value, "%Y")
        except ValueError:
            pass


@dataclass
class NumericConstant(Constant):
    token: NumericLiteral
    value: Union[int, float]

    def __init__(self, token, value):
        self.type_info = TypeInfo(token, "numeric", "date")
        super().__init__(token, self.type_info)
        self.token = token
        self.value = value

    def __repr__(self) -> str:
        if self.type_info() is None:
            return f"Constant({self.value})"
        return f"Constant({self.value} / {self.type_info()})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, NumericConstant):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


class AnnotationType(Enum):
    BANG = "!"
    OPT = "?"


@dataclass
class IDConstant(Constant):
    token: Identifier
    annotation: AnnotationType
    value: str

    def __init__(self, token, annotation, value):
        self.type_info = TypeInfo(token, "entity_id")
        super().__init__(token, self.type_info)
        self.token = token
        self.annotation = annotation
        self.value = value

    def source_name(self) -> str:
        return f"{self.annotation.value}{self.value}"

    def query_name(self) -> str:
        return self.source_name()

    def __repr__(self) -> str:
        return f"{self.annotation.value}IDConstant({self.value})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, IDConstant):
            return False
        return self.value == other.value and self.annotation == other.annotation

    def __hash__(self):
        return hash(self.source_name())


class AggregationType(Enum):
    COUNT = auto()
    SUM = auto()
    AVG = auto()
    MAX = auto()
    MIN = auto()


@dataclass
class Aggregation:
    token: AggregationFunction
    var: Variable
    type_: AggregationType

    def __repr__(self) -> str:
        return f"{self.type_.name}({self.var})"


HeadItem = Union[Variable, Aggregation]


@dataclass
class QueryHead:
    items: List[HeadItem] = field(default_factory=lambda: [])

    def vars(self) -> List[Variable]:
        """
        Returns a list of unique variables occuring in the head, ordered by occurence.
        """
        vars: List[Variable] = []
        for item in self.items:
            if isinstance(item, Variable):
                if item not in vars:
                    vars.append(item)
            else:
                assert isinstance(item, Aggregation)
                if item.var not in vars:
                    vars.append(item.var)
        return vars

    def __iter__(self):
        return self.items.__iter__()


@dataclass
class QueryAtom:
    pass


PredicateType = Union[IDConstant, Variable]
ArgumentType = Union[Variable, Constant]


@dataclass
class QueryClause(QueryAtom):
    # TODO(jlscheerer) Rename this to property.
    predicate: PredicateType

    arguments: List[ArgumentType]
    qualifier: Optional[Variable] = None

    def __repr__(self) -> str:
        prefix = str()
        if self.qualifier is not None:
            prefix = f"{self.qualifier} := "
        if isinstance(self.predicate, Variable):
            return f"{prefix}{self.predicate.name}({', '.join([str(arg) for arg in self.arguments])})"
        else:
            assert isinstance(self.predicate, IDConstant)
            return f"{prefix}{self.predicate}({', '.join([str(arg) for arg in self.arguments])}))"

    def is_qualifier_claim(self):
        return any([argument.type_info() == "qualifier" for argument in self.arguments])


class FilterOp(Enum):
    EQ = "="
    NEQ = "!="
    LE = "<"
    LEQ = "<="
    GE = ">"
    GEQ = ">="


@dataclass
class QueryFilter(QueryAtom):
    lhs: Variable
    op: FilterOp
    rhs: Union[Variable, Constant]

    def __repr__(self) -> str:
        return f"{self.lhs} {self.op.value} {self.rhs}"


@dataclass
class ParsedQuery:
    head: QueryHead

    clauses: List[QueryClause]
    filters: List[QueryFilter]

    def spo(self) -> List[Tuple[ArgumentType, PredicateType, ArgumentType]]:
        spo: List[Tuple[ArgumentType, PredicateType, ArgumentType]] = []
        for clause in self.clauses:
            if len(clause.arguments) != 2:
                raise AssertionError()
            spo.append((clause.arguments[0], clause.predicate, clause.arguments[1]))
        return spo

    def canonical(self) -> str:
        return f"{QuerySerializer(self)}"


class QueryParserException(Exception):
    def __init__(self, token: Token, error: str):
        self.token = token
        self.error = error


class QueryParserExceptionWithNote(Exception):
    def __init__(self, token: Token, error: str, note_token: Token, note: str):
        self.token = token
        self.error = error
        self.note_token = note_token
        self.note = note


class QuerySerializer:
    def __init__(self, pq: ParsedQuery):
        self.pq = pq

    def __str__(self):
        head = ", ".join([self._serialize_head_item(item) for item in self.pq.head])
        body = "; ".join(
            [self._serialize_clause(clause) for clause in self.pq.clauses]
            + [self._serialize_filter(filter) for filter in self.pq.filters]
        )
        return f"{head}: {body}"

    def _serialize_head_item(self, item):
        if isinstance(item, Variable):
            return self._serialize_var(item)
        assert isinstance(item, Aggregation)
        return f"{item.type_.name}({self._serialize_var(item.var)})"

    def _serialize_clause(self, clause: QueryClause):
        qprefix = str()
        if clause.qualifier is not None:
            qprefix = f"{colored(clause.qualifier.name, 'magenta')} {colored('/', 'light_grey')} {colored(clause.qualifier.type_info(), 'light_grey')} := "
        arguments = [
            self._serialize_var(argument)
            if isinstance(argument, Variable)
            else self._serialize_const(argument)
            for argument in clause.arguments
        ]
        return f"{qprefix}{clause.predicate.source_name()}({', '.join(arguments)})"

    def _serialize_filter(self, filter: QueryFilter):
        lhs = self._serialize_var(filter.lhs)
        rhs = (
            self._serialize_var(filter.rhs)
            if isinstance(filter.rhs, Variable)
            else self._serialize_const(filter.rhs)
        )
        return f"{lhs} {filter.op.value} {rhs}"

    def _serialize_var(self, var):
        return f"{colored(var.name, 'magenta')} {colored('/', 'light_grey')} {colored(var.type_info(), 'light_grey')}"

    def _serialize_const(self, const):
        value = str()
        if isinstance(const, StringConstant):
            value = colored(
                f"{const.token.quote_type.value}{const.value}{const.token.quote_type.value}",
                "yellow",
            )
        elif isinstance(const, NumericConstant):
            value = colored(f"{const.value}", "green")
        elif isinstance(const, IDConstant):
            value = colored(f"!{const.value}", "green")
        else:
            raise AssertionError
        return f"{value} {colored('/', 'light_grey')} {colored(const.type_info(), 'light_grey')}"


class QueryParser:
    _tokens: List[Token]
    _cursor: int
    _eof: int

    def parse(self, query: str, note_fn=None) -> ParsedQuery:
        self.note_fn = note_fn
        self._tokens = list(QueryLexer(query))
        self._cursor = 0
        self._eof = len(query)
        head = QueryHead()
        if self._check_contains_colon():
            head = self._parse_head()
        clauses, filters = self._parse_body()
        pq = ParsedQuery(head=head, clauses=clauses, filters=filters)
        if not self._validate_query(pq):
            raise AssertionError()
        pq = self._rewrite_query(pq)
        if not self._type_check_query(pq):
            raise AssertionError()

        pq = self._canonicalize_order(pq)
        return pq

    def _canonicalize_order(self, pq: ParsedQuery):
        clauses: List[QueryClause] = []
        for clause in pq.clauses:
            arguments = clause.arguments
            assert len(arguments) == 2
            if clause.is_qualifier_claim():
                if arguments[0].type_info() != "qualifier":
                    arguments = [arguments[0], arguments[1]]
            else:
                if arguments[0].type_info() != "entity_id":
                    arguments = [arguments[1], arguments[0]]
            clause.arguments = arguments
            clauses.append(clause)
        return ParsedQuery(head=pq.head, clauses=clauses, filters=pq.filters)

    def _type_check_query(self, pq: ParsedQuery):
        var_types: Dict[str, Variable] = dict()
        qualifiers: Set[str] = set()
        # Pick up on qualifier types automatically
        for clause in pq.clauses:
            if clause.qualifier is not None:
                clause.qualifier.type_info.set("qualifier")
                self._type_insert_or_throw(var_types, clause.qualifier) # maintains a dictionary of variable:datatype
                if clause.qualifier.name in qualifiers:
                    raise QueryParserException(
                        clause.qualifier.token, "redefinition of qualifier" # X:=something, X:=somethingelse, WRONG, same variable cannot hold 2 different claims
                    )
                qualifiers.add(clause.qualifier.name)

        # Any other variable in clauses cannot be a qualifier
        for clause in pq.clauses:
            for argument in clause.arguments:
                if isinstance(argument, Variable):
                    if argument.name not in qualifiers:
                        argument.type_info.erase("qualifier") # remove "qualifier" from type_info of rest of the variables

        for item in pq.head:
            if isinstance(item, Aggregation):
                if item.type_ in [
                    AggregationType.MAX,
                    AggregationType.MIN,
                    AggregationType.SUM,
                    AggregationType.AVG,
                ]:
                    item.var.type_info.set("numeric") # count(X) : X should be set to numeric

        self._type_check_query_propagate(pq, var_types)

        # At least one element in a clause (w.o. qualifiers) must be an entity_id
        for clause in pq.clauses:
            if clause.is_qualifier_claim(): # X: Y:=holds("Obama", "President") ; start_date(Y, X/date) start_date clause is a qualifier claim since argument of it is a qualifier
                # NOTE We can have at most a single qualifier.
                if (
                    clause.arguments[0].type_info() == "qualifier"
                    and clause.arguments[1].type_info() == "qualifier"
                ):
                    raise QueryParserExceptionWithNote(
                        clause.arguments[1].token,
                        "clause contains multiple qualifiers",
                        clause.arguments[0].token,
                        "first qualifier argument is located here",
                    )
                continue
            else:
                assert len(clause.arguments) == 2
                if not clause.arguments[0].type_info.can("entity_id"):
                    clause.arguments[1].type_info.set("entity_id")
                elif not clause.arguments[1].type_info.can("entity_id"):
                    clause.arguments[0].type_info.set("entity_id")

        # Automatically "infer" the standard datatype for constants.
        for clause in pq.clauses:
            for argument in clause.arguments:
                if isinstance(argument, StringConstant):
                    # NOTE double quote is already set to entity_id by default.
                    argument.type_info.try_set("string")
                elif isinstance(argument, NumericConstant):
                    argument.type_info.try_set("numeric")
        self._type_check_query_propagate(pq, var_types)

        # NOTE Cannot have qualifiers on qualifier clause.
        for clause in pq.clauses:
            if clause.is_qualifier_claim() and clause.qualifier is not None: # cannot be X: Y:=holds("Obama", "President"); Z:= start_date(Y, X/date) start_date is a clause with qualifier and Z is a qualifier for this clause, WRONG because Y itself is a qualifier and that is in turn being assigned to qualifier Z
                raise QueryParserExceptionWithNote(
                    clause.qualifier.token,
                    "cannot have qualifiers on this clause",
                    next(
                        argument
                        for argument in clause.arguments
                        if argument.type_info() == "qualifier"
                    ).token,
                    "variable is already a qualifier",
                )

        # NOTE the default type for variable is entity_id
        for clause in pq.clauses:
            for argument in clause.arguments:
                if isinstance(argument, Variable):
                    argument.type_info.try_set("entity_id")

        self._type_check_query_propagate(pq, var_types)

        # Add this point everything should be typed.
        for item in pq.head:
            if isinstance(item, Aggregation):
                assert item.var.type_info() is not None
            else:
                assert isinstance(item, Variable)
                assert item.type_info() is not None

        for clause in pq.clauses:
            if clause.qualifier is not None:
                assert clause.qualifier.type_info() is not None
            for argument in clause.arguments:
                assert argument.type_info() is not None

        for filter in pq.filters:
            assert filter.lhs.type_info() is not None
            assert filter.rhs.type_info() is not None

        if self.note_fn is not None:
            for clause in pq.clauses:
                for argument in clause.arguments:
                    if isinstance(argument, StringConstant):
                        if argument.type_info() != "date":
                            if argument.try_parse_date(explicit_cast=False) is not None:
                                self.note_fn(
                                    argument.token,
                                    f"string literal matches date format, but is of type {argument.type_info()}; explicitly cast via '... / date'",
                                )

        # Check that constants typed date can be parsed to dates
        for clause in pq.clauses:
            for argument in clause.arguments:
                if (
                    isinstance(argument, StringConstant)
                    and argument.type_info() == "date"
                ):
                    if argument.try_parse_date(explicit_cast=True) is None:
                        raise QueryParserException(
                            argument.token, "unknown format for date constant"
                        )

        return True

    def _type_check_query_propagate(
        self, pq: ParsedQuery, var_types: Dict[str, Variable], recursed=False
    ) -> bool:
        # propagates the type of the variable across the IR
        # example - X, Y:  film(X); release_date(X, Y/date) -> then Y as date should be propagated to head as well. 
        # done recursively
        updated = 0
        for item in pq.head:
            if isinstance(item, Aggregation):
                updated += self._type_insert_or_throw(var_types, item.var)
            else:
                assert isinstance(item, Variable)
                updated += self._type_insert_or_throw(var_types, item)

        for item in pq.filters:
            if item.lhs.type_info() is None:
                updated += item.lhs.type_info.set(item.rhs.type_info())
            self._type_insert_or_throw(var_types, item.lhs)
            if item.rhs.type_info() is None:
                updated += item.rhs.type_info.set(item.lhs.type_info())
            if isinstance(item.rhs, Variable):
                updated += self._type_insert_or_throw(var_types, item.rhs)

        for clause in pq.clauses:
            assert len(clause.arguments) == 2
            for argument in clause.arguments:
                if isinstance(argument, Variable):
                    updated += self._type_insert_or_throw(var_types, argument)
        if updated:
            return self._type_check_query_propagate(pq, var_types, True)
        return recursed

    def _type_insert_or_throw(
        self, var_types: Dict[str, Variable], var: Variable
    ) -> bool:
        if var.type_info() is None:
            if var.name in var_types:
                return var.type_info.set(var_types[var.name].type_info())
            return False
        if var.name in var_types:
            if var.type_info() != var_types[var.name].type_info():
                raise QueryParserExceptionWithNote(
                    var.token,
                    f"inconsistent type declaration {var.type_info()} for variable {var.name}",
                    var_types[var.name].token,
                    f"{var.name} declared to be {var_types[var.name].type_info()} here",
                )
            return False
        var_types[var.name] = var
        return True

    def _rewrite_query(self, pq: ParsedQuery) -> ParsedQuery:
        # Rewrite unary queries using "instance_of": person(X) becomes !P31(X, "person")
        clauses: List[QueryClause] = []
        for clause in pq.clauses:
            if len(clause.arguments) != 1:
                clauses.append(clause)
                continue

            type_ = clause.predicate
            if not isinstance(type_, Variable):
                raise QueryParserException(
                    clause.predicate.token, "cannot rewrite unary predicate"
                )
            assert isinstance(type_, Variable)
            
            # rewrite film(X) as !P31(X, "film")

            type_lit = StringLiteral(
                source_location=clause.predicate.token.source_location,
                value=type_.name,
            )
            # TODO(jlscheerer) It might also make sense to include occupation here.
            clauses.append(
                QueryClause(
                    predicate=IDConstant(
                        Identifier(
                            source_location=SourceLocation.synthetic(), name="P31"
                        ),
                        annotation=AnnotationType.BANG,
                        value="P31",
                    ),
                    arguments=[
                        clause.arguments[0],
                        StringConstant(token=type_lit, value=type_lit.value),
                    ],
                )
            )
        return ParsedQuery(head=pq.head, clauses=clauses, filters=pq.filters)

    def _validate_query(self, pq: ParsedQuery) -> bool:
        head_vars = pq.head.vars()
        aggregate_vars = set()
        for item in pq.head:
            if isinstance(item, Aggregation):
                aggregate_vars.add(item.var.name)

        for item in pq.head:
            if isinstance(item, Variable):
                if item.name in aggregate_vars:
                    raise QueryParserException(
                        item.token,
                        f"variable {item.source_name()} appears as variable and in aggregate(s)", # X, count(X) : wrong!
                    )

        clause_vars: Set[Variable] = set()
        for clause in pq.clauses:
            for argument in clause.arguments:
                if isinstance(argument, Variable):
                    clause_vars.add(argument)
            if clause.qualifier is not None:
                clause_vars.add(clause.qualifier)

        # Every variable occuring in the head must be bound in the body via a clause.
        for var in head_vars:
            if var not in clause_vars:
                raise QueryParserException(
                    var.token,
                    f"unbound variable: {var.source_name()} does not appear in a clause",
                )

        # Every variable as a filter must be bound in the body via a clause.
        for filter in pq.filters:
            if filter.lhs not in clause_vars:
                raise QueryParserException(
                    filter.lhs.token,
                    f"unbound variable: {filter.lhs.source_name()} does not appear in a clause",
                )
            if isinstance(filter.rhs, Variable):
                if filter.rhs not in clause_vars:
                    raise QueryParserException(
                        filter.rhs.token,
                        f"unbound variable: {filter.rhs.source_name()} does not appear in a clause",
                    )

        # Aggregations are not yet supported.
        for item in pq.head:
            if isinstance(item, Aggregation):
                if item.type_.name not in ["COUNT", "MIN", "MAX"]:
                    raise QueryParserException(
                        item.token,
                        f"aggregation {item.type_.name}(_) not yet supported",
                    )

        # We only support unary/binary predicates
        for clause in pq.clauses:
            if len(clause.arguments) == 0:
                raise QueryParserException(
                    clause.predicate.token, "unsupported nullary predicate"
                )
            elif len(clause.arguments) > 2:
                raise QueryLexerException(
                    SourceLocation(
                        begin=clause.arguments[0].token.source_location.begin,
                        end=clause.arguments[-1].token.source_location.end,
                    ),
                    f"too many arguments to predicate '{clause.predicate.source_name()}'",
                )

        # Check the format of IDConstants as entities/predicates
        for clause in pq.clauses:
            if isinstance(clause.predicate, IDConstant):
                if clause.predicate.annotation != AnnotationType.BANG: # !P31 are ID Constants !? : Bang
                    raise QueryParserException(
                        clause.predicate.token,
                        f"unsupported annotation '{clause.predicate.annotation.value}' on predicate {clause.predicate.value}",
                    )
                if not re.match("^P[0-9]+$", clause.predicate.value):
                    raise QueryParserException(
                        clause.predicate.token,
                        f"unsupported format for predicate constant: {clause.predicate.value}",
                    )
            for argument in clause.arguments:
                if isinstance(argument, IDConstant):
                    if argument.annotation != AnnotationType.BANG:
                        raise QueryParserException(
                            argument.token,
                            f"unsupported annotation '{argument.annotation.value}' on predicate {argument.value}",
                        )
                    if not re.match("^Q[0-9]+", argument.value):
                        raise QueryParserException(
                            argument.token,
                            f"unsupported format for entity constant: {argument.value}",
                        )

        # Check for overlap in assignments
        for clause in pq.clauses:
            if clause.qualifier is None:
                continue
            for argument in clause.arguments: # cannot be Y:=holds(Y, Z)
                if isinstance(argument, Variable):
                    if clause.qualifier.name == argument.name:
                        raise QueryParserExceptionWithNote(
                            clause.qualifier.token,
                            "qualifier appears as part of its own clause",
                            argument.token,
                            "the qualifier appears here",
                        )

        return True

    def _parse_head(self) -> QueryHead:
        token = self._pop_token()
        # We should always at least encounter the `COLON` token.
        assert token is not None
        item: HeadItem
        if token.token_type == TokenType.IDENTIFIER:
            item = Variable(token=token, name=token.name)
            pk = self._curr_token()
            if pk is not None and pk.token_type == TokenType.TYPE_INDICATOR:
                self._pop_token()
                type_ = self._pop_require_token()
                if type_.token_type != TokenType.TYPE_NAME:
                    raise QueryParserException(
                        type_, f"unexpected {type_.token_type} as type"
                    )
                item.type_info.set(type_.type_)
        elif token.token_type == TokenType.AGGREGATION_FUNCTION:
            arguments = self._parse_arguments()
            if len(arguments) == 0:
                raise QueryParserException(token, "missing argument for aggregation")
            elif len(arguments) != 1:
                raise QueryLexerException(
                    SourceLocation(
                        begin=arguments[0].token.source_location.begin,
                        end=arguments[-1].token.source_location.end,
                    ),
                    "too many arguments for aggregation",
                )

            var = arguments[0]
            if not isinstance(var, Variable):
                raise QueryParserException(
                    var.token, f"unexpected {var} for aggregation"
                )
            item = Aggregation(token=token, var=var, type_=AggregationType[token.name])
        else:
            raise QueryParserException(
                token, f"unexpected {token.token_type} in query head"
            )

        token = self._pop_token()
        # We should always at least encounter the `COLON` token.
        assert token is not None
        if token.token_type == TokenType.COMMA:
            return QueryHead(items=[item] + self._parse_head().items)
        elif token.token_type != TokenType.COLON:
            raise QueryParserException(
                token, f"unexpected {token.token_type} in query head"
            )
        return QueryHead(items=[item])

    def _parse_body(self) -> Tuple[List[QueryClause], List[QueryFilter]]:
        clauses: List[QueryClause] = []
        filters: List[QueryFilter] = []
        while True:
            atom = self._parse_atom()
            if atom is None:
                raise QueryLexerException(
                    SourceLocation(begin=self._eof, end=self._eof + 1),
                    "missing query body",
                )

            if isinstance(atom, QueryClause):
                clauses.append(atom)
            else:
                assert isinstance(atom, QueryFilter)
                filters.append(atom)

            if self._curr_token() is None:
                break
            token = self._pop_require_token()
            if token.token_type != TokenType.SEMICOLON:
                raise QueryParserException(
                    token, f"unexpected {token.token_type} in query body"
                )
        return clauses, filters

    def _parse_atom(self) -> Optional[QueryAtom]:
        ident = self._pop_token()
        if ident is None:
            return None

        # We have an annotated predicate, e.g., !P17 / ?P17
        annotation: Optional[Token] = None
        if ident.token_type in [TokenType.EXCLAMATION_MARK, TokenType.QUESTION_MARK]:
            annotation = ident
            ident = self._pop_require_token()

        # TODO(jlscheerer) We could also support Literals on the lhs of comparisons
        if ident.token_type != TokenType.IDENTIFIER:
            raise QueryParserException(
                ident, f"unexpected {ident.token_type} in query body"
            )
        qualifier_ident = None
        qualifier_type = None
        token = self._require_token()

        if token.token_type == TokenType.TYPE_INDICATOR:
            # will get triggered in cases like X/date:=holds("Obama", "President") or X/date>2000
            self._pop_token()
            type_ = self._pop_require_token()
            if type_.token_type != TokenType.TYPE_NAME:
                raise QueryParserException(
                    type_, f"expected type, but got {type_.token_type}"
                )
            qualifier_type = type_.type_
            token = self._require_token()
            if token.token_type not in [TokenType.ASSIGNMENT, TokenType.COMPARATOR]:
                raise QueryParserException(
                    token,
                    f"expected assignment or comparison, but got {type_.token_type}",
                )

        if token.token_type == TokenType.ASSIGNMENT:
            # will triggered in cases like X:=holds("Obama", "President")
            self._pop_token()  # NOTE remove the assignment tken.
            if annotation is not None:
                # cannot do something like !P31:=holds("Obama", "President")
                raise QueryParserException(
                    annotation, f"unexpected {annotation.token_type} in assignment"
                )
            # TODO(jlscheerer) Support type indicator for the qualifier.
            qualifier_ident = ident
            ident = self._pop_require_token()
            if ident.token_type != TokenType.IDENTIFIER:
                raise QueryParserException(
                    ident,
                    f"unexpected {ident.token_type} as right-hand side of assignment",
                )
            token = self._require_token()
        if token.token_type == TokenType.OPEN_PAREN:
            arguments = self._parse_arguments()
            predicate: Union[Variable, IDConstant]
            if annotation is None:
                predicate = Variable(token=ident, name=ident.name) # holds("Obama",X)
            else:
                predicate = self._as_id_constant(annotation=annotation, constant=ident) # !P31("Obama", X) while putting it as predicate in a clause, it is labelled ID Constant, else as tokens ! exclamation P31 identifier
            qualifier = None
            if qualifier_ident is not None:
                qualifier = Variable(token=qualifier_ident, name=qualifier_ident.name)
                if qualifier_type is not None:
                    qualifier.type_info.set(qualifier_type)
            return QueryClause(
                predicate=predicate, arguments=arguments, qualifier=qualifier # for query 'Z: Y := award(X, "Academy Award for Best Picture"); winner(Y, Z)' : predicate = award, arguments = X, "Academy..", qualifier = Y
            )
        elif token.token_type == TokenType.COMPARATOR: # X: film(X) ; release_year(X, Y); Y>2000 list all films released after year 2000
            # We cannot have annotated predicates with comparisons.
            if annotation is not None:
                raise QueryParserException(
                    annotation, f"unexpected {annotation.token_type} in comparison"
                )
            # We cannot have assignments with comparisons. No comparators in qualifier clause
            if qualifier_ident is not None:
                raise QueryParserException(
                    qualifier_ident,
                    f"unexpected {qualifier_ident.token_type} in comparison",
                )

            op = self._pop_require_token()
            if op.token_type != TokenType.COMPARATOR:
                raise QueryParserException(
                    op, f"expected {TokenType.COMPARATOR} got {op.token_type}"
                )
            rhs = self._pop_require_token()
            lhs_var = Variable(token=ident, name=ident.name)
            lhs_var.type_info.set(qualifier_type)

            if rhs.token_type in [
                TokenType.STRING_LITERAL,
                TokenType.NUMERIC_LITERAL,
            ]:
                return QueryFilter(
                    lhs=lhs_var,
                    op=FilterOp(op.operator),
                    rhs=self._as_constant(rhs), # in double/single quotes ( string constant ) or numeric constant X>=2000
                )
            elif rhs.token_type == TokenType.IDENTIFIER:
                rhs_var = Variable(token=rhs, name=rhs.name) 
                pk = self._curr_token() # X > Y/date
                if pk is not None and pk.token_type == TokenType.TYPE_INDICATOR:
                    self._pop_token()
                    type_ = self._pop_require_token()
                    if type_.token_type != TokenType.TYPE_NAME:
                        raise QueryParserException(
                            type_, f"expected type, but got {type_.token_type}"
                        )
                    rhs_var.type_info.set(type_.type_)
                return QueryFilter(
                    lhs=lhs_var,
                    op=FilterOp(op.operator),
                    rhs=rhs_var, # X > Y , added as variable
                )
            else:
                raise QueryParserException(
                    rhs,
                    f"expected {TokenType.STRING_LITERAL} or {TokenType.NUMERIC_LITERAL}, but got {rhs.token_type}",
                )
        raise QueryParserException(
            token, f"unexpected {token.token_type} in query body"
        )

    def _as_constant(self, token: Token) -> Constant:
        literal_type = None
        pk = self._curr_token()
        if pk is not None and pk.token_type == TokenType.TYPE_INDICATOR:
            self._pop_token()
            type_ = self._pop_require_token()
            if type_.token_type != TokenType.TYPE_NAME:
                raise QueryParserException(
                    type_, f"expected type, but got {type_.token_type}"
                )
            literal_type = type_.type_
        const: Constant
        if token.token_type == TokenType.STRING_LITERAL:
            const = StringConstant(token=token, value=token.value)
            const.type_info.set(literal_type)
            return const
        elif token.token_type == TokenType.NUMERIC_LITERAL:
            if "." in token.value:
                const = NumericConstant(token=token, value=float(token.value))
                const.type_info.set(literal_type)
                return const
            const = NumericConstant(token=token, value=int(token.value))
            const.type_info.set(literal_type)
            return const
        # this represents an illegal invocation of _as_constant()
        raise AssertionError()

    def _as_id_constant(self, annotation: Token, constant: Identifier) -> IDConstant:
        if annotation.token_type == TokenType.EXCLAMATION_MARK:
            return IDConstant(
                token=constant, annotation=AnnotationType.BANG, value=constant.name
            )
        elif annotation.token_type == TokenType.QUESTION_MARK:
            return IDConstant(
                token=constant, annotation=AnnotationType.OPT, value=constant.name
            )
        # this represents an illegal invocation of _as_id_constant()
        raise AssertionError()

    def _parse_arguments(self) -> List[Union[Variable, Constant]]:
        self._check_token(TokenType.OPEN_PAREN, should_raise=True)

        arguments: List[Union[Variable, Constant]] = []
        while True:
            token = self._pop_token()
            if token is None:
                raise QueryLexerException(
                    SourceLocation(begin=self._eof, end=self._eof + 1),
                    "unterminated argument list",
                )
            if token.token_type == TokenType.CLOSE_PAREN:
                return arguments

            if token.token_type in [
                TokenType.EXCLAMATION_MARK,
                TokenType.QUESTION_MARK,
            ]:
                # We have an "annotated" identifier, e.g., !Q76 / ?Q76
                ident = self._pop_require_token()
                if ident.token_type != TokenType.IDENTIFIER:
                    raise QueryParserException(
                        ident,
                        f"expected {TokenType.IDENTIFIER} but got {ident.token_type}",
                    )
                arguments.append(self._as_id_constant(annotation=token, constant=ident))
            elif token.token_type == TokenType.IDENTIFIER: # holds(X/date, Y)
                var = Variable(token=token, name=token.name)
                pk = self._curr_token()
                if pk is not None and pk.token_type == TokenType.TYPE_INDICATOR:
                    self._pop_token()
                    type_ = self._pop_require_token()
                    if type_.token_type != TokenType.TYPE_NAME:
                        raise QueryParserException(
                            type_, f"unexpected {type_.token_type} as type"
                        )
                    var.type_info.set(type_.type_)
                arguments.append(var)
            elif token.token_type in [ # holds("Obama",X) or holds('Obama', X)
                TokenType.STRING_LITERAL,
                TokenType.NUMERIC_LITERAL,
            ]:
                arguments.append(self._as_constant(token))
            else:
                raise QueryParserException(
                    token, f"unexpected {token.token_type} in argument list"
                )

            token = self._pop_token()
            if token is None:
                raise QueryLexerException(
                    SourceLocation(begin=self._eof, end=self._eof + 1),
                    "unterminated argument list",
                )
            if token.token_type == TokenType.CLOSE_PAREN:
                return arguments

            if token.token_type != TokenType.COMMA:
                raise QueryParserException(
                    token, f"unexpected {token.token_type} in argument list"
                )

    def _check_contains_colon(self) -> bool:
        colon_tokens = [
            *filter(lambda token: token.token_type == TokenType.COLON, self._tokens)
        ]
        if len(colon_tokens) > 1:
            raise QueryParserException(colon_tokens[1], "extranous ':' in query")
        return len(colon_tokens) == 1

    def _advance_cursor(self, amount=1) -> None:
        self._cursor += amount

    def _token_at(self, cursor) -> Optional[Token]:
        if cursor >= len(self._tokens):
            return None
        return self._tokens[cursor]

    def _require_token(self) -> Token:
        token = self._curr_token()
        if token is None:
            raise QueryLexerException(
                SourceLocation(begin=self._eof, end=self._eof + 1),
                "missing required token",
            )
        return token

    def _curr_token(self) -> Optional[Token]:
        return self._token_at(self._cursor)

    def _pop_require_token(self) -> Token:
        token = self._pop_token()
        if token is None:
            raise QueryLexerException(
                SourceLocation(begin=self._eof, end=self._eof + 1),
                "missing required token",
            )
        return token

    def _pop_token(self) -> Optional[Token]:
        token = self._curr_token()
        self._advance_cursor()
        return token

    def _check_token(self, token_type: TokenType, should_raise: bool = False) -> bool:
        token = self._pop_token()
        if token is None:
            if should_raise:
                raise QueryLexerException(
                    SourceLocation(begin=self._eof, end=self._eof + 1),
                    f"expected {token_type} but got EOF",
                )
            return False
        if token.token_type != token_type:
            if should_raise:
                raise QueryParserException(
                    token, f"expected {token_type} but got {token.token_type}"
                )
            return False
        return True

    def _peak_token(self):
        return self._token_at(self._cursor + 1)
