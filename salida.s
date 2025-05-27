.data
x: .word 0
y: .word 0
.text
.globl main
j main
nop
suma:
sub $sp, $sp, 8
sw $ra, 4($sp)
sw $fp, 0($sp)
move $fp, $sp

lw $t0, 8($fp)  # cargar var/param a
lw $t1, 12($fp)  # cargar var/param b
add $t2, $t0, $t1
move $v0, $t2  # return valor
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
li $t3, 5
la $t4, x
sw $t3, 0($t4)  # asignar global x
la $t5, x
lw $t5, 0($t5)
sub $sp, $sp, 4
sw $t5, 0($sp)
li $t6, 3
sub $sp, $sp, 4
sw $t6, 0($sp)
jal suma
add $sp, $sp, 8
move $t7, $v0
la $t8, y
sw $t7, 0($t8)  # asignar global y
la $t9, y
lw $t9, 0($t9)
move $a0, $t9
li $v0, 1
syscall
li $v0, 11
li $a0, 10
syscall
move $v0, $zero  # return valor
li $v0, 10
syscall
