class Parser():
    """A Parser class to parse and process a given assembly file."""

    def __init__(self, filename):
        """Initializes the Parser with the given file, and processes its lines."""
        self.text = self._read_and_process_file(filename)

        # Variables for tracking the current position and state
        self.current_address = 16
        self.current_index = 0
        self.current_line = 0
        self.total_lines = len(self.text)
        self.current_command = ""
        self.current_comp = ""
        self.current_dest = ""
        self.current_jump = ""

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
        if line and '//' in line:
            line = line.split('//', 1)[0].strip()
        return line.replace(' ', '') if line else None    
        
    def has_more_commands(self):
        """Returns True if there are more commands left to process."""
        return self.current_index < self.total_lines
    
    def advance_to_next_command(self):
        """Advances to the next command, if there are any left."""
        if self.has_more_commands():
            self.current_command = self.text[self.current_index]
            self.current_index += 1
            if not self._is_label_command():
                self.current_line += 1

    def _is_label_command(self):
        """Returns True if the current command is a label command."""
        return self.current_command[0] == "("

    def get_command_type(self):
        """Returns the type of the current command."""
        if self.current_command[0] == "@":
            return "A"
        elif self._is_label_command():
            return "L"
        else:
            self._separate_c_command()
            return "C"

    def _separate_c_command(self):
        """Separates the parts of a C command."""
        dest_separator = self.current_command.find("=")
        jump_separator = self.current_command.find(";")
        if dest_separator != -1 and jump_separator != -1:
            self.current_comp = self.current_command[dest_separator+1: jump_separator]
            self.current_dest = self.current_command[:dest_separator]
            self.current_jump = self.current_command[jump_separator+1:]
        elif dest_separator == -1:
            self.current_comp = self.current_command[:jump_separator]
            self.current_dest = ""
            self.current_jump = self.current_command[jump_separator+1:]
        elif jump_separator == -1:
            self.current_comp = self.current_command[dest_separator+1:]
            self.current_dest = self.current_command[:dest_separator]
            self.current_jump = ""

    def symbol(self, symboltable):
        #变量
        if self.get_command_type() == "A":
            sym = self.current_command[1:]
            #判断是否为数字
            if sym.isdigit():
                return int(sym)
            else:
                #判断是否在符号表中
                if not(symboltable.contains(sym)):
                    symboltable.addEntry(sym, self.current_address)
                    self.current_address += 1
                return symboltable.getAddress(sym)
        #符号
        elif self.get_command_type() == "L":
            sym = self.current_command[1: -1]
            if not(symboltable.contains(sym)):
                symboltable.addEntry(sym, self.current_line)
                
            return symboltable.getAddress(sym)
        
    def dest(self, code):
        if self.get_command_type() == "C":
            return code.dest(self.current_dest)
        
    def comp(self, code):
        if self.get_command_type() == "C":
            return code.comp(self.current_comp)

    def jump(self, code):
        if self.get_command_type() == "C":
            return code.jump(self.current_jump) 