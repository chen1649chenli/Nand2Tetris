from Code import Code
from SymbolTable import SymbolTable
from Parser import Parser
import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error")
        sys.exit(1)
    filename = sys.argv[-1]
    
    #初始化
    code = Code()
    symboltable = SymbolTable()
    parser = Parser(filename)

    #第一轮循环
    while parser.has_more_commands():
        parser.advance_to_next_command()
        if parser.get_command_type() == "L":
            sym = parser.current_command[1:-1]
            addr = parser.current_line
            symboltable.addEntry(sym, addr)

    #重置
    parser.current_index = 0
    parser.current_line = 0

    Res = []            

    #第二轮循环
    while parser.has_more_commands():
        parser.advance_to_next_command()
        res = ""
        if parser.get_command_type() == "A":
            #数字地址
            num = parser.symbol(symboltable)
            #二进制，前缀为0b
            b = bin(num)[2:]
            #补0
            res = (16 - len(b)) * "0" + b
            Res.append(res)
        elif parser.get_command_type() == "C":
            dest = parser.dest(code)
            comp = parser.comp(code)
            jump = parser.jump(code)
            
            res = "111" + comp + dest + jump
            Res.append(res)
    
    name = filename.split(".")[0]
    #存储结果
    with open(name+".hack", "w+") as f:
        for i in Res:
            f.writelines(i + "\n")