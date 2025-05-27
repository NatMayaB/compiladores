from enum import Enum, auto


class TokenType(Enum):
    # Literales y generales
    NUM = auto()
    ID = auto()
    ENDFILE = auto()
    ERROR = auto()

    # Palabras clave
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    INT = auto()
    VOID = auto()
    MAIN = auto()
    INPUT = auto()
    OUTPUT = auto()

    # Operadores aritméticos
    PLUS = auto()        # +
    MINUS = auto()       # -
    MULT = auto()        # *
    DIV = auto()         # /

    # Operadores relacionales y asignación
    LT = auto()          # <
    LTEQ = auto()        # <=
    GT = auto()          # >
    GTEQ = auto()        # >=
    EQ = auto()          # ==
    NEQ = auto()         # !=
    ASSIGN = auto()      # =

    # Delimitadores
    SEMI = auto()        # ;
    COMMA = auto()       # ,
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]

    COMMENT = auto()
