class Code:
    def __init__(self):
        self.dest_dict = {
            "M": "001",
            "D": "010",
            "MD": "011",
            "A": "100",
            "AM": "101",
            "AD": "110",
            "AMD": "111",
            None: "000"
        }

        self.comp_dict = {
            "0": ("0", "101010"),
            "1": ("0", "111111"),
            "-1": ("0", "111010"),
            "D": ("0", "001100"),
            "A": ("0", "110000"),
            "M": ("1", "110000"),
            "!D": ("0", "001101"),
            "!A": ("0", "110001"),
            "!M": ("1", "110001"),
            "-D": ("0", "001111"),
            "-A": ("0", "110011"),
            "-M": ("1", "110011"),
            "D+1": ("0", "011111"),
            "A+1": ("0", "110111"),
            "M+1": ("1", "110111"),
            "D-1": ("0", "001110"),
            "A-1": ("0", "110010"),
            "M-1": ("1", "110010"),
            "D+A": ("0", "000010"),
            "D+M": ("1", "000010"),
            "D-A": ("0", "010011"),
            "D-M": ("1", "010011"),
            "A-D": ("0", "000111"),
            "M-D": ("1", "000111"),
            "D&A": ("0", "000000"),
            "D&M": ("1", "000000"),
            "D|A": ("0", "010101"),
            "D|M": ("1", "010101"),
            None: ("0", "000000")
        }

        self.jump_dict = {
            "JGT": "001",
            "JEQ": "010",
            "JGE": "011",
            "JLT": "100",
            "JNE": "101",
            "JLE": "110",
            "JMP": "111",
            None: "000"
        }

    def dest(self, mnemonic):
        return self.dest_dict.get(mnemonic, "000")

    def comp(self, mnemonic):
        a, c = self.comp_dict.get(mnemonic, ("0", "000000"))
        return a + c

    def jump(self, mnemonic):
        return self.jump_dict.get(mnemonic, "000")