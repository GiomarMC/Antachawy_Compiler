class LexemasAntachawy:
    QHAPAQ = "qhapaq"                           # main
    YUPAY = "yupay"                             # int
    CHUNKAYUQ = "chunkayuq"                     # float
    SANANPA = "sananpa"                         # char
    QAYTU = "qaytu"                             # string
    BOOL = "bool"                               # bool
    ARI = "ari"                                 # if
    MANA_CHAYQA_ARI = "mana_chayqa_ari"         # else if
    MANA_CHAYQA = "mana_chayqa"                 # else
    RIKUCHIY = "rikuchiy"                       # print
    IMAPAQ = "imapaq"                           # for
    CHAYKAMA = "chaykama"                       # while
    YANQA = "yanqa"                             # false
    CHIQAQ = "chiqaq"                           # true
    CUTICHIY = "cutichiy"                       # return
    SALTO_LINEA = "\n"                          # salto de linea
    LLAVE_IZQ = "{"                             # {
    LLAVE_DER = "}"                             # }
    PAREN_IZQ = "("                             # (
    PAREN_DER = ")"                             # )
    COMA = ","                                  # ,
    PUNTOYCOMA = ";"                            # ;
    MAS = "+"                                   # +
    MENOS = "-"                                 # -
    MULTIPLICA = "*"                            # *
    DIVIDE = "/"                                # /
    DIVISIONEXACTA = "//"                       # //
    ASIGNA = "="                                # =
    MAYOR = ">"                                 # >
    MENOR = "<"                                 # <
    IGUAL = "=="                                # ==
    DIFERENTE = "!="                            # !=
    MAYOR_IGUAL = ">="                          # >=
    MENOR_IGUAL = "<="                          # <=
    Y_LOGICO = "&&"                             # &&
    O_LOGICO = "||"                             # ||
    NUMEROENTERO = "entero"                     # numero
    NUMEROFLOTANTE = "flotante"                 # flotante
    CARACTER = "caracter"                       # caracter
    CADENA = "cadena"                           # cadena
    ID = "id"                                   # identificador


class EtiquetasAntachawy:
    TIPO_YUPAY = "TIPOENTERO"
    TIPO_CHUNKAYUQ = "TIPOFLOAT"
    TIPO_SANANPA = "TIPOCHAR"
    TIPO_QAYTU = "TIPOSTRING"
    TIPO_BOOL = "TIPOBOOL"
    ASIGNACION = "ASIGNACION"
    CONDICION_ARI = "CONDICION_IF"
    CONDICION_MANA_CHAYQA_ARI = "CONDICION_ELSEIF"
    CONDICION_MANA_CHAYQA = "CONDICION_ELSE"
    MAS = "MAS"
    MENOS = "MENOS"
    MULTIPLICA = "MULTIPLICA"
    DIVIDE = "DIVIDE"
    IMPRESION = "IMPRESION"
    BUCLE_FOR = "BUCLE_FOR"
    BUCLE_WHILE = "BUCLE_WHILE"
    BLOQUE = "BLOQUE"
    SALTO_LINEA = "SALTO_LINEA"
    LLAVE_IZQ = "LLAVE_IZQ"
    LLAVE_DER = "LLAVE_DER"
    PAREN_IZQ = "PAREN_IZQ"
    PAREN_DER = "PAREN_DER"
    COMA = "COMA"
    PUNTOYCOMA = "PUNTOYCOMA"
    PROGRAMA = "PROGRAMA"
    NUMEROENTERO = "ENTERO"
    NUMEROFLOTANTE = "FLOTANTE"
    CARACTER = "CARACTER"
    CADENA = "CADENA"
    TRUE = "TRUE"
    FALSE = "FALSE"
    ID = "ID"
    MAYOR = "MAYOR"
    MENOR = "MENOR"
    IGUAL = "IGUAL"
    DIFERENTE = "DIFERENTE"
    MAYOR_IGUAL = "MAYOR_IGUAL"
    MENOR_IGUAL = "MENOR_IGUAL"
    Y_LOGICO = "OPERADOR_Y"
    O_LOGICO = "OPERADOR_O"
    FIN_ARCHIVO = "FIN_ARCHIVO"


L = LexemasAntachawy
E = EtiquetasAntachawy

lexema_a_etiqueta = {
    L.QHAPAQ: E.PROGRAMA,
    L.YUPAY: E.TIPO_YUPAY,
    L.CHUNKAYUQ: E.TIPO_CHUNKAYUQ,
    L.SANANPA: E.TIPO_SANANPA,
    L.QAYTU: E.TIPO_QAYTU,
    L.BOOL: E.TIPO_BOOL,
    L.ASIGNA: E.ASIGNACION,
    L.ARI: E.CONDICION_ARI,
    L.MANA_CHAYQA_ARI: E.CONDICION_MANA_CHAYQA_ARI,
    L.MANA_CHAYQA: E.CONDICION_MANA_CHAYQA,
    L.RIKUCHIY: E.IMPRESION,
    L.IMAPAQ: E.BUCLE_FOR,
    L.CHAYKAMA: E.BUCLE_WHILE,
    L.SALTO_LINEA: E.SALTO_LINEA,
    L.LLAVE_IZQ: E.LLAVE_IZQ,
    L.LLAVE_DER: E.LLAVE_DER,
    L.PAREN_IZQ: E.PAREN_IZQ,
    L.PAREN_DER: E.PAREN_DER,
    L.COMA: E.COMA,
    L.PUNTOYCOMA: E.PUNTOYCOMA,
    L.YANQA: E.FALSE,
    L.CHIQAQ: E.TRUE,
    L.MAS: E.MAS,
    L.MENOS: E.MENOS,
    L.MULTIPLICA: E.MULTIPLICA,
    L.DIVIDE: E.DIVIDE,
    L.MAYOR: E.MAYOR,
    L.MENOR: E.MENOR,
    L.IGUAL: E.IGUAL,
    L.DIFERENTE: E.DIFERENTE,
    L.MAYOR_IGUAL: E.MAYOR_IGUAL,
    L.MENOR_IGUAL: E.MENOR_IGUAL,
    L.Y_LOGICO: E.Y_LOGICO,
    L.O_LOGICO: E.O_LOGICO,
    L.NUMEROENTERO: E.NUMEROENTERO,
    L.NUMEROFLOTANTE: E.NUMEROFLOTANTE,
    L.CARACTER: E.CARACTER,
    L.CADENA: E.CADENA,
    L.ID: E.ID,
}

simbolos_compuestos = {
    "==": E.IGUAL,
    "!=": E.DIFERENTE,
    "<=": E.MENOR_IGUAL,
    ">=": E.MAYOR_IGUAL,
    "&&": E.Y_LOGICO,
    "||": E.O_LOGICO,
}

# Etiqueta -> texto legible para los mensajes de error.
etiqueta_a_lexema = {etiqueta: lexema
                     for lexema, etiqueta in lexema_a_etiqueta.items()}
etiqueta_a_lexema[E.SALTO_LINEA] = "salto de línea"
etiqueta_a_lexema[E.FIN_ARCHIVO] = "final del archivo"
