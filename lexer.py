from globalTypes import *

programa = ""
posicion = 0
progLong = 0
lexer_error = False  # Variable para controlar errores léxicos


def globales(prog, pos, long):
    global programa, posicion, progLong, lexer_error
    programa = prog
    posicion = pos
    progLong = long
    lexer_error = False  # Reiniciar el estado de error


def getToken(imprime=True):
    global posicion, programa

    # ignora los espacios en blanco y saltos de línea
    while posicion < progLong and programa[posicion].isspace():
        posicion += 1

    if posicion >= progLong or programa[posicion] == '$':
        return TokenType.ENDFILE, "EOF"

    while True:
        token, lexema = reconocer()

        # si es un comentario busca el siguiente token
        if token == TokenType.COMMENT:
            continue

        if imprime and token != TokenType.ERROR:
            print(token, "=", lexema)

        return token, lexema


def reconocer():
    global programa, posicion, lexer_error

    estado = 0
    lexema = ""
    linea = programa[:posicion].count('\n') + 1

    while posicion < progLong:
        c = programa[posicion]

        if estado == 0:
            if c.isspace():
                posicion += 1
                continue  # ignora espacios en blanco
            if c.isdigit():
                estado = 1
                lexema += c
                posicion += 1
            elif c.isalpha() or c == "_":
                estado = 2
                lexema += c
                posicion += 1
            elif c == '/':
                if posicion + 1 < progLong and programa[posicion + 1] == '*':
                    # comentario de varias líneas
                    posicion += 2
                    while posicion < progLong - 1:
                        if programa[posicion] == '*' and programa[posicion + 1] == '/':
                            posicion += 2
                            return TokenType.COMMENT, "/*...*/"
                        posicion += 1
                    print(f"Línea {linea}: Error, comentario no cerrado")
                    lexer_error = True
                    return TokenType.ERROR, "Comentario no cerrado"
                else:
                    return manejarSimbolos(c, linea)
            elif c in "+-*=<>!;:,(){}[]":
                return manejarSimbolos(c, linea)
            else:
                print(f"Línea {linea}: Carácter inválido '{c}'")
                print(obtenerLinea(programa, linea))
                print(" " * posLinea(programa, posicion) + "^")
                posicion += 1
                lexer_error = True
                return TokenType.ERROR, c

        elif estado == 1:  # número entero o decimal
            if c.isdigit():
                lexema += c
                posicion += 1
            elif c == '.':
                lexema += c
                posicion += 1
                estado = 3
            else:
                return TokenType.NUM, lexema

        elif estado == 2:  # identificador o palabra reservada
            if c.isalnum() or c == "_":
                lexema += c
                posicion += 1
            else:
                palabras = ["if", "else", "while", "return",
                            "int", "void", "output", "input"]
                if lexema in palabras:
                    return TokenType[lexema.upper()], lexema
                return TokenType.ID, lexema

        elif estado == 3:  # decimal después del punto
            if c.isdigit():
                lexema += c
                posicion += 1
                estado = 4
            else:
                print(f"Línea {linea}: Error, punto decimal sin dígito")
                return TokenType.ERROR, lexema

        elif estado == 4:
            if c.isdigit():
                lexema += c
                posicion += 1
            else:
                return TokenType.NUM, lexema

    # fin del archivo
    if estado == 1 or estado == 4:
        return TokenType.NUM, lexema
    elif estado == 2:
        return TokenType.ID, lexema
    return TokenType.ERROR, lexema


def manejarSimbolos(c, linea):
    global posicion, programa, lexer_error

    simbolos = {
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.MULT,
        '/': TokenType.DIV,
        '=': TokenType.ASSIGN,
        '<': TokenType.LT,
        '>': TokenType.GT,
        ';': TokenType.SEMI,
        ',': TokenType.COMMA,
        '(': TokenType.LPAREN,
        ')': TokenType.RPAREN,
        '{': TokenType.LBRACE,
        '}': TokenType.RBRACE,
        '[': TokenType.LBRACKET,
        ']': TokenType.RBRACKET
    }

    siguiente = programa[posicion + 1:posicion + 2]
    doble = c + siguiente

    if doble == "==":
        posicion += 2
        return TokenType.EQ, "=="
    elif doble == "!=":
        posicion += 2
        return TokenType.NEQ, "!="
    elif doble == "<=":
        posicion += 2
        return TokenType.LTEQ, "<="
    elif doble == ">=":
        posicion += 2
        return TokenType.GTEQ, ">="
    elif c == '/' and siguiente == '*':
        posicion += 2
        while posicion < len(programa) - 1:
            if programa[posicion] == '*' and programa[posicion + 1] == '/':
                posicion += 2
                return TokenType.COMMENT, "/*...*/"
            if programa[posicion] == '\n':
                pass
            posicion += 1
        lexer_error = True
        return TokenType.ERROR, "/* sin cerrar */"
    else:
        posicion += 1
        return simbolos.get(c, TokenType.ERROR), c


def obtenerLinea(texto, num_linea):
    lineas = texto.splitlines()
    return lineas[num_linea - 1] if num_linea <= len(lineas) else ""


def posLinea(texto, index):
    linea_inicio = texto.rfind('\n', 0, index) + 1
    return index - linea_inicio


def getLineaActual():
    global programa, posicion
    return programa[:posicion].count('\n') + 1
