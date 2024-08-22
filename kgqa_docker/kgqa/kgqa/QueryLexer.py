from enum import auto, Enum
from typing import Optional, Literal, Union
from dataclasses import dataclass
import string

TYPE_NAMES = {"entity_id", "string", "date", "numeric", "coordinate", "qualifier"}
AGGREGATION_FUNCTIONS = {"COUNT", "SUM", "AVG", "MAX", "MIN"}


class TokenType(Enum):
    IDENTIFIER = auto()
    TYPE_NAME = auto()
    AGGREGATION_FUNCTION = auto()

    COMPARATOR = auto()

    STRING_LITERAL = auto()
    NUMERIC_LITERAL = auto()

    COLON = auto()
    TYPE_INDICATOR = auto()
    ASSIGNMENT = auto()

    SEMICOLON = auto()
    COMMA = auto()

    OPEN_PAREN = auto()
    CLOSE_PAREN = auto()

    EXCLAMATION_MARK = auto()
    QUESTION_MARK = auto()


@dataclass
class SourceLocation:
    begin: int
    end: int

    @staticmethod
    def synthetic():
        return SourceLocation(begin=-1, end=-1)


@dataclass
class TokenBase:
    source_location: SourceLocation


@dataclass
class Identifier(TokenBase):
    name: str

    token_type: Literal[TokenType.IDENTIFIER] = TokenType.IDENTIFIER


@dataclass
class TypeName(TokenBase):
    type_: Literal["entity_id", "string", "date", "numeric", "coordinate", "qualifier"]

    token_type: Literal[TokenType.TYPE_NAME] = TokenType.TYPE_NAME


@dataclass
class AggregationFunction(TokenBase):
    name: Literal["COUNT", "SUM", "AVG", "MAX", "MIN"]

    token_type: Literal[TokenType.AGGREGATION_FUNCTION] = TokenType.AGGREGATION_FUNCTION


@dataclass
class Compator(TokenBase):
    operator: Literal["=", "!=", ">=", "<=", ">", "<"]

    token_type: Literal[TokenType.COMPARATOR] = TokenType.COMPARATOR


class QuoteType(Enum):
    SINGLE_QUOTE = "'"
    DOUBLE_QUOTE = '"'


@dataclass
class StringLiteral(TokenBase):
    value: str
    quote_type: QuoteType = QuoteType.DOUBLE_QUOTE

    token_type: Literal[TokenType.STRING_LITERAL] = TokenType.STRING_LITERAL


@dataclass
class NumericLiteral(TokenBase):
    value: str

    token_type: Literal[TokenType.NUMERIC_LITERAL] = TokenType.NUMERIC_LITERAL


@dataclass
class Colon(TokenBase):
    token_type: Literal[TokenType.COLON] = TokenType.COLON


@dataclass
class TypeIndicator(TokenBase):
    token_type: Literal[TokenType.TYPE_INDICATOR] = TokenType.TYPE_INDICATOR


@dataclass
class Assignment(TokenBase):
    token_type: Literal[TokenType.ASSIGNMENT] = TokenType.ASSIGNMENT


@dataclass
class Semicolon(TokenBase):
    token_type: Literal[TokenType.SEMICOLON] = TokenType.SEMICOLON


@dataclass
class Comma(TokenBase):
    token_type: Literal[TokenType.COMMA] = TokenType.COMMA


@dataclass
class OpenParen(TokenBase):
    token_type: Literal[TokenType.OPEN_PAREN] = TokenType.OPEN_PAREN


@dataclass
class CloseParen(TokenBase):
    token_type: Literal[TokenType.CLOSE_PAREN] = TokenType.CLOSE_PAREN


@dataclass
class ExclamationMark(TokenBase):
    token_type: Literal[TokenType.EXCLAMATION_MARK] = TokenType.EXCLAMATION_MARK


@dataclass
class QuestionMark(TokenBase):
    token_type: Literal[TokenType.QUESTION_MARK] = TokenType.QUESTION_MARK


LiteralToken = Union[StringLiteral, NumericLiteral]
IdentifierToken = Union[Identifier, AggregationFunction]
Token = Union[
    IdentifierToken,
    TypeName,
    Compator,
    LiteralToken,
    Colon,
    TypeIndicator,
    Assignment,
    Semicolon,
    Comma,
    OpenParen,
    CloseParen,
    ExclamationMark,
    QuestionMark,
]


class QueryLexerException(Exception):
    def __init__(self, source_location: SourceLocation, error: str):
        self.source_location = source_location
        self.error = error


class QueryLexer:
    def __init__(self, query: str):
        self._cursor = 0
        self._query = query

    def __iter__(self):
        return self

    def __next__(self) -> Token:
        token = self._next_token()
        if token is not None:
            return token
        raise StopIteration

    def _next_token(self) -> Optional[Token]:
        loc = self._current_source_location()
        char = self._curr_char()
        if char is None:
            return None
        elif char == ":" and self._peak_char() == "=":
            self._advance_cursor(amount=2)
            return Assignment(source_location=SourceLocation(loc.begin, loc.end + 1))
        elif char == "/":
            self._advance_cursor()
            return TypeIndicator(source_location=loc)
        elif char == ":":
            self._advance_cursor()
            return Colon(source_location=loc)
        elif char == ";":
            self._advance_cursor()
            return Semicolon(source_location=loc)
        elif char == ",":
            self._advance_cursor()
            return Comma(source_location=loc)
        elif char == "(":
            self._advance_cursor()
            return OpenParen(source_location=loc)
        elif char == ")":
            self._advance_cursor()
            return CloseParen(source_location=loc)
        elif self._is_whitespace(char):
            self._advance_cursor()
            return self._next_token()
        elif char == '"' or char == "'":
            return self._tokenize_string_literal()
        elif self._char_begins_numeric_literal(char):
            return self._tokenize_numeric_literal()
        elif char in [">", "<", "!"] and self._peak_char() == "=":
            self._advance_cursor(amount=2)
            return Compator(
                source_location=SourceLocation(loc.begin, loc.end + 1),
                operator=f"{char}=",  # type: ignore
            )
        elif char in ["=", ">", "<"]:
            self._advance_cursor()
            return Compator(source_location=loc, operator=char)  # type: ignore
        elif char == "!":
            self._advance_cursor()
            return ExclamationMark(source_location=loc)
        elif char == "?":
            self._advance_cursor()
            return QuestionMark(source_location=loc)
        elif self._char_begins_identifier(char):
            return self._tokenize_identifier()
        raise QueryLexerException(
            self._current_source_location(), f"unknown character '{char}'"
        )

    def _tokenize_identifier(self) -> IdentifierToken:
        assert self._char_begins_identifier(self._curr_char())

        begin = self._cursor
        name = str()
        while self._is_valid_identifier_char(self._curr_char()):
            char = self._curr_char()
            assert char is not None
            self._advance_cursor()
            name += char

        if name in TYPE_NAMES:
            return TypeName(
                source_location=SourceLocation(begin=begin, end=self._cursor),
                type_=name,  # type: ignore
            )
        if name.upper() in AGGREGATION_FUNCTIONS:
            return AggregationFunction(
                source_location=SourceLocation(begin=begin, end=self._cursor),
                name=name.upper(),  # type: ignore
            )
        return Identifier(
            source_location=SourceLocation(begin=begin, end=self._cursor), name=name
        )

    def _char_begins_identifier(self, char) -> bool:
        IDENTIFIER_BEGIN_CHARS = string.ascii_letters + "_"
        return char in IDENTIFIER_BEGIN_CHARS

    def _is_valid_identifier_char(self, char):
        IDENTIFIER_CHARS = string.ascii_letters + string.digits + "_"
        return char is not None and char in IDENTIFIER_CHARS

    def _tokenize_string_literal(self) -> StringLiteral:
        begin = self._cursor
        quote_type = self._curr_char()
        assert quote_type in ['"', "'"]

        self._advance_cursor()
        escaped = False
        value = str()
        while self._curr_char() is not None:
            char = self._curr_char()
            assert char is not None

            self._advance_cursor()
            if char == quote_type and not escaped:
                return StringLiteral(
                    source_location=SourceLocation(begin=begin, end=self._cursor),
                    value=value,
                    quote_type=(
                        QuoteType.DOUBLE_QUOTE
                        if quote_type == '"'
                        else QuoteType.SINGLE_QUOTE
                    ),
                )
            elif char == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
                value += char
        raise QueryLexerException(
            SourceLocation(begin=begin, end=self._cursor), "unterminated string literal"
        )

    def _tokenize_numeric_literal(self) -> NumericLiteral:
        # For now only numeric literals must be of the form:
        # [0-9]+(.[0-9])? | .[0-9]+
        begin = self._cursor
        integer = str()
        char = self._curr_char()
        while char is not None and char in string.digits:
            integer += char
            self._advance_cursor()
            char = self._curr_char()

        fraction = str()
        if char is not None and char == ".":
            self._advance_cursor()
            char = self._curr_char()
            while char is not None and char in string.digits:
                fraction += char
                self._advance_cursor()
                char = self._curr_char()

        if len(integer) == 0 and len(fraction) == 0:
            raise QueryLexerException(
                SourceLocation(begin=begin, end=self._cursor), "invalid numeric literal"
            )

        if len(fraction) == 0:
            return NumericLiteral(
                source_location=SourceLocation(begin=begin, end=self._cursor),
                value=integer,
            )

        if len(integer) == 0:
            integer = "0"

        return NumericLiteral(
            source_location=SourceLocation(begin=begin, end=self._cursor),
            value=f"{integer}.{fraction}",
        )

    def _char_begins_numeric_literal(self, char):
        # TODO(jlscheerer) Maybe want to support different bases for numerics?
        return char in string.digits or char == "."

    def _advance_cursor(self, amount: int = 1):
        self._cursor += amount

    def _char_at(self, cursor):
        if cursor >= len(self._query):
            return None
        return self._query[cursor]

    def _curr_char(self):
        return self._char_at(self._cursor)

    def _peak_char(self):
        return self._char_at(self._cursor + 1)

    def _current_source_location(self):
        return SourceLocation(begin=self._cursor, end=self._cursor + 1)

    def _is_whitespace(self, char):
        # TODO(jlscheerer) Support different types of whitespace here.
        return char == " "
