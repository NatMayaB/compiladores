from globalTypes import *
from parser import *
import semantica
from cgenFer import *
from lexer import *

f = open("texto.txt", "r")
programa = f.read()
progLong = len(programa)
programa = programa + " $"
posicion = 0

globales(programa, posicion, progLong)

AST = parser(False)
semantica.verificar_errores(AST)
codeGen(AST, "salida.s")
