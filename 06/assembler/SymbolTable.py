class SymbolTable:
    def __init__(self):
        self.table = {f"R{i}": i for i in range(16)}
        self.table.update({
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4,
            "SCREEN": 16384,
            "KBD": 24576
        })

    def contains(self, symbol):
        return symbol in self.table

    def addEntry(self, symbol, address):
        if not self.contains(symbol):
            self.table[symbol] = address
        else:
            print("The symbol already exists!")
            
    def getAddress(self, symbol):
        return self.table.get(symbol)