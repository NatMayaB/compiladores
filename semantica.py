from globalTypes import *
from parser import *
from lexer import *

tabla_stack = []
todas_las_tablas = []
contador_bloques = 0
funcion_actual = None

# --- NUEVO: sets para evitar duplicados y errores repetidos ---
variables_por_scope = {}
errores_reportados = set()
variables_no_declaradas_reportadas = set()


def nueva_tabla(nombre):
    tabla = {
        'nombre': nombre,
        'entradas': []
    }
    tabla_stack.append(tabla)
    todas_las_tablas.append(tabla)


def salir_tabla():
    tabla_stack.pop()


def insertar(nombre, tipo, linea, es_array=False, tam=None, param=False):
    actual = tabla_stack[-1]
    scope_name = actual['nombre']
    if scope_name not in variables_por_scope:
        variables_por_scope[scope_name] = set()
    clave = (nombre, tipo, linea)
    if clave in variables_por_scope[scope_name]:
        return  # Ya insertada en este scope
    variables_por_scope[scope_name].add(clave)
    actual['entradas'].append({
        'nombre': nombre,
        'tipo': tipo.name if isinstance(tipo, TokenType) else str(tipo),
        'linea': linea if linea is not None else '?',
        'es_array': es_array,
        'tam': tam if isinstance(tam, int) else None,
        'param': param
    })


def imprimir_tablas():
    from tabulate import tabulate

    for tabla in todas_las_tablas:
        print(f"\n Scope: {tabla['nombre']}")
        if not tabla['entradas']:
            print("(sin variables declaradas)")
            continue

        filas = []
        for e in tabla['entradas']:
            filas.append([
                e['nombre'],
                e['tipo'],
                "Sí" if e['es_array'] else "No",
                e['linea']
            ])

        print(tabulate(filas, headers=[
              "Nombre", "Tipo", "¿Es array?", "Línea"], tablefmt="grid"))


def recorrer_arbol(nodo, scope='global', es_declaracion=False):
    if nodo is None:
        return

    if nodo.nodoTipo == 'fun':
        # Insertar la firma de la función en el scope global
        if len(tabla_stack) == 1:  # Solo si estamos en global
            insertar(nodo.nombre, nodo.tipo, getattr(nodo, 'lineno', '?'))
        # Crear scope para la función
        nueva_tabla(nodo.nombre)
        for param in nodo.parametros:
            if param.nombre is not None and param.tipo is not None:
                es_array = param.tam == 'arreglo' or (isinstance(
                    param.tam, str) and param.tam.endswith('[]'))
                insertar(param.nombre, param.tipo, getattr(
                    param, 'lineno', '?'), es_array, param= True)
        # Recorrer declaraciones y sentencias del cuerpo de la función
        for decl in nodo.cuerpo.decl:
            recorrer_arbol(decl, nodo.nombre, es_declaracion=True)
        for stmt in nodo.cuerpo.sentencias:
            recorrer_arbol(stmt, nodo.nombre)
        salir_tabla()

    elif nodo.nodoTipo == 'var':
        # Solo insertar si es una declaración
        if es_declaracion:
            if len(tabla_stack) == 1 or scope == 'global':
                es_array = nodo.tam is not None and nodo.tam != 'arreglo'
                tam = nodo.tam if isinstance(nodo.tam, int) else None
                insertar(nodo.nombre, nodo.tipo, getattr(
                    nodo, 'lineno', '?'), es_array, tam)

            else:
                es_array = nodo.tam is not None and nodo.tam != 'arreglo'
                tam = nodo.tam if isinstance(nodo.tam, int) else None
                insertar(nodo.nombre, nodo.tipo, getattr(
                    nodo, 'lineno', '?'), es_array, tam)

        # No insertar en usos

    # NO crear scopes para bloques internos
    elif nodo.nodoTipo == 'compuesto':
        for decl in nodo.decl:
            recorrer_arbol(decl, scope, es_declaracion=True)
        for stmt in nodo.sentencias:
            recorrer_arbol(stmt, scope)

    elif nodo.nodoTipo == 'param':
        # Solo insertar si es_declaracion (pero en la práctica, solo se insertan en la lista de parámetros de la función)
        if es_declaracion:
            es_array = nodo.tam == 'arreglo' or (
                isinstance(nodo.tam, str) and nodo.tam.endswith('[]'))
            insertar(nodo.nombre, nodo.tipo, getattr(
                nodo, 'lineno', '?'), es_array, param=True)

    elif nodo.nodoTipo == 'return':
        recorrer_arbol(nodo.retorno, scope)

    elif nodo.nodoTipo == 'exp-stmt':
        recorrer_arbol(nodo.hijoIzq, scope)

    elif nodo.nodoTipo == 'if':
        recorrer_arbol(nodo.condicion, scope)
        recorrer_arbol(nodo.hijoIzq, scope)
        if nodo.hijoDer:
            recorrer_arbol(nodo.hijoDer, scope)

    elif nodo.nodoTipo == 'while':
        recorrer_arbol(nodo.condicion, scope)
        recorrer_arbol(nodo.hijoIzq, scope)

    elif nodo.nodoTipo == 'call':
        if nodo.nombre == 'input':
            nodo.tipo = TokenType.INT
        elif nodo.nombre == 'output':
            if len(nodo.hijos) > 0:
                # Si el argumento es una variable no declarada, no reportar error
                if isinstance(nodo.hijos[0], NodoArbol) and nodo.hijos[0].nodoTipo == 'var':
                    entry = buscar_global(nodo.hijos[0].nombre)
                    if not entry:
                        return  # No reportar error si la variable no está declarada

                # Si el argumento es una llamada a función, verificar si tiene variables no declaradas
                if isinstance(nodo.hijos[0], NodoArbol) and nodo.hijos[0].nodoTipo == 'call':
                    tiene_var_no_declarada = False
                    for arg in nodo.hijos[0].hijos:
                        if isinstance(arg, NodoArbol) and arg.nodoTipo == 'var':
                            if buscar_global(arg.nombre) is None:
                                tiene_var_no_declarada = True
                                break
                    if tiene_var_no_declarada:
                        return  # No reportar error si hay variables no declaradas

                checkTipos(nodo.hijos[0])
                # Solo reportar error si el argumento no es una llamada a función con variables no declaradas
                if getattr(nodo.hijos[0], 'tipo', None) != TokenType.INT:
                    reportar_error(nodo, "output debe recibir un entero")
            nodo.tipo = TokenType.VOID
        else:
            entry = buscar_global(nodo.nombre)
            if entry:
                nodo.tipo = entry.get('tipo', TokenType.VOID)
                # Verificar argumentos de la función
                if hasattr(nodo, 'hijos') and len(nodo.hijos) > 0:
                    # Buscar la definición de la función para verificar argumentos
                    for tabla in todas_las_tablas:
                        if tabla['nombre'] == nodo.nombre:
                            params = [e for e in tabla['entradas']
                                      if e['nombre'] != nodo.nombre]
                            if len(nodo.hijos) != len(params):
                                reportar_error(
                                    nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, número de argumentos incorrecto para función '{nodo.nombre}'.")
                                break  # No intentar comparar tipos si el número de argumentos es incorrecto
                            # Verificar tipo de cada argumento
                            for i, (arg, param) in enumerate(zip(nodo.hijos, params)):
                                checkTipos(arg)
                                # Buscar en tabla de símbolos si el argumento es arreglo
                                arg_is_array = False
                                if isinstance(arg, NodoArbol) and arg.nodoTipo == 'var':
                                    arg_entry = buscar_global(arg.nombre)
                                    if arg_entry and arg_entry.get('es_array', False):
                                        arg_is_array = True
                                # Si el parámetro es un arreglo
                                param_is_array = param['es_array']
                                param_is_int = param['tipo'] == TokenType.INT.name or param['tipo'] == str(
                                    TokenType.INT)
                                arg_is_error = getattr(arg, 'tipo', None) == TokenType.ERROR or getattr(
                                    arg, 'tipo', None) == 'error'
                                if arg_is_error or getattr(arg, 'tipo', None) is None:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser '{param['tipo'].lower()}', pero se encontró 'error'.")
                                elif param_is_array and not arg_is_array:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser un arreglo.")
                                elif param_is_int and arg_is_array:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser 'int', pero se encontró 'arreglo'.")
                                elif param_is_int and getattr(arg, 'tipo', None) != TokenType.INT:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser 'int', pero se encontró '{getattr(arg, 'tipo', None)}'.")
                            break
            else:
                reportar_error(
                    nodo, f"Llamada a función no declarada: {nodo.nombre}")
                nodo.tipo = TokenType.VOID

    elif nodo.nodoTipo == 'return':
        if nodo.retorno:
            checkTipos(nodo.retorno)
            tipo_retorno = getattr(nodo.retorno, 'tipo', None)

            # Obtener tipo de la función actual desde la tabla global
            tipo_funcion = None
            if len(tabla_stack) > 1:
                nombre_funcion = tabla_stack[-1]['nombre']
                for tabla in todas_las_tablas:
                    if tabla['nombre'] == 'global':
                        for entry in tabla['entradas']:
                            if entry['nombre'] == nombre_funcion:
                                tipo_funcion = entry['tipo']
                                break

            if tipo_funcion == TokenType.VOID:
                reportar_error(
                    nodo.retorno, "No se puede retornar un valor en una función void")
            elif tipo_funcion == TokenType.INT and tipo_retorno != TokenType.INT:
                reportar_error(
                    nodo.retorno, "El return debe devolver un entero")

    elif nodo.nodoTipo == 'fun':
        funcion_actual = nodo
        if nodo.tipo == TokenType.INT and not tiene_return(nodo.cuerpo):
            reportar_error(
                nodo, f"La función {nodo.nombre} no retorna un valor")

    # Verificar variables no declaradas en el cuerpo de la función
    if nodo.nodoTipo == 'compuesto':
        for stmt in nodo.sentencias:
            if isinstance(stmt, NodoArbol) and stmt.nodoTipo == 'exp-stmt':
                if stmt.hijoIzq and isinstance(stmt.hijoIzq, NodoArbol) and stmt.hijoIzq.nodoTipo == 'var':
                    entry = buscar_global(stmt.hijoIzq.nombre)
                    if not entry:
                        reportar_error(
                            stmt, f"Línea {getattr(stmt, 'lineno', '?')}: Error, variable '{stmt.hijoIzq.nombre}' no declarada.")

    # Por si quedaron hijos en lista .hijos que aún no se recorrieron
    for campo in ['hijos', 'hijoIzq', 'hijoDer', 'condicion', 'retorno', 'tam']:
        sub = getattr(nodo, campo, None)
        if isinstance(sub, list):
            for item in sub:
                if isinstance(item, NodoArbol):
                    checkTipos(item)
        elif isinstance(sub, NodoArbol):
            checkTipos(sub)


def tabla(tree, imprime=True):
    nueva_tabla("global")
    for nodo in tree:
        recorrer_arbol(nodo, es_declaracion=True)
    if imprime:
        imprimir_tablas()


Error = False  # Global para controlar si hubo errores


def semantica(tree, imprime=True):
    tabla(tree, imprime)  # Ya la tenemos funcionando
    if imprime:
        print("\nVerificación de tipos...")
    for nodo in tree:
        checkTipos(nodo)
    # Imprime los errores al final
    if Error:
        print("\nSe encontraron errores semánticos en el código:")
        for linea, mensaje in sorted(errores_reportados):
            print(f"Línea {linea}: {mensaje}")
    else:
        print("\nNo se encontraron errores semánticos.")


def checkTipos(nodo):
    global Error, funcion_actual, tabla_stack
    if nodo is None:
        return None

    # Si es función, push de su tabla de símbolos
    if nodo.nodoTipo == 'fun':
        # Busca la tabla de la función
        for tabla in todas_las_tablas:
            if tabla['nombre'] == nodo.nombre:
                tabla_stack.append(tabla)
                break
        funcion_actual = nodo
        # Recorre el cuerpo de la función
        checkTipos(nodo.cuerpo)
        tabla_stack.pop()
        return

    # Si es variable, obtener su tipo
    if nodo.nodoTipo == 'var':
        entry = buscar_global(nodo.nombre)
        if entry:
            nodo.tipo = entry['tipo']
            if entry['es_array'] and hasattr(nodo, 'tam') and isinstance(nodo.tam, NodoArbol):
                if nodo.tam == 'arreglo':
                    return
                checkTipos(nodo.tam)
                if getattr(nodo.tam, 'tipo', None) != TokenType.INT:
                    reportar_error(
                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, el índice debe ser entero para el arreglo '{nodo.nombre}'.")

                # Verificar si el índice es una constante
                if hasattr(nodo.tam, 'exp') and nodo.tam.exp == TipoExpresion.Const:
                    indice = nodo.tam.val
                    tam_max = entry.get('tam')
                    if isinstance(tam_max, int) and indice >= tam_max:
                        reportar_error(
                            nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, índice {indice} fuera del límite del arreglo '{nodo.nombre}' (tamaño {tam_max}).")
                # Verificar si el índice es un número literal
                elif hasattr(nodo.tam, 'val') and isinstance(nodo.tam.val, int):
                    indice = nodo.tam.val
                    tam_max = entry.get('tam')
                    if isinstance(tam_max, int) and indice >= tam_max:
                        reportar_error(
                            nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, índice {indice} fuera del límite del arreglo '{nodo.nombre}' (tamaño {tam_max}).")
        else:
            reportar_error(
                nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, variable '{nodo.nombre}' no declarada.")
            nodo.tipo = TokenType.INT
        return

    # Detectar variables no declaradas en expresiones
    if nodo.nodoTipo == 'exp-stmt' and nodo.hijoIzq is not None:
        if isinstance(nodo.hijoIzq, NodoArbol) and nodo.hijoIzq.nodoTipo == 'var':
            entry = buscar_global(nodo.hijoIzq.nombre)
            if not entry:
                reportar_error(
                    nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, variable '{nodo.hijoIzq.nombre}' no declarada.")

    # Recorrido postorden
    for h in nodo.hijos:
        checkTipos(h)
    checkTipos(nodo.hijoIzq)
    checkTipos(nodo.hijoDer)
    checkTipos(nodo.condicion)
    checkTipos(nodo.retorno)

    if hasattr(nodo, 'tam') and isinstance(nodo.tam, NodoArbol):
        checkTipos(nodo.tam)

    if nodo.nodoTipo == 'expresion':
        if nodo.hijoIzq:
            checkTipos(nodo.hijoIzq)
        if nodo.hijoDer:
            checkTipos(nodo.hijoDer)

        tipo_izq = getattr(nodo.hijoIzq, 'tipo', None)
        tipo_der = getattr(nodo.hijoDer, 'tipo', None)

        # Verificar si alguno de los operandos es una variable no declarada
        var_izq_no_declarada = (isinstance(nodo.hijoIzq, NodoArbol) and
                                nodo.hijoIzq.nodoTipo == 'var' and
                                buscar_global(nodo.hijoIzq.nombre) is None)
        var_der_no_declarada = (isinstance(nodo.hijoDer, NodoArbol) and
                                nodo.hijoDer.nodoTipo == 'var' and
                                buscar_global(nodo.hijoDer.nombre) is None)

        # Si alguna variable no está declarada, no reportar errores de tipo
        if var_izq_no_declarada or var_der_no_declarada:
            return

        # Solo reportar errores de tipo si ambos operandos tienen tipo definido
        if tipo_izq is not None and tipo_der is not None:
            if nodo.op in {'+', '-', '*', '/'}:
                # Las operaciones aritméticas siempre son de tipo INT
                nodo.tipo = TokenType.INT
                # No reportar error de tipo en operaciones aritméticas
                return

            elif nodo.op in {'==', '!=', '<', '<=', '>', '>='}:
                # Las comparaciones siempre son de tipo INT
                nodo.tipo = TokenType.INT
                # No reportar error de tipo en comparaciones
                return

            elif nodo.op == '=':
                # Verificar si el lado izquierdo es un array
                if isinstance(nodo.hijoIzq, NodoArbol) and nodo.hijoIzq.nodoTipo == 'var':
                    entry = buscar_global(nodo.hijoIzq.nombre)
                    if entry and entry['es_array']:
                        if tipo_der != TokenType.INT:
                            reportar_error(
                                nodo, "Asignación a array debe ser de tipo entero")
                        # Verificar el índice del array
                        if hasattr(nodo.hijoIzq, 'tam') and isinstance(nodo.hijoIzq.tam, NodoArbol):
                            if nodo.hijoIzq.tam.exp == TipoExpresion.Const:
                                indice = nodo.hijoIzq.tam.val
                                tam_max = entry.get('tam')
                                if isinstance(tam_max, int) and indice >= tam_max:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, índice {indice} fuera del límite del arreglo '{nodo.hijoIzq.nombre}' (tamaño {tam_max}).")
                elif tipo_izq != tipo_der:
                    reportar_error(
                        nodo, "Asignación entre tipos incompatibles")
                nodo.tipo = tipo_izq

    elif nodo.nodoTipo == 'call':
        if nodo.nombre == 'input':
            nodo.tipo = TokenType.INT
        elif nodo.nombre == 'output':
            if len(nodo.hijos) > 0:
                # Si el argumento es una variable no declarada, no reportar error
                if isinstance(nodo.hijos[0], NodoArbol) and nodo.hijos[0].nodoTipo == 'var':
                    entry = buscar_global(nodo.hijos[0].nombre)
                    if not entry:
                        return  # No reportar error si la variable no está declarada

                # Si el argumento es una llamada a función, verificar si tiene variables no declaradas
                if isinstance(nodo.hijos[0], NodoArbol) and nodo.hijos[0].nodoTipo == 'call':
                    tiene_var_no_declarada = False
                    for arg in nodo.hijos[0].hijos:
                        if isinstance(arg, NodoArbol) and arg.nodoTipo == 'var':
                            if buscar_global(arg.nombre) is None:
                                tiene_var_no_declarada = True
                                break
                    if tiene_var_no_declarada:
                        return  # No reportar error si hay variables no declaradas

                checkTipos(nodo.hijos[0])
                # Solo reportar error si el argumento no es una llamada a función con variables no declaradas
                if getattr(nodo.hijos[0], 'tipo', None) != TokenType.INT:
                    reportar_error(nodo, "output debe recibir un entero")
            nodo.tipo = TokenType.VOID
        else:
            entry = buscar_global(nodo.nombre)
            if entry:
                nodo.tipo = entry.get('tipo', TokenType.VOID)
                # Verificar argumentos de la función
                if hasattr(nodo, 'hijos') and len(nodo.hijos) > 0:
                    # Buscar la definición de la función para verificar argumentos
                    for tabla in todas_las_tablas:
                        if tabla['nombre'] == nodo.nombre:
                            params = [e for e in tabla['entradas']
                                      if e['nombre'] != nodo.nombre]
                            if len(nodo.hijos) != len(params):
                                reportar_error(
                                    nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, número de argumentos incorrecto para función '{nodo.nombre}'.")
                                break  # No intentar comparar tipos si el número de argumentos es incorrecto
                            # Verificar tipo de cada argumento
                            for i, (arg, param) in enumerate(zip(nodo.hijos, params)):
                                checkTipos(arg)
                                # Buscar en tabla de símbolos si el argumento es arreglo
                                arg_is_array = False
                                if isinstance(arg, NodoArbol) and arg.nodoTipo == 'var':
                                    arg_entry = buscar_global(arg.nombre)
                                    if arg_entry and arg_entry.get('es_array', False):
                                        arg_is_array = True
                                # Si el parámetro es un arreglo
                                param_is_array = param['es_array']
                                param_is_int = param['tipo'] == TokenType.INT.name or param['tipo'] == str(
                                    TokenType.INT)
                                arg_is_error = getattr(arg, 'tipo', None) == TokenType.ERROR or getattr(
                                    arg, 'tipo', None) == 'error'
                                if arg_is_error or getattr(arg, 'tipo', None) is None:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser '{param['tipo'].lower()}', pero se encontró 'error'.")
                                elif param_is_array and not arg_is_array:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser un arreglo.")
                                elif param_is_int and arg_is_array:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser 'int', pero se encontró 'arreglo'.")
                                elif param_is_int and getattr(arg, 'tipo', None) != TokenType.INT:
                                    reportar_error(
                                        nodo, f"Línea {getattr(nodo, 'lineno', '?')}: Error, argumento {i+1} debe ser 'int', pero se encontró '{getattr(arg, 'tipo', None)}'.")
                            break
            else:
                reportar_error(
                    nodo, f"Llamada a función no declarada: {nodo.nombre}")
                nodo.tipo = TokenType.VOID

    elif nodo.nodoTipo == 'return':
        if nodo.retorno:
            checkTipos(nodo.retorno)
            tipo_retorno = getattr(nodo.retorno, 'tipo', None)

            # Obtener tipo de la función actual desde la tabla global
            tipo_funcion = None
            if len(tabla_stack) > 1:
                nombre_funcion = tabla_stack[-1]['nombre']
                for tabla in todas_las_tablas:
                    if tabla['nombre'] == 'global':
                        for entry in tabla['entradas']:
                            if entry['nombre'] == nombre_funcion:
                                tipo_funcion = entry['tipo']
                                break

            if tipo_funcion == TokenType.VOID:
                reportar_error(
                    nodo.retorno, "No se puede retornar un valor en una función void")
            elif tipo_funcion == TokenType.INT and tipo_retorno != TokenType.INT:
                reportar_error(
                    nodo.retorno, "El return debe devolver un entero")

    elif nodo.nodoTipo == 'fun':
        funcion_actual = nodo
        if nodo.tipo == TokenType.INT and not tiene_return(nodo.cuerpo):
            reportar_error(
                nodo, f"La función {nodo.nombre} no retorna un valor")

    # Verificar variables no declaradas en el cuerpo de la función
    if nodo.nodoTipo == 'compuesto':
        for stmt in nodo.sentencias:
            if isinstance(stmt, NodoArbol) and stmt.nodoTipo == 'exp-stmt':
                if stmt.hijoIzq and isinstance(stmt.hijoIzq, NodoArbol) and stmt.hijoIzq.nodoTipo == 'var':
                    entry = buscar_global(stmt.hijoIzq.nombre)
                    if not entry:
                        reportar_error(
                            stmt, f"Línea {getattr(stmt, 'lineno', '?')}: Error, variable '{stmt.hijoIzq.nombre}' no declarada.")

    # Por si quedaron hijos en lista .hijos que aún no se recorrieron
    for campo in ['hijos', 'hijoIzq', 'hijoDer', 'condicion', 'retorno', 'tam']:
        sub = getattr(nodo, campo, None)
        if isinstance(sub, list):
            for item in sub:
                if isinstance(item, NodoArbol):
                    checkTipos(item)
        elif isinstance(sub, NodoArbol):
            checkTipos(sub)


def reportar_error(nodo, mensaje):
    global Error, variables_no_declaradas_reportadas
    Error = True
    linea = getattr(nodo, 'lineno', '?')
    try:
        linea = int(linea)
    except Exception:
        linea = 0
    if linea == 0 or linea == '?':
        return  # Ignora errores sin línea válida

    # Solo reportar el primer error de variable no declarada por línea
    if "variable '" in mensaje and "no declarada" in mensaje:
        import re
        m = re.search(r"variable '([^']+)' no declarada", mensaje)
        if m:
            var = m.group(1)
            clave_var = (linea, var)
            if clave_var in variables_no_declaradas_reportadas:
                return  # Ya reportado para esta línea
            variables_no_declaradas_reportadas.add(clave_var)

    clave_error = (linea, mensaje)
    if clave_error in errores_reportados:
        return  # Ya reportado
    errores_reportados.add(clave_error)
    # Ya no imprimimos el error aquí, solo lo guardamos para el resumen final


def buscar_global(nombre):
    for tabla in reversed(tabla_stack):
        for entry in tabla['entradas']:
            if entry['nombre'] == nombre:
                return entry
    return None


def tiene_return(nodo):
    if nodo is None:
        return False

    if nodo.nodoTipo == 'return':
        return nodo.retorno is not None  # Solo cuenta si tiene valor

    if nodo.nodoTipo == 'if':
        return (
            tiene_return(nodo.hijoIzq) and
            tiene_return(nodo.hijoDer)
        ) if nodo.hijoDer else False

    if nodo.nodoTipo == 'while':
        return False  # no garantiza ejecución del return

    if hasattr(nodo, 'sentencias'):
        return any(tiene_return(s) for s in nodo.sentencias)

    if hasattr(nodo, 'hijoIzq') and tiene_return(nodo.hijoIzq):
        return True

    if hasattr(nodo, 'hijoDer') and tiene_return(nodo.hijoDer):
        return True

    if hasattr(nodo, 'hijos'):
        return any(tiene_return(h) for h in nodo.hijos)

    return False


def verificar_errores(tree):
    global Error, errores_reportados
    Error = False
    errores_reportados.clear()

    print("\n🔎 Verificación de tipos...")

    # Primero construimos la tabla de símbolos
    tabla(tree, False)  # False para no imprimir las tablas aquí

    # Luego verificamos los tipos
    for nodo in tree:
        checkTipos(nodo)

    # Verificar variables no declaradas en el cuerpo de las funciones
    for nodo in tree:
        if nodo.nodoTipo == 'fun':
            for stmt in nodo.cuerpo.sentencias:
                if isinstance(stmt, NodoArbol) and stmt.nodoTipo == 'exp-stmt':
                    if stmt.hijoIzq and isinstance(stmt.hijoIzq, NodoArbol) and stmt.hijoIzq.nodoTipo == 'var':
                        entry = buscar_global(stmt.hijoIzq.nombre)
                        if not entry:
                            reportar_error(
                                stmt, f"Línea {getattr(stmt, 'lineno', '?')}: Error, variable '{stmt.hijoIzq.nombre}' no declarada.")

    if Error:
        print("\nSe encontraron errores semánticos en el código:")
        for linea, mensaje in sorted(errores_reportados):
            print(f"Línea {linea}: {mensaje}")
    else:
        print("\nNo se encontraron errores semánticos.")
