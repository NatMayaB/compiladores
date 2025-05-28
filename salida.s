.data
.text
.globl main
j main
nop
max:
sub $sp, $sp, 8
sw $ra, 4($sp)
sw $fp, 0($sp)
move $fp, $sp
lw $t0, 8($fp)  # cargar var/param a
lw $t1, 12($fp)  # cargar var/param b
slt $t2, $t1, $t0
beq $t2, $zero, L0  # if false -> else
lw $t3, 8($fp)  # cargar var/param a
move $v0, $t3  # return valor
move $sp, $fp
lw $fp, 0($sp)
lw $ra, 4($sp)
add $sp, $sp, 8
jr $ra
j L1
L0:
lw $t4, 12($fp)  # cargar var/param b
move $v0, $t4  # return valor
move $sp, $fp
lw $fp, 0($sp)
lw $ra, 4($sp)
add $sp, $sp, 8
jr $ra
L1:
li $v0, 1  # return por defecto
move $sp, $fp
lw $fp, 0($sp)
lw $ra, 4($sp)
add $sp, $sp, 8
jr $ra
suma:
sub $sp, $sp, 8
sw $ra, 4($sp)
sw $fp, 0($sp)
move $fp, $sp
lw $t5, 8($fp)  # cargar var/param a
lw $t6, 12($fp)  # cargar var/param b
add $t7, $t5, $t6
move $v0, $t7  # return valor
move $sp, $fp
lw $fp, 0($sp)
lw $ra, 4($sp)
add $sp, $sp, 8
jr $ra
main:
sub $sp, $sp, 8
sw $ra, 4($sp)
sw $fp, 0($sp)
move $fp, $sp
sub $sp, $sp, 36
li $t8, 3
li $t9, 0
li $t0, -20
mul $t9, $t9, 4
add $t0, $t0, $t9
add $t0, $t0, $fp
sw $t8, 0($t0)  # A[...] = ...
li $t1, 6
li $t2, 1
li $t3, -20
mul $t2, $t2, 4
add $t3, $t3, $t2
add $t3, $t3, $fp
sw $t1, 0($t3)  # A[...] = ...
li $t4, 1
li $t5, 2
li $t6, -20
mul $t5, $t5, 4
add $t6, $t6, $t5
add $t6, $t6, $fp
sw $t4, 0($t6)  # A[...] = ...
li $t7, 8
li $t8, 3
li $t9, -20
mul $t8, $t8, 4
add $t9, $t9, $t8
add $t9, $t9, $fp
sw $t7, 0($t9)  # A[...] = ...
li $t0, 2
li $t1, 4
li $t2, -20
mul $t1, $t1, 4
add $t2, $t2, $t1
add $t2, $t2, $fp
sw $t0, 0($t2)  # A[...] = ...
li $t3, 0
sw $t3, -24($fp)  # asignar var/param i
li $t4, 0
sw $t4, -32($fp)  # asignar var/param total
li $t6, 0
li $t5, -20
mul $t6, $t6, 4
add $t5, $t5, $t6
add $t5, $t5, $fp
lw $t5, 0($t5)
sw $t5, -36($fp)  # asignar var/param maximo
L2:
lw $t7, -24($fp)  # cargar var local i
li $t8, 5
slt $t9, $t7, $t8
beq $t9, $zero, L3  # while false -> exit
lw $t1, -24($fp)  # cargar var local i
li $t0, -20
mul $t1, $t1, 4
add $t0, $t0, $t1
add $t0, $t0, $fp
lw $t0, 0($t0)
li $t2, 5
slt $t3, $t2, $t0
beq $t3, $zero, L4  # if false -> else
lw $t4, -32($fp)  # cargar var local total
sub $sp, $sp, 4
sw $t4, 0($sp)
lw $t6, -24($fp)  # cargar var local i
li $t5, -20
mul $t6, $t6, 4
add $t5, $t5, $t6
add $t5, $t5, $fp
lw $t5, 0($t5)
sub $sp, $sp, 4
sw $t5, 0($sp)
jal suma
add $sp, $sp, 8
move $t7, $v0
sw $t7, -32($fp)  # asignar var/param total
lw $t9, -24($fp)  # cargar var local i
li $t8, -20
mul $t9, $t9, 4
add $t8, $t8, $t9
add $t8, $t8, $fp
lw $t8, 0($t8)
li $t0, 10
slt $t1, $t8, $t0
beq $t1, $zero, L6  # if false -> else
lw $t2, -24($fp)  # cargar var local i
sub $sp, $sp, 4
sw $t2, 0($sp)
lw $t4, -24($fp)  # cargar var local i
li $t3, -20
mul $t4, $t4, 4
add $t3, $t3, $t4
add $t3, $t3, $fp
lw $t3, 0($t3)
sub $sp, $sp, 4
sw $t3, 0($sp)
jal suma
add $sp, $sp, 8
move $t5, $v0
sw $t5, -28($fp)  # asignar var/param z
lw $t6, -32($fp)  # cargar var local total
sub $sp, $sp, 4
sw $t6, 0($sp)
lw $t7, -28($fp)  # cargar var local z
sub $sp, $sp, 4
sw $t7, 0($sp)
jal suma
add $sp, $sp, 8
move $t8, $v0
sw $t8, -32($fp)  # asignar var/param total
j L7
L6:
L7:
j L5
L4:
lw $t9, -32($fp)  # cargar var local total
li $t0, 1
add $t1, $t9, $t0
sw $t1, -32($fp)  # asignar var/param total
L5:
lw $t2, -36($fp)  # cargar var local maximo
sub $sp, $sp, 4
sw $t2, 0($sp)
lw $t4, -24($fp)  # cargar var local i
li $t3, -20
mul $t4, $t4, 4
add $t3, $t3, $t4
add $t3, $t3, $fp
lw $t3, 0($t3)
sub $sp, $sp, 4
sw $t3, 0($sp)
jal max
add $sp, $sp, 8
move $t5, $v0
sw $t5, -36($fp)  # asignar var/param maximo
lw $t6, -24($fp)  # cargar var local i
li $t7, 1
add $t8, $t6, $t7
sw $t8, -24($fp)  # asignar var/param i
j L2
L3:
lw $t9, -36($fp)  # cargar var local maximo
lw $t0, -32($fp)  # cargar var local total
add $t1, $t9, $t0
move $v0, $t1  # return valor
move $a0, $v0
li $v0, 1
syscall
li $v0, 10
syscall
add $sp, $sp, 36
