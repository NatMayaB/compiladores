from globalTypes import *
from parser import *
import semantica
from cgen import *
from lexer import *

f = open("texto.txt", "r")
programa = f.read()
progLong = len(programa)
programa = programa + " $"
posicion = 0

globales(programa, posicion, progLong)

AST = parser(False)
semantica.tabla(AST)  # Imprime las tablas de símbolos
codeGen(AST, "salida.s")
