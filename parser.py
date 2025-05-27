from enum import Enum
from lexer import *
from globalTypes import *

posicion_error = -1  # posición del error en el programa
linea_error = -1    # línea del error en el programa
parser_error = False  # Variable para controlar errores sintácticos


# tipos de expresiones posibles
class TipoExpresion(Enum):
    Op = 0
    Const = 1


# nodo del árbol de sintaxis
class NodoArbol:
    def __init__(self, nodoTipo=None):
        self.nodoTipo = nodoTipo
        self.exp = None
        self.hijoIzq = None
        self.hijoDer = None
        self.hijos = []
        self.op = None
        self.val = None
        self.nombre = None
        self.tipo = None
        self.parametros = None
        self.cuerpo = None
        self.tam = None
        self.condicion = None
        self.decl = []
        self.sentencias = []
        self.retorno = None


# nuevo nodo
def nuevoNodoExp(expTipo):
    nodo = NodoArbol('expresion')
    nodo.exp = expTipo
    nodo.lineno = getLineaActual()  # agregado para semantica
    return nodo


# muestra error de sintaxis y ubicación
def errorSintaxis(mensaje):
    global token, tokenString, parser_error
    from lexer import getLineaActual, programa, posicion

    parser_error = True  # Marcar que hubo un error sintáctico
    linea_actual = getLineaActual()

    inicio_linea = programa.rfind('\n', 0, posicion) + 1
    fin_linea = programa.find('\n', posicion)
    if fin_linea == -1:
        fin_linea = len(programa)

    linea_texto = programa[inicio_linea:fin_linea]
    columna = posicion - inicio_linea

    print(f"Línea {linea_actual}: {mensaje} en token \"{tokenString}\"")
    print(linea_texto)
    print(' ' * columna + '^')

    # modo pánico para seguir parseando
    tokens_recuperacion = {TokenType.SEMI, TokenType.RBRACE,
                           TokenType.LBRACE, TokenType.IF, TokenType.WHILE, TokenType.RETURN}
    while token not in tokens_recuperacion and token != TokenType.ENDFILE:
        token, tokenString = getToken(imprime=False)


# espacios para indentación
def imprimeEspacios():
    print(' ' * endentacion, end='')


# AST de forma estructurada
def imprimeAST(arbol):
    global endentacion
    endentacion += 2
    if arbol is not None:
        imprimeEspacios()
        if arbol.nodoTipo == 'expresion':
            if arbol.exp == TipoExpresion.Op:
                print(f'Op: {arbol.op}')  # imprime el operador
            elif arbol.exp == TipoExpresion.Const:
                print(f'Const: {arbol.val}')
            else:
                print('Expresión desconocida')

        elif arbol.nodoTipo == 'fun':
            print(f'Funcion: {arbol.nombre} tipo: {arbol.tipo}')
            # imprime bloque compuesto de la función
            imprimeAST(arbol.cuerpo)

        elif arbol.nodoTipo == 'var':
            print(
                f'Variable: {arbol.nombre} tipo: {arbol.tipo} tam: {arbol.tam}')

        elif arbol.nodoTipo == 'compuesto':
            print('Bloque compuesto:')
            for decl in arbol.decl:
                imprimeAST(decl)
            for stmt in arbol.sentencias:
                imprimeAST(stmt)

        elif arbol.nodoTipo == 'return':
            print('Sentencia return:')
            imprimeAST(arbol.retorno)

        elif arbol.nodoTipo == 'exp-stmt':
            print('Sentencia de expresión:')
            imprimeAST(arbol.hijoIzq)

        elif arbol.nodoTipo == 'call':
            print(f'Llamada a función: {arbol.nombre}')
            for arg in arbol.hijos:
                imprimeAST(arg)

        elif arbol.nodoTipo == 'if':
            print('Sentencia if:')
            print('Condición:')
            imprimeAST(arbol.condicion)
            print('Bloque if:')
            imprimeAST(arbol.hijoIzq)
            if arbol.hijoDer:
                print('Bloque else:')
                imprimeAST(arbol.hijoDer)

        elif arbol.nodoTipo == 'while':
            print('Sentencia while:')
            print('Condición:')
            imprimeAST(arbol.condicion)
            print('Bloque:')
            imprimeAST(arbol.hijoIzq)

        else:
            print(f'Nodo: {arbol.nodoTipo}')

        # solo imprime hijos si el nodo es de tipo expresion
        if arbol.nodoTipo == 'expresion':
            imprimeAST(arbol.hijoIzq)
            imprimeAST(arbol.hijoDer)

        # solo imprime hijos de call si no los imprime arriba
        elif arbol.nodoTipo != 'call':
            for h in arbol.hijos:
                imprimeAST(h)

    endentacion -= 2


# token actual coincide con el esperado
def match(expectedToken):
    global token, tokenString
    if token == expectedToken:
        # print(f'Match: {token} = {tokenString}')
        token, tokenString = getToken(imprime=False)
    else:
        errorSintaxis(f"Se esperaba {expectedToken} pero se encontró {token}")


# analiza un factor
def factor():
    global token, tokenString

    if token == TokenType.LPAREN:
        match(TokenType.LPAREN)
        t = exp()
        match(TokenType.RPAREN)
        return t

    elif token == TokenType.NUM:
        t = nuevoNodoExp(TipoExpresion.Const)
        t.val = int(tokenString)  # Convertir a entero
        t.valor = int(tokenString)  # Agregar valor numérico
        t.tipo = TokenType.INT  # Agregar tipo
        match(TokenType.NUM)
        return t

    elif token in (TokenType.ID, TokenType.INPUT, TokenType.OUTPUT):
        nombre = tokenString
        match(token)

        if token == TokenType.LPAREN:
            t = NodoArbol('call')
            t.nombre = nombre
            t.hijos = []
            t.lineno = getLineaActual()  # agregado para semantica
            match(TokenType.LPAREN)
            if token != TokenType.RPAREN:
                t.hijos.append(exp())
                while token == TokenType.COMMA:
                    match(TokenType.COMMA)
                    t.hijos.append(exp())
            match(TokenType.RPAREN)
            return t

        elif token == TokenType.LBRACKET:
            t = NodoArbol('var')
            t.nombre = nombre
            t.lineno = getLineaActual()  # agregado para semantica
            match(TokenType.LBRACKET)
            t.tam = exp()  # Aquí se procesa el índice
            match(TokenType.RBRACKET)
            return t

        else:
            t = NodoArbol('var')
            t.nombre = nombre
            t.lineno = getLineaActual()  # agregado para semantica
            return t

    else:
        errorSintaxis("Expresión no válida en factor")


# analiza expresiones simples
def simpleExpression(inicial=None):
    t = inicial if inicial else term()  # inicializa primer término

    while token in (TokenType.PLUS, TokenType.MINUS):
        p = nuevoNodoExp(TipoExpresion.Op)
        p.hijoIzq = t
        if token == TokenType.PLUS:
            p.op = '+'
            match(TokenType.PLUS)
        else:
            p.op = '-'
            match(TokenType.MINUS)
        p.hijoDer = term()
        t = p

    return t


# analiza una expresión completa
def exp():
    global token, tokenString

    if token in (TokenType.ID, TokenType.INPUT, TokenType.OUTPUT):
        nombre = tokenString
        match(token)

        if token == TokenType.LBRACKET:
            # acceso a arreglo
            var_node = NodoArbol('var')
            var_node.nombre = nombre
            match(TokenType.LBRACKET)
            var_node.tam = exp()
            match(TokenType.RBRACKET)

            if token == TokenType.ASSIGN:
                match(TokenType.ASSIGN)
                assign_node = nuevoNodoExp(TipoExpresion.Op)
                assign_node.op = '='
                assign_node.hijoIzq = var_node
                assign_node.hijoDer = exp()
                return assign_node
            else:
                t = simpleExpression(var_node)

        elif token == TokenType.ASSIGN:
            # asignación simple
            var_node = NodoArbol('var')
            var_node.nombre = nombre
            match(TokenType.ASSIGN)
            assign_node = nuevoNodoExp(TipoExpresion.Op)
            assign_node.op = '='
            assign_node.hijoIzq = var_node
            assign_node.hijoDer = exp()
            return assign_node

        elif token == TokenType.LPAREN:
            # llamada a función
            call_node = NodoArbol('call')
            call_node.nombre = nombre
            call_node.hijos = []
            call_node.lineno = getLineaActual()  # agregado para semantica
            match(TokenType.LPAREN)
            if token != TokenType.RPAREN:
                call_node.hijos.append(exp())
                while token == TokenType.COMMA:
                    match(TokenType.COMMA)
                    call_node.hijos.append(exp())
            match(TokenType.RPAREN)
            return call_node

        else:
            # variable simple
            var_node = NodoArbol('var')
            var_node.nombre = nombre
            var_node.lineno = getLineaActual()  # agregado para semantica
            t = simpleExpression(var_node)

    else:
        # caso normal (número, paréntesis)
        t = simpleExpression()

    # checa si viene un operador relacional
    if token in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):
        p = nuevoNodoExp(TipoExpresion.Op)
        p.hijoIzq = t
        if token == TokenType.EQ:
            p.op = '=='
            match(TokenType.EQ)
        elif token == TokenType.NEQ:
            p.op = '!='
            match(TokenType.NEQ)
        elif token == TokenType.LT:
            p.op = '<'
            match(TokenType.LT)
        elif token == TokenType.LTEQ:
            p.op = '<='
            match(TokenType.LTEQ)
        elif token == TokenType.GT:
            p.op = '>'
            match(TokenType.GT)
        elif token == TokenType.GTEQ:
            p.op = '>='
            match(TokenType.GTEQ)
        p.hijoDer = simpleExpression()
        return p
    else:
        return t


# analiza mult y div
def term():
    global token, tokenString
    t = factor()
    while token in (TokenType.MULT, TokenType.DIV):
        p = nuevoNodoExp(TipoExpresion.Op)
        p.hijoIzq = t
        if token == TokenType.MULT:
            p.op = '*'
            match(TokenType.MULT)
        else:
            p.op = '/'
            match(TokenType.DIV)
        p.hijoDer = factor()
        t = p
    return t


# declaración de una variable
def varDeclaration(tipo, id_nombre, id_linea):
    tam = None
    if token == TokenType.LBRACKET:
        match(TokenType.LBRACKET)
        tam = int(tokenString)
        match(TokenType.NUM)
        match(TokenType.RBRACKET)
    match(TokenType.SEMI)
    nodo = NodoArbol('var')
    nodo.tipo = tipo
    nodo.nombre = id_nombre
    nodo.tam = tam
    nodo.lineno = id_linea
    return nodo


# parámetros de una función
def params():
    lista_parametros = []
    # si el  token es void, no hay parámetros
    if token == TokenType.VOID:
        match(TokenType.VOID)
        return lista_parametros

    while True:
        param = NodoArbol('param')
        if token in (TokenType.INT, TokenType.VOID):
            param.tipo = token
            match(token)
            if token == TokenType.ID:
                param.nombre = tokenString
                param.lineno = getLineaActual()  # Captura la línea antes del match
                match(TokenType.ID)
                if token == TokenType.LBRACKET:
                    match(TokenType.LBRACKET)
                    match(TokenType.RBRACKET)
                    param.tam = 'arreglo'
            else:
                errorSintaxis("Se esperaba un identificador de parámetro")
        else:
            errorSintaxis("Se esperaba un tipo de parámetro")

        lista_parametros.append(param)

        if token != TokenType.COMMA:
            break
        match(TokenType.COMMA)

    return lista_parametros


# analiza bloque de código
def analyzeBlock():
    match(TokenType.LBRACE)
    nodo = NodoArbol('compuesto')
    nodo.lineno = getLineaActual()  # agregado para semantica
    nodo.decl = []
    while token in (TokenType.INT, TokenType.VOID):
        nodo.decl.append(declaration())

    nodo.sentencias = []
    while token not in (TokenType.RBRACE, TokenType.ENDFILE):
        stmt = statement()
        if stmt is not None:  # evita agregar None
            nodo.sentencias.append(stmt)

    match(TokenType.RBRACE)
    return nodo


# analiza sentencia if
def selectionStmt():
    nodo = NodoArbol('if')
    nodo.lineno = getLineaActual()  # agregado para semanticas
    match(TokenType.IF)
    match(TokenType.LPAREN)
    nodo.condicion = exp()
    match(TokenType.RPAREN)
    nodo.hijoIzq = statement()
    if token == TokenType.ELSE:
        match(TokenType.ELSE)
        nodo.hijoDer = statement()
    return nodo


# analiza sentencia while
def iterationStmt():
    nodo = NodoArbol('while')
    nodo.lineno = getLineaActual()  # agregado para semanticas
    match(TokenType.WHILE)
    match(TokenType.LPAREN)
    nodo.condicion = exp()
    match(TokenType.RPAREN)
    nodo.hijoIzq = statement()
    return nodo


# analiza cualquier tipo de sentencia
def statement():
    global token
    if token == TokenType.IF:
        return selectionStmt()
    elif token == TokenType.WHILE:
        return iterationStmt()
    elif token == TokenType.RETURN:
        return returnStmt()
    elif token == TokenType.LBRACE:
        return analyzeBlock()
    elif token in (TokenType.ID, TokenType.INPUT, TokenType.OUTPUT, TokenType.LPAREN, TokenType.NUM, TokenType.SEMI):
        return expressionStmt()
    else:
        errorSintaxis(f"Token inesperado en statement: {token}")


# analiza declaración de una función
def funDeclaration(tipo, id_nombre, id_linea):
    match(TokenType.LPAREN)
    parametros = params()
    match(TokenType.RPAREN)
    cuerpo = analyzeBlock()
    nodo = NodoArbol('fun')
    nodo.tipo = tipo
    nodo.nombre = id_nombre
    nodo.parametros = parametros
    nodo.cuerpo = cuerpo
    nodo.lineno = id_linea
    return nodo


# analiza una declaración variable o función
def declaration():
    if token in (TokenType.INT, TokenType.VOID):
        tipo = token
        match(token)
        id_nombre = tokenString
        id_linea = getLineaActual()  # Captura la línea antes del match
        match(TokenType.ID)
        if token == TokenType.LPAREN:
            return funDeclaration(tipo, id_nombre, id_linea)
        else:
            return varDeclaration(tipo, id_nombre, id_linea)
    else:
        errorSintaxis("Se esperaba tipo de dato")


# analiza programa completo
def program():
    declaraciones = []
    while token in (TokenType.INT, TokenType.VOID):  # se espera  declaración
        declaraciones.append(declaration())
    return declaraciones


def parser(imprime=True):
    global token, tokenString, endentacion
    token, tokenString = getToken(imprime=False)
    # print(f'Primer token: {token} = {tokenString}')
    AST = program()
    if token != TokenType.ENDFILE:
        errorSintaxis("El archivo no terminó correctamente")
    elif imprime:
        endentacion = 0
        for nodo in AST:
            imprimeAST(nodo)
    return AST


# analiza sentencia return
def returnStmt():
    match(TokenType.RETURN)
    nodo = NodoArbol('return')
    nodo.lineno = getLineaActual()  # agregado para semantica
    if token != TokenType.SEMI:
        nodo.retorno = exp()
    match(TokenType.SEMI)
    return nodo


# analiza sentencia de expresión
def expressionStmt():
    global token
    nodo = NodoArbol('exp-stmt')
    nodo.lineno = getLineaActual()  # agregado para semantica
    if token == TokenType.SEMI:
        match(TokenType.SEMI)
        nodo.hijoIzq = None
    else:
        nodo.hijoIzq = exp()
        match(TokenType.SEMI)

    return nodo


endentacion = 0
