def somar(a, b):
    return a + b

def dividir(a, b):
    if b == 0:
        raise ValueError("Não é possível dividir por zero")
    return a / b

def verificar_numero(numero):
    if numero > 0:
        return "positivo"
    elif numero < 0:
        return "negativo"
    else:
        return "zero"

def eh_par(numero):
    if numero % 2 == 0:
        return True
    return False