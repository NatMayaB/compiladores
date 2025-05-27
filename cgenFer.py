from globalTypes import *
import semantica
from parser import *
import sys

temp_count = 0
output = []
offsets = {}  # { varName: offset }
offset_actual = 0
label_count = 0


def nueva_etiqueta():
    global label_count
    etiqueta = f"L{label_count}"
    label_count += 1
    return etiqueta


def nueva_temp():
    global temp_count
    reg = f"$t{temp_count % 10}"
    temp_count += 1
    return reg


def generar_data_section():
    data_lines = [".data"]
    global_scope = semantica.tabla_stack[0]  # La primera tabla es la global
    for entry in global_scope['entradas']:
        # Solo incluir variables globales, no funciones
        if entry['nombre'] != 'main' and not any(tabla['nombre'] == entry['nombre'] for tabla in semantica.todas_las_tablas[1:]):
            if entry.get('es_array', False) and entry.get('tam'):
                data_lines.append(
                    f"{entry['nombre']}: .space {int(entry['tam'])*4}")
            else:
                data_lines.append(f"{entry['nombre']}: .word 0")
    return data_lines


def codeGen(AST, filename):
    # Importar banderas de error actualizadas
    from lexer import lexer_error
    from parser import parser_error
    from semantica import Error as semantic_error

    # Si hay errores léxicos, no se genera código
    if lexer_error:
        print(
            "\033[91mSe detectaron errores léxicos | Generación de código abortada.\033[0m")
        return  # No genera nada

    # Si hay errores de análisis sintáctico, mostrar advertencia pero continuar
    if parser_error:
        print("\033[93mAdvertencia: Se detectaron errores sintácticos, pero se continuará con la generación de código.\033[0m")

    # Si hay errores semánticos, mostrar advertencia pero continuar
    if semantic_error:
        print("\033[93mAdvertencia: Se detectaron errores semánticos, pero se continuará con la generación de código.\033[0m")

    global output, temp_count, offsets, offset_actual
    output = []
    temp_count = 0
    offsets = {}
    offset_actual = 0

    # Generar sección .data primero
    data_section = generar_data_section()
    output.extend(data_section)
    output.append(".text")

    # Primero generar todas las funciones excepto main
    for nodo in AST:
        if nodo.nodoTipo == 'fun' and nodo.nombre != "main":
            scope = None
            for tabla in semantica.todas_las_tablas:
                if tabla['nombre'] == nodo.nombre:
                    scope = tabla
                    break
            if scope:
                offsets = {}
                offset_actual = 0
                param_index = 0
                # Primero cuenta cuántos parámetros hay
                param_entries = [
                    entry for entry in scope['entradas'] if entry.get('param', False)]
                for entry in scope['entradas']:
                    if entry.get('param', False):
                        # Offset positivo respecto a $fp: 8 + 4 * i
                        offsets[entry['nombre']] = 8 + 4 * param_index
                        param_index += 1
                    else:
                        if entry.get('es_array', False) and entry.get('tam'):
                            offset_actual -= int(entry['tam']) * 4
                        else:
                            offset_actual -= 4
                        offsets[entry['nombre']] = offset_actual

            output.append(f"{nodo.nombre}:")
            genFun(nodo)

    # Luego generar main
    for nodo in AST:
        if nodo.nodoTipo == 'fun' and nodo.nombre == "main":
            scope = None
            for tabla in semantica.todas_las_tablas:
                if tabla['nombre'] == nodo.nombre:
                    scope = tabla
                    break
            if scope:
                offsets = {}
                offset_actual = 0
                param_index = 0
                param_entries = [
                    entry for entry in scope['entradas'] if entry.get('param', False)]
                for entry in scope['entradas']:
                    if entry.get('param', False):
                        offsets[entry['nombre']] = 8 + 4 * param_index
                        param_index += 1
                    else:
                        if entry.get('es_array', False) and entry.get('tam'):
                            offset_actual -= int(entry['tam']) * 4
                        else:
                            offset_actual -= 4
                        offsets[entry['nombre']] = offset_actual

            output.append(".globl main")
            output.append("main:")
            genFun(nodo, is_main=True)

    with open(filename, "w") as f:
        for line in output:
            f.write(line + "\n")


def genFun(nodo, is_main=False):
    output.append("sub $sp, $sp, 8")      # espacio para $fp y $ra
    output.append("sw $ra, 4($sp)")
    output.append("sw $fp, 0($sp)")
    output.append("move $fp, $sp")

    # Calcular espacio para variables locales
    locals_only = [offset for offset in offsets.values() if offset < 0]
    local_size = -min(locals_only) if locals_only else 0
    if local_size > 0:
        output.append(f"sub $sp, $sp, {local_size}")

    # Detectar tipo de función
    tipo_funcion = nodo.tipo

    # Bandera para saber si hubo return
    hubo_return = False
    uso_output = False

    # Generar cuerpo de la función
    if nodo.cuerpo:
        for stmt in nodo.cuerpo.sentencias:
            genStmt(stmt)
            if stmt.nodoTipo == 'return':
                hubo_return = True
                break

    # Si es función int y no hubo return, devolver 1 por defecto
    if tipo_funcion == TokenType.INT and not hubo_return:
        output.append("li $v0, 1  # return por defecto")

    # Liberar espacio para locales si fue reservado
    if local_size > 0:
        output.append(f"add $sp, $sp, {local_size}")

    if is_main:
        if not hubo_return:
            # Main caso int y void
            if tipo_funcion == TokenType.INT:
                output.append("move $a0, $v0")
                output.append("li $v0, 1")         # syscall: print int
                output.append("syscall")
            output.append("li $v0, 10")        # syscall: exit
            output.append("syscall")
    else:
        if not hubo_return:
            output.append("move $sp, $fp")
            output.append("lw $fp, 0($sp)")
            output.append("lw $ra, 4($sp)")
            output.append("add $sp, $sp, 8")
            output.append("jr $ra")


def genStmt(nodo):
    if nodo.nodoTipo == 'exp-stmt':
        if nodo.hijoIzq:
            genExp(nodo.hijoIzq)

    elif nodo.nodoTipo == 'expresion' and nodo.op == '=':
        var_name = nodo.hijoIzq.nombre
        valor = genExp(nodo.hijoDer)
        offset = offsets.get(var_name)
        if offset is not None:
            output.append(f"sw {valor}, {offset}($fp)  # {var_name} = ...")
        else:
            output.append(
                f"# ERROR: variable {var_name} no tiene offset asignado")

    elif nodo.nodoTipo == 'if':
        et_else = nueva_etiqueta()
        et_end = nueva_etiqueta()

        cond_reg = genExp(nodo.condicion)
        output.append(f"beq {cond_reg}, $zero, {et_else}  # if false -> else")

        if nodo.hijoIzq:
            if nodo.hijoIzq.nodoTipo == 'compuesto':
                for stmt in nodo.hijoIzq.sentencias:
                    genStmt(stmt)
            else:
                genStmt(nodo.hijoIzq)

        output.append(f"j {et_end}")

        output.append(f"{et_else}:")
        if nodo.hijoDer:
            if nodo.hijoDer.nodoTipo == 'compuesto':
                for stmt in nodo.hijoDer.sentencias:
                    genStmt(stmt)
            else:
                genStmt(nodo.hijoDer)

        output.append(f"{et_end}:")

    elif nodo.nodoTipo == 'while':
        et_start = nueva_etiqueta()
        et_exit = nueva_etiqueta()

        output.append(f"{et_start}:")
        cond_reg = genExp(nodo.condicion)
        output.append(
            f"beq {cond_reg}, $zero, {et_exit}  # while false -> exit")

        if nodo.hijoIzq.nodoTipo == 'compuesto':
            for stmt in nodo.hijoIzq.sentencias:
                genStmt(stmt)
        else:
            genStmt(nodo.hijoIzq)
        output.append(f"j {et_start}")
        output.append(f"{et_exit}:")

    elif nodo.nodoTipo == 'return':
        if nodo.retorno:
            valor = genExp(nodo.retorno)
            output.append(f"move $v0, {valor}  # return valor")
        # Agregar código para limpiar la pila y retornar
        output.append("move $sp, $fp")
        output.append("lw $fp, 0($sp)")
        output.append("lw $ra, 4($sp)")
        output.append("add $sp, $sp, 8")
        output.append("jr $ra")
        return  # Detener generación tras return


def genExp(nodo):
    if nodo.exp == TipoExpresion.Const:
        reg = nueva_temp()
        output.append(f"li {reg}, {nodo.val}")
        return reg

    elif nodo.nodoTipo == 'var':
        offset = offsets.get(nodo.nombre)
        reg = nueva_temp()
        # Detectar si es variable global
        global_scope = semantica.tabla_stack[0]
        is_global = any(entry['nombre'] ==
                        nodo.nombre for entry in global_scope['entradas'])
        if offset is not None and not is_global:
            if nodo.tam:
                indice_reg = genExp(nodo.tam)
                output.append(f"li {reg}, {offset}")
                output.append(f"mul {indice_reg}, {indice_reg}, 4")
                output.append(f"add {reg}, {reg}, {indice_reg}")
                output.append(f"add {reg}, {reg}, $fp")
                output.append(f"lw {reg}, 0({reg})")
            else:
                # Si es un parámetro, usar offset positivo desde $fp
                if offset >= 0:
                    output.append(
                        f"lw {reg}, {offset}($fp)  # cargar var/param {nodo.nombre}")
                else:
                    output.append(
                        f"lw {reg}, {offset}($fp)  # cargar var local {nodo.nombre}")
        elif is_global:
            if nodo.tam:
                base_reg = nueva_temp()
                output.append(f"la {base_reg}, {nodo.nombre}")
                indice_reg = genExp(nodo.tam)
                output.append(f"mul {indice_reg}, {indice_reg}, 4")
                output.append(f"add {base_reg}, {base_reg}, {indice_reg}")
                output.append(f"lw {reg}, 0({base_reg})")
            else:
                output.append(f"la {reg}, {nodo.nombre}")
                output.append(f"lw {reg}, 0({reg})")
        else:
            output.append(
                f"# ERROR: variable {nodo.nombre} no tiene offset asignado")
        return reg

    elif nodo.nodoTipo == 'expresion' and nodo.op == '=':
        var_name = nodo.hijoIzq.nombre
        valor = genExp(nodo.hijoDer)
        offset = offsets.get(var_name)
        # Detectar si es variable global
        global_scope = semantica.tabla_stack[0]
        is_global = any(entry['nombre'] ==
                        var_name for entry in global_scope['entradas'])
        if offset is not None and not is_global:
            if nodo.hijoIzq.tam:
                indice_reg = genExp(nodo.hijoIzq.tam)
                temp_reg = nueva_temp()
                output.append(f"li {temp_reg}, {offset}")
                output.append(f"mul {indice_reg}, {indice_reg}, 4")
                output.append(f"add {temp_reg}, {temp_reg}, {indice_reg}")
                output.append(f"add {temp_reg}, {temp_reg}, $fp")
                output.append(
                    f"sw {valor}, 0({temp_reg})  # {var_name}[...] = ...")
            else:
                output.append(
                    f"sw {valor}, {offset}($fp)  # asignar var/param {var_name}")
        elif is_global:
            if nodo.hijoIzq.tam:
                base_reg = nueva_temp()
                output.append(f"la {base_reg}, {var_name}")
                indice_reg = genExp(nodo.hijoIzq.tam)
                output.append(f"mul {indice_reg}, {indice_reg}, 4")
                output.append(f"add {base_reg}, {base_reg}, {indice_reg}")
                output.append(
                    f"sw {valor}, 0({base_reg})  # {var_name}[...] = ...")
            else:
                addr_reg = nueva_temp()
                output.append(f"la {addr_reg}, {var_name}")
                output.append(
                    f"sw {valor}, 0({addr_reg})  # asignar global {var_name}")
        else:
            output.append(
                f"# ERROR: variable {var_name} no tiene offset asignado")
        return valor

    elif nodo.nodoTipo == 'expresion':
        izq = genExp(nodo.hijoIzq)
        der = genExp(nodo.hijoDer)
        res = nueva_temp()

        if nodo.op == '+':
            output.append(f"add {res}, {izq}, {der}")
        elif nodo.op == '-':
            output.append(f"sub {res}, {izq}, {der}")
        elif nodo.op == '*':
            output.append(f"mul {res}, {izq}, {der}")
        elif nodo.op == '/':
            output.append(f"div {res}, {izq}, {der}")
        elif nodo.op == '<':
            output.append(f"slt {res}, {izq}, {der}")
        elif nodo.op == '>':
            output.append(f"slt {res}, {der}, {izq}")
        elif nodo.op == '<=':
            output.append(f"slt {res}, {der}, {izq}")
            output.append(f"xori {res}, {res}, 1")
        elif nodo.op == '>=':
            output.append(f"slt {res}, {izq}, {der}")
            output.append(f"xori {res}, {res}, 1")
        elif nodo.op == '==':
            output.append(f"seq {res}, {izq}, {der}")
        elif nodo.op == '!=':
            output.append(f"sne {res}, {izq}, {der}")
        else:
            output.append(f"# ERROR: operador desconocido {nodo.op}")
        return res

    elif nodo.nodoTipo == 'call':
        # Soporte para output(x)
        if nodo.nombre == "output" and len(nodo.hijos) == 1:
            val = genExp(nodo.hijos[0])
            output.append(f"move $a0, {val}")
            output.append("li $v0, 1")  # syscall: print int
            output.append("syscall")
            # Agregar salto de línea después de imprimir
            output.append("li $v0, 11")  # syscall: print char
            output.append("li $a0, 10")  # newline character
            output.append("syscall")
            global uso_output
            uso_output = True
            return "$zero"
        # Soporte para input()
        if nodo.nombre == "input" and len(nodo.hijos) == 0:
            reg = nueva_temp()
            output.append("li $v0, 5")  # syscall: read int
            output.append("syscall")
            output.append(f"move {reg}, $v0")
            return reg
        # Llamadas normales - pasar argumentos en orden correcto
        for arg in nodo.hijos:  # Mantener orden original de argumentos
            val = genExp(arg)
            output.append("sub $sp, $sp, 4")
            output.append(f"sw {val}, 0($sp)")
        output.append(f"jal {nodo.nombre}")
        output.append(f"add $sp, $sp, {len(nodo.hijos) * 4}")
        # Detectar si la función es void
        global_scope = semantica.tabla_stack[0]
        fun_symbol = next(
            (entry for entry in global_scope['entradas'] if entry['nombre'] == nodo.nombre), None)
        if fun_symbol and fun_symbol.get('tipo') == 'VOID':
            return None  # No retorna valor
        res = nueva_temp()
        output.append(f"move {res}, $v0")
        return res

    return "$zero"  # Por defecto, retornar $zero si no se cumple ninguna condición
