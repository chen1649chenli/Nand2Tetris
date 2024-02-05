import os,sys

class VMTranslator():
    def __init__(self, filename):
        self.input_file = filename
        self.vm_filename= self.get_filename_without_suffix(filename)
        self.arith_dict = {"not":"!","neg":"-","add":"+","sub":"-","and":"&","or":"|","eq":"JNE","lt":"JGE","gt":"JLE"}
        self.asm_codes=[]
        self.codes=self._read_and_process_file(filename)
        self.symbol_index=0
        self.mapping = {"local":"LCL", "argument":"ARG", "this":"THIS", "that":"THAT", "temp":"5", "pointer":"3"}

    def get_output_file_name(self):
        path = os.path.dirname(self.input_file)
        file_name = self.get_filename_without_suffix(self.input_file)
        if len(path) == 0:
            path = "."
        return "/".join([path, file_name]) + ".asm"


    def get_filename_without_suffix(self, path):
        # Get the filename from the path
        filename = os.path.basename(path)

        # Split the filename into name and extension
        name, extension = os.path.splitext(filename)
        
        return name
    
    def _read_and_process_file(self, filename):
        """Reads the file, and processes its lines."""
        text = []
        with open(filename, "r") as file:
            for line in file.readlines():
                line = self._process_line(line)
                if line:
                    text.append(line)
        return text

    def _process_line(self, line):
        """Strips leading/trailing white space, removes comments, and spaces within the line."""
        line = line.strip()
        if line and "//" in line:
            line = line.split("//", 1)[0].strip()
        return line 

    def C_arith(self, command):
        """
		generate assembly codes for arithmetic commands
		@para command (str): the arithmetic command to be translated
		"""
        asm_code = []
        if command in ["add", "sub", "and", "or"]:
            spec = "M=M"+self.arith_dict[command] + "D"
            asm_code = ["@SP", "AM=M-1", "D=M", "A=A-1", spec]
        elif command in ["not", "neg"]:
            spec="M="+self.arith_dict[command]+"M"
            asm_code=["@SP", "A=M-1", spec]
        elif command in ["eq", "gt", "lt"]:
            symbol = command + "_" + str(self.symbol_index)
            symbol1 = "@" + symbol
            symbol2 = "(" + symbol + ")"
            spec = "D;" + self.arith_dict[command]
            asm_code = ["@SP", "AM=M-1", "D=M", "A=A-1", "D=M-D", "M=0", symbol1, spec, "@SP", "A=M-1", "M=-1", symbol2]
            self.symbol_index+=1  
        return asm_code             

    def C_push(self, command):
        """
        Generate assembly codes for push commands
        @para command (list of str): the push command to be translated
        """
        asm_code = []
        if command[0] == "constant":
            asm_code= ["@" + command[1], "D=A"]
        elif command[0] in ["local","argument","this","that"]:
            asm_code = ["@" + command[1], "D=A", "@"+self.mapping[command[0]], "A=M+D", "D=M"] 
        elif command[0] == "static":
            symbol = "@" + self.vm_filename + "." + command[1]
            asm_code = [symbol, "D=M"]
        elif command[0] in ["temp", "pointer"]:
            asm_code = ["@" + command[1], "D=A", "@"+self.mapping[command[0]], "A=A+D", "D=M"]  
                
        return asm_code + ["@SP", "A=M", "M=D", "@SP", "M=M+1"] 

    def C_pop(self, command):
        """
        Generate assembly codes for pop commands
        @para command( list of str): the pop command to be translated
        """
		#compute the address 
        if command[0] in ["local","argument","this","that"]:
            asm_code=["@"+command[1],"D=A","@"+self.mapping[command[0]],"D=M+D","@R15","M=D"]
        elif command[0] in ["temp","pointer"]:
            asm_code=["@"+command[1],"D=A","@"+self.mapping[command[0]],"D=A+D","@R15","M=D"]
        elif command[0] == "static":
            symbol = "@" + self.vm_filename + "." + command[1]
            asm_code = [symbol, "D=A","@R15","M=D"]

        # put the value *SP into M[address], then SP--
        return asm_code + ["@SP","AM=M-1","D=M","@R15","A=M","M=D"]

    def parse(self):
        """
        For each line in the self.codes, generate its corresponding assembly codes
        """
        for code in self.codes:
            parts = code.split()
            print("VM code:" + code)
            if len(parts) == 1: # arithmetic command
                self.asm_codes += self.C_arith(parts[0])
                print("Hack Assembly code:")
                self.print_list(self.C_arith(parts[0]))
            elif parts[0] == "push": # push command   
                self.asm_codes += self.C_push(parts[1:])
                print("Hack Assembly code:")
                self.print_list(self.C_push(parts[1:]))
            elif parts[0] == "pop": # pop command
                self.asm_codes += self.C_pop(parts[1:])   
                print("Hack Assembly code:")
                self.print_list(self.C_pop(parts[1:])) 


    def save_file(self):
        """
        save self.asm_codes into xxx.asm file
        """
        output_path=self.get_output_file_name()
        with open(output_path, "w") as file:
            for line in self.asm_codes:
                file.write(line + "\n")

    def print_list(self, strings):
        for line in strings:
            print(line)
        print("\n")    


def main():
    file_path = sys.argv[1]
    vmtranslator=VMTranslator(file_path)
    vmtranslator.parse()
    vmtranslator.save_file()

if __name__ == "__main__":
    main()  