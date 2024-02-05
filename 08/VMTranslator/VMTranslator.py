import os,sys

class VMTranslator():
    def __init__(self, file_path):
        """
        @attr self.vm_files (list of str):the Xxx.vm files needed to be translated
        @attr self.asm_filename (str): output filename
        @attr self.output_path (str): path for the output_file
        @attr self.symbol_index(int): use it to make sure that each symbol is unique
        @attr self.ret_index(int): use it to make sure that each ret label is unique
        """
        self.vm_files = []
        self.asm_codes = []
        self.symbol_index = 0
        self.ret_index = 0

        if os.path.isdir(file_path):
            for file in os.listdir(file_path):
                if (file.endswith(".vm")):
                    self.vm_files.append(os.path.join(file_path, file))
            assert len(self.vm_files) > 0, "please choose a dir with vm files in it."
            self.asm_filename = os.path.basename(file_path) + ".asm"
            self.output_path = file_path
            self.multi = True
        else:
            assert file_path.endswith(".vm"), "please choose an input file named Xxx.vm"
            full_path = os.path.abspath(file_path)
            self.vm_files = [full_path]
            self.output_path = os.path.dirname(full_path)
            self.asm_filename = self.get_filename_without_suffix(full_path) + ".asm"
            self.multi = False

    def get_filename_without_suffix(self, path):
            # Get the filename from the path
        filename = os.path.basename(path)

        # Split the filename into name and extension
        name, extension = os.path.splitext(filename)
        
        return name

    def save_file(self):
        """
        save self.asm_codes into xxx.asm file
        """
        output_file = os.path.join(self.output_path, self.asm_filename)
        with open(output_file, "w") as file:
            for line in self.asm_codes:
                file.write(line + "\n")

    def parse(self):
        """
        Translate the vm files in self.vm_files into Hack assembly codes and store them in self.asm_codes
        """

        if self.multi: # add bootstrap codes
            self.asm_codes = self.bootstrap()

        for file in self.vm_files:
            single_file_parser = SingleFileVMTranslator(file, self.symbol_index, self.ret_index)
            single_file_parser.parse()
            self.asm_codes += single_file_parser.asm_codes
            self.symbol_index = single_file_parser.symbol_index
            self.ret_index = single_file_parser.ret_index

    def bootstrap(self):
        asm_code = ["@256", "D=A", "@SP", "M=D"] # set SP = 256
        asm_code += ["@1","D=A","@LCL","M=D"]
        asm_code += ["@2","D=A","@ARG","M=D"]
        asm_code += ["@3","D=A","@THIS","M=D"]
        asm_code += ["@4","D=A","@THAT","M=D"]

        push_command = ["@SP", "A=M", "M=D", "@SP", "M=M+1"]
        asm_code += ["@bootstrap", "D=A"] + push_command # push return address

        for segment in ["LCL", "ARG", "THIS", "THAT"]: # push LCL, ARG, THIS, THAT
            segment_label = "@" + segment
            asm_code += [segment_label, "D=M"] + push_command

        # Repositions ARG: ARG = SP - nArgs - 5
        asm_code += ["@5", "D=A", "@SP", "D=M-D", "@ARG", "M=D"]

        # Reposition LCL: LCL = SP
        asm_code += ["@SP", "D=M", "@LCL", "M=D"]  

        # Transfer control to the sys function
        asm_code += ["@Sys.init", "0;JMP"]

        # Declares a label for the return address
        asm_code += ["(bootstrap)" ]

        return asm_code                                

class SingleFileVMTranslator():
    """ 
	translate a .vm file into Hack assembly codes
	"""
    def __init__(self, filename, symbol_index, ret_index):
        """
        Open the file and filter the blanks and comments
        @attr self.vm_filename (str): input vm file
        @attr self.codes (list of str): a list contains clean vm code with no blank or comments
        @attr self.asm_codes(list of str): a list contains assembly codes generated from self.codes
        @attr self.symbol_index(int): use it to make sure that each symbol is unique
        @attr self.ret_index(int): use it to make sure that each ret label is unique
        """
        self.vm_filename = filename
        self.arith_dict = {"not":"!","neg":"-","add":"+","sub":"-","and":"&","or":"|","eq":"JNE","lt":"JGE","gt":"JLE"}
        self.asm_codes=[]
        self.codes=self._read_and_process_file(filename)
        self.symbol_index = symbol_index
        self.ret_index = ret_index
        self.mapping = {"local":"LCL", "argument":"ARG", "this":"THIS", "that":"THAT", "temp":"5", "pointer":"3"}
        self.cur_funcname = ""
         
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
        vm_filename = os.path.splitext(os.path.basename(self.vm_filename))[0]
        asm_code = []
        if command[0] == "constant":
            asm_code= ["@" + command[1], "D=A"]
        elif command[0] in ["local","argument","this","that"]:
            asm_code = ["@" + command[1], "D=A", "@"+self.mapping[command[0]], "A=M+D", "D=M"] 
        elif command[0] == "static":
            symbol = "@" + vm_filename + "." + command[1]
            asm_code = [symbol, "D=M"]
        elif command[0] in ["temp", "pointer"]:
            asm_code = ["@" + command[1], "D=A", "@"+self.mapping[command[0]], "A=A+D", "D=M"]  
                
        return asm_code + ["@SP", "A=M", "M=D", "@SP", "M=M+1"] 

    def C_pop(self, command):
        """
        Generate assembly codes for pop commands
        @para command(list of str): the pop command to be translated
        """
        vm_filename = os.path.splitext(os.path.basename(self.vm_filename))[0]

		#compute the address 
        if command[0] in ["local","argument","this","that"]:
            asm_code=["@"+command[1],"D=A","@"+self.mapping[command[0]],"D=M+D","@R15","M=D"]
        elif command[0] in ["temp","pointer"]:
            asm_code=["@"+command[1],"D=A","@"+self.mapping[command[0]],"D=A+D","@R15","M=D"]
        elif command[0] == "static":
            symbol = "@" + vm_filename + "." + command[1]
            asm_code = [symbol, "D=A","@R15","M=D"]

        # put the value *SP into M[address], then SP--
        return asm_code + ["@SP","AM=M-1","D=M","@R15","A=M","M=D"]

    def C_call(self, command):
        """
        Generate assembly codes for call commands
        @para command(list of str): [call func_name argument_variable_count - e.g., "call Main.fibonacci 1"]
        """
        label = command[0] + "$ret" + str(self.ret_index)
        self.ret_index += 1
        push_command = ["@SP", "A=M", "M=D", "@SP", "M=M+1"]
        asm_code = ["@" + label, "D=A"] + push_command # push return address

        for segment in ["LCL", "ARG", "THIS", "THAT"]: # push LCL, ARG, THIS, THAT
            segment_label = "@" + segment
            asm_code += [segment_label, "D=M"] + push_command

        # Repositions ARG
        asm_code += ["@" + str(int(command[1]) + 5), "D=A", "@SP", "D=M-D", "@ARG", "M=D"] # # ARG = SP - nArgs - 5

        # Reposition LCL: LCL = SP
        asm_code += ["@SP", "D=M", "@LCL", "M=D"]  

        # Transfer control to the called function
        asm_code += ["@" + command[0], "0;JMP"]

        # Declares a label for the return address
        asm_code += ["(" + label + ")" ]

        return asm_code

    def C_function(self, command):
        """
        Generate assembly codes for function declaration
        @para command(list of str): [function func_name local_variables_count - e.g., "function Main.fibonacci 0"]
        """
        self.cur_funcname = command[0]
        asm_code = ["(" + command[0] + ")"]
        for _ in range(int(command[1])):
            asm_code += ["@SP", "A=M", "M=0", "@SP", "M=M+1"]
        return asm_code

    def C_return(self):
        """ 
        Generate assembly codes for return command
        """
        asm_code = ["@LCL", "D=M", "@R13", "M=D"] # put LCL into R13.
        asm_code += ["@5", "D=A", "@R13", "A=M-D", "D=M", "@R14", "M=D"] # put return address into R14
        asm_code += ["@SP", "AM=M-1", "D=M", "@ARG", "A=M", "M=D"] # *ARG = pop()
        asm_code += ["@ARG", "D=M+1", "@SP", "M=D"] # SP = ARG + 1
        asm_code += ["@R13", "A=M-1","D=M", "@THAT", "M=D" ] # THAT = *(FRAME - 1)
        asm_code += ["@2", "D=A", "@R13", "A=M-D","D=M", "@THIS", "M=D"] # THIS = *(FRAME - 2)
        asm_code += ["@3", "D=A", "@R13", "A=M-D","D=M", "@ARG", "M=D"] # ARG = *(FRAME - 3)
        asm_code += ["@4", "D=A", "@R13", "A=M-D","D=M", "@LCL", "M=D"] # LCL = *(FRAME - 4)
        asm_code += ["@R14", "A=M", "0;JMP"] # go to return address
        return asm_code

    def parse(self):
        """
        For each line in the self.codes, generate its corresponding assembly codes
        """
        for code in self.codes:
            parts = code.split()
            if len(parts) == 1: # arithmetic command or return command
                self.asm_codes += ["\n//" + code]
                if parts[0] == "return":
                    self.asm_codes += self.C_return() # parse return command
                else:
                    self.asm_codes += self.C_arith(parts[0]) # parse arithmetic command
            elif parts[0] == "push": # push command  
                self.asm_codes += ["\n//" + code] 
                self.asm_codes += self.C_push(parts[1:])
            elif parts[0] == "pop": # pop command
                self.asm_codes += ["\n//" + code]
                self.asm_codes += self.C_pop(parts[1:])   
            elif parts[0] == 'label': # branching command - label
                self.asm_codes += ["\n//" + code]
                label_ = self.cur_funcname + "$" + parts[1]
                self.asm_codes += ["(" + label_ + ")"]
            elif parts[0] == 'goto': # branching command - goto
                self.asm_codes += ["\n//" + code]
                label_ = self.cur_funcname + "$" + parts[1]
                self.asm_codes += ["@" + label_, "0;JMP"]  
            elif parts[0] == 'if-goto': # branching command - "if-goto"
                self.asm_codes+=["\n//" + code]
                label_ = self.cur_funcname + "$" + parts[1]
                self.asm_codes += ["@SP", "AM=M-1", "D=M", "@" + label_, "D;JNE"] 
            elif parts[0] == 'call': # call function
                self.asm_codes += ["\n//" + code]
                self.asm_codes += self.C_call(parts[1:]) 
            elif parts[0] == 'function': # function declaration
                self.asm_codes += ["\n//" + code]
                self.asm_codes += self.C_function(parts[1:])     

    def print_list(self, strings):
        for line in strings:
            print(line)
        print("\n")    


def main():
    assert len(sys.argv) >=2, "please enter a filename or directory."
    file_path = sys.argv[1]
    vmtranslator=VMTranslator(file_path)
    vmtranslator.parse()
    vmtranslator.save_file()

if __name__ == "__main__":
    main()  