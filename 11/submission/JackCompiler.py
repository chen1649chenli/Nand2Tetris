import sys
import os
import re
import xml.etree.ElementTree as ET
import xml.dom.minidom
from enum import Enum

class VariableKind(Enum):
    STATIC = 'static'
    FIELD = 'field'
    ARG = 'argument'
    VAR = 'local'

class SymbolTable:
    """
    Creates a new symbol table to store identifiers with their properties.
    """
    def __init__(self):
        self.table = dict()
        self.var_type_count = dict() 

    def define(self, name: str, var_type: str, kind: VariableKind):
        """
        Define a new identifier of the given name, type and kind, and assigns it a running index.
        """
        index = self.var_count(kind)
        self.table[name] = (name, var_type, kind, index)
        self.var_type_count[kind] = index + 1
    
    def start_subroutine(self):
        """ Start a new subroutine scope by clearing the table. """
        self.table.clear()
        self.var_type_count.clear()
    
    def var_count(self, kind: VariableKind):
        """ 
        Return the number of variables of the given kind (STATIC, FIELD, ARG, VAR) already defined in the current scope.
        """
        return self.var_type_count.get(kind, 0)

    def kind_of(self, name: str):
        """
        Return the kind (STATIC, FIELD, ARG, VAR) of the input variable name
        tip: each symbol not found in the symbol table can be assumed to be either a subroutine name or a class name
        """
        variable = self.table.get(name, None)
        return variable[2] if variable else None


    def type_of(self, name: str):
        """
        Return the type (int, string, class_name) of the input variable name
        """
        variable = self.table.get(name, None)
        return variable[1] if variable else None

    def index_of(self, name: str):
        """
        Return the index of the input variable name
        """
        variable = self.table.get(name, None)
        return variable[3] if variable else None   

class JackTokenizer:
    """
    transform the input Xxx.jack file into tokens
    """
    def __init__(self, file_name):
        """
        Initializes the tokenizer with sets of keywords and symbols.

        Args:
            keywords (set): A set of strings representing the keywords in the language.
            symbols (set): A set of characters representing the symbols in the language.
        """
        self.keywords = {'class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean',
         'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return'}
        self.symbols = {'{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~'}
        self.xml_symbol_replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            '&': '&amp;'
        }
        assert file_name[-4:] == 'jack', 'the input file must be Xxx.jack'
        self.file_name = file_name
        
    def remove_comments(self):
        cleaned_code = []
        multi_comments = False

        with open(self.file_name) as file:
            for line in file:
                line = line.strip()

                if multi_comments:
                    if '*/' in line:
                        line = line[line.find('*/') + 2:]
                        multi_comments = False
                    else:
                        continue

                if line.startswith('//'):
                    continue

                if '//' in line:
                    line = line[:line.find('//')]

                if '/*' in line:
                    if '*/' in line:
                        start = line.find('/*')
                        end = line.find('*/') + 2
                        line = line[:start] + line[end:]
                    else:
                        line = line[:line.find('/*')]
                        multi_comments = True

                # for subroutine that return void, push constant 0, then return; the caller then throw away the returned 0;
                if line == "return;":
                    line = "return 0;" 

                if line:
                    cleaned_code.append(line)

        return cleaned_code

    def tokenize(self, code):
        """
        Tokenizes the given code into XML formatted tokens.

        Args:
            code (str): A string representing the code to be tokenized.

        Returns:
            str: A string containing the XML representation of the tokens.
        """

        # Define patterns for different token types
        keyword_pattern = '|'.join(self.keywords)
        symbol_pattern = '|'.join(re.escape(s) for s in self.symbols)
        int_pattern = r'\d+'
        string_pattern = r'"[^"\n]*"'
        identifier_pattern = r'[A-Za-z_]\w*'    
        # Combined pattern
        token_pattern = f'({keyword_pattern})|({symbol_pattern})|({int_pattern})|({string_pattern})|({identifier_pattern})'

        tokens = []

        # Function to process each token match
        def process_match(match):
            """
            Processes each regex match and converts it to the appropriate XML tag.

            Args:
                match (MatchObject): A MatchObject representing the current regex match.

            Returns:
                str: A string representing the XML tag for the matched token.
            """
            token = match.group(0)

            if token in self.keywords:
                return f'<keyword> {token} </keyword>'
            elif token in self.symbols:
                # Replace symbol with XML entity if needed
                token = self.xml_symbol_replacements.get(token, token)
                return f'<symbol> {token} </symbol>'
            elif token.isdigit():
                return f'<integerConstant> {token} </integerConstant>'
            elif token.startswith('"') and token.endswith('"'):
                # Strip quotes for string constants
                return f'<stringConstant> {token[1:-1]} </stringConstant>'
            else:
                return f'<identifier> {token} </identifier>'

        # Tokenize the code
        for match in re.finditer(token_pattern, code):
            token_xml = process_match(match)
            tokens.append(token_xml)

        # Return XML-wrapped tokens
        return '<tokens>\n' + '\n'.join(tokens) + '\n</tokens>'

    def save_token_file(self, tokenized_xml):
        output_file_name = self.file_name[:-5] + 'TTT.xml'
        with open(output_file_name, 'w') as file:
            file.write(tokenized_xml)       

class CompilationEngine:
    def __init__(self, input_tokens, output_file):
        """
        Initializes the compilation engine with the given input tokens.

        Args:
            input_tokens (str): A string of XML-formatted tokens.
        """
        self.tokens = ET.fromstring(input_tokens)
        self.current_token = 0
        self.output = []
        self.op = {'+', '-', '*', '/', '&', '|', '<', '>', '='}
        self.xml_symbol_replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            '&': '&amp;'
        }
        self.unary_op = {'-', '~'}
        self.key_constant = {'true', 'false', 'null', 'this'}
        self.statement_type = {"let", "do", "return", "if", "while"}
        self.output_file = output_file
        self.class_symbol_table = SymbolTable()
        self.subroutine_symbol_table = SymbolTable()
        self.method_names = set()
        self._class_name = ""

    def get_class_name(self):
        return self._class_name

    def get_method_names(self):
        return self.method_names

    def advance(self):
        """Move to the next token."""
        if self.current_token < len(self.tokens) - 1:
            self.current_token += 1

    def eat(self, expected_type):
        """
        Consume a token of a specific type.

        Args:
            expected_type (str): The expected type of the current token.
        """
        if self.get_current_token_type() == expected_type:
            current_value = self.get_current_token_value()
            self.advance()
            return current_value
        else:
            raise ValueError(f'Expected token type {expected_type}, found {self.get_current_token_type()} for value {self.get_current_token_value()}')

    def get_current_token(self):
        """Returns the current token element."""
        return self.tokens[self.current_token]

    def get_current_token_type(self):
        """Returns the type of the current token."""
        return self.get_current_token().tag

    def get_current_token_value(self):
        """Returns the type of the current token."""
        return self.get_current_token().text.strip()   

    def compile_var_dec(self):
        """
        Compiles a var declaration.
        """
        self.output.append("<varDec>")

        # 'var'
        self.eat("keyword") # 'var' is a keyword
        self.output.append("<keyword> var </keyword>")

        # 'type' which can be either a primitive type or a className (identifier)
        type_token_type = self.get_current_token_type()
        type_token = self.get_current_token_value()
        if type_token_type == "keyword":
            self.output.append(f"<keyword> {type_token} </keyword>")
            self.advance()
        elif self.get_current_token_type() == "identifier":
            self.output.append(f"<identifier category='class' purpose='used'> {type_token} </identifier>")
            self.advance()            
        else:
            raise ValueError("Expected type keyword or identifier, but actual value is {type_token_type}")
        
        # varName(s)
        while True:
            _value = self.eat("identifier")
            self.subroutine_symbol_table.define(_value, type_token, VariableKind.VAR)
            _index = self.subroutine_symbol_table.index_of(_value)
            self.output.append(f"<identifier category='local' purpose='defined' index='{_index}' type='{type_token}'> {_value} </identifier>")
            if self.get_current_token_value() == ";":
                break
            self.eat("symbol") # Comma
            self.output.append(f"<symbol> , </symbol>")
        
        # ';'
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>")

        self.output.append("</varDec>")

    def compile_class_var_dec(self):
        """
        Compiles a static or field var declaration in a class
        """
        self.output.append("<classVarDec>")

        # 'static|field' 
        _category = self.eat("keyword") 
        category = VariableKind.STATIC if _category == "static" else VariableKind.FIELD
        self.output.append(f"<keyword> {_category} </keyword>")

        # 'type' which can be either a primitive type or a className (identifier)
        if self.get_current_token_type() in ["keyword", "identifier"]:
            type_token = self.get_current_token_value()
            type_token_type = self.get_current_token_type()
            if type_token_type == "identifier":
                self.output.append(f"<identifier category='{_category}' purpose='used'> {type_token} </identifier>")
            else:
                self.output.append(f"<{type_token_type}> {type_token} </{type_token_type}>")
            self.advance()
        else:
            raise ValueError("Expected type keyword or identifier, but actual value is {type_token_type}") 

        # varName(s)
        while True:
            _value = self.eat("identifier")
            self.class_symbol_table.define(_value, type_token, category)
            _index = self.class_symbol_table.index_of(_value)
            # self.output.append(f"<identifier> {_value} </identifier>")
            self.output.append(f"<identifier category='{_category}' purpose='defined' index='{_index}' type='{type_token}'> {_value} </identifier>")
            if self.get_current_token_value() == ";":
                break
            self.eat("symbol") # Comma
            self.output.append(f"<symbol> , </symbol>")
        
        # ';'
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>") 

        self.output.append("</classVarDec>")

    def compile_parameter_list(self, class_name, subroutine_type):
        """
        Compiles a (possibly empty) parameter list. 
        Does not handle the enclosing "()".
        """
        self.output.append("<parameterList>")

        # Add 'this' as the first parameter of class method
        if subroutine_type == 'method':
            self.subroutine_symbol_table.define("this", class_name, VariableKind.ARG)
            this_index = str(self.subroutine_symbol_table.index_of("this"))
            self.output.append(f"<identifier category='class' purpose='used'> {class_name} </identifier>")
            self.output.append(f"<identifier category='argument' purpose='defined' index='{this_index}' type='{class_name}'> this </identifier>")
        

        # Check if there is at least one parameter
        if self.get_current_token_type() in ["keyword", "identifier"]:
            # parameter(s)
            while True:
                # type
                type_token_type = self.get_current_token_type()
                type_token_value = self.get_current_token_value()
                if self.get_current_token_type() == "keyword":
                    self.output.append(f"<keyword> {type_token_value} </keyword>")
                    self.advance()
                elif type_token_type == "identifier":
                    self.output.append(f"<identifier category='class' purpose='used'> {type_token_value} </identifier>")
                    self.advance()                   
                else:
                    raise ValueError("Expected type keyword or identifier for parameter")

                # varName
                _value = self.eat("identifier")
                self.subroutine_symbol_table.define(_value, type_token_value, VariableKind.ARG)
                _index = str(self.subroutine_symbol_table.index_of(_value))
                self.output.append(f"<identifier category='argument' purpose='defined' index='{_index}' type='{type_token_value}'> {_value} </identifier>")

                # check for more parameters
                if self.get_current_token_value() != ',':
                    break

                # consume the comma, and continue
                self.eat("symbol")
                self.output.append(f"<symbol> , </symbol>")

        self.output.append("</parameterList>")

    def compile_expression(self):
        """
        Compile expression
        """
        self.output.append("<expression>")
        self.compile_term()

        while self.get_current_token_value() in self.op:
            _value = self.eat("symbol").strip()
            _value = self.xml_symbol_replacements.get(_value, _value)

            self.output.append(f"<symbol> {_value} </symbol>")
            self.compile_term()
        self.output.append("</expression>")

    def compile_term(self):
        """
        Compile terms
        """
        self.output.append("<term>")

        _value = self.get_current_token_value()
        _value_next = self.tokens[self.current_token + 1].text.strip()
        _tag = self.get_current_token_type()

        # integerConstant
        if _value.isdigit() and _tag == "integerConstant":
            self.output.append(f"<integerConstant> {_value} </integerConstant>")
            self.advance()
        #stringConstant    
        elif _tag == "stringConstant":
            self.output.append(f"<stringConstant> {_value} </stringConstant>")
            self.advance()
        # keywordConstant
        elif _tag == "keyword" and _value in self.key_constant:
            self.output.append(f"<keyword> {_value} </keyword>")
            self.advance()
        # '(' expression ')
        elif _tag == "symbol" and _value == "(": # '(' expression ')
            self.eat("symbol") # (
            self.output.append(f"<symbol> ( </symbol>")
            self.compile_expression() # expression
            self.eat("symbol") # (
            self.output.append(f"<symbol> ) </symbol>")
        # unaryOp term 
        elif _value in self.unary_op:
            self.eat("symbol")
            self.output.append(f"<symbol> {_value} </symbol>")
            self.compile_term()
        # subroutineCall    
        elif _tag == "identifier" and _value_next in {"(", "."}:
            self.compile_subroutine_call()
        # varName '[' expression ']'    
        elif _value_next == "[":
            # varName
            self.eat("identifier")
            # self.output.append(f"<identifier> {_value} </identifier>")
            _category = self.subroutine_symbol_table.kind_of(_value).value if self.subroutine_symbol_table.kind_of(_value) else self.class_symbol_table.kind_of(_value).value
            _index = self.subroutine_symbol_table.index_of(_value) if self.subroutine_symbol_table.index_of(_value) is not None else self.class_symbol_table.index_of(_value)
            _type = self.subroutine_symbol_table.type_of(_value) if self.subroutine_symbol_table.type_of(_value) is not None else self.class_symbol_table.type_of(_value)
            self.output.append(f"<identifier category='{_category}' index='{_index}' purpose='used' type='{_type}'> {_value} </identifier>")         
            # [
            self.eat("symbol")
            self.output.append(f"<symbol> [ </symbol>")
            # expression
            self.compile_expression()
            # ]
            self.eat("symbol")
            self.output.append(f"<symbol> ] </symbol>")
        # varName    
        else:
            self.eat("identifier")
            # self.output.append(f"<identifier> {_value} </identifier>")
            _category = self.subroutine_symbol_table.kind_of(_value).value if self.subroutine_symbol_table.kind_of(_value) else self.class_symbol_table.kind_of(_value).value
            _index = self.subroutine_symbol_table.index_of(_value) if self.subroutine_symbol_table.index_of(_value) is not None else self.class_symbol_table.index_of(_value)
            _type = self.subroutine_symbol_table.type_of(_value) if self.subroutine_symbol_table.type_of(_value) is not None else self.class_symbol_table.type_of(_value)
            self.output.append(f"<identifier category='{_category}' index='{_index}' purpose='used' type='{_type}'> {_value} </identifier>") 
        self.output.append("</term>")

    def compile_expression_list(self):
        """
        Compiles a (possibly empty) comma-separated list of expressions.
        """ 
        self.output.append("<expressionList>")

        # check if there is at least one expression
        if self.get_current_token_value() != ")": # Assuming ')' signifies the end of an expression list
            while True:
                # Compile the expression 
                self.compile_expression()

                # If the next token is not a comma, break the loop
                if self.get_current_token_value() != ",":
                    break
                
                # ,
                self.eat("symbol")
                self.output.append("<symbol> , </symbol>")

        self.output.append("</expressionList>")

    def compile_subroutine_call(self):
        """
        Compiles a subroutine call.
        """

        # Subroutine call can start with a subroutineName or className/varName
        _value = self.eat("identifier")
        # self.output.append(f"<identifier> {_value} </identifier>")
        if self.subroutine_symbol_table.index_of(_value) is not None or self.class_symbol_table.index_of(_value) is not None:
            _category = self.subroutine_symbol_table.kind_of(_value).value if self.subroutine_symbol_table.kind_of(_value) else self.class_symbol_table.kind_of(_value).value
            _index = self.subroutine_symbol_table.index_of(_value) if self.subroutine_symbol_table.index_of(_value) is not None else self.class_symbol_table.index_of(_value)
            _type = self.subroutine_symbol_table.type_of(_value) if self.subroutine_symbol_table.type_of(_value) is not None else self.class_symbol_table.type_of(_value)
            self.output.append(f"<identifier category='{_category}' index='{_index}' purpose='used' type='{_type}'> {_value} </identifier>")
        elif _value[0].isupper():
            self.output.append(f"<identifier category='class' purpose='used'> {_value} </identifier>")
        else:
            self.output.append(f"<identifier category='subroutine' purpose='used'> {_value} </identifier>")

        # Check for '.' indicating a method call on an object or class
        if self.get_current_token_value() == '.':
            self.eat("symbol")
            self.output.append(f"<symbol> . </symbol>") 
            _value = self.eat("identifier")
            # self.output.append(f"<identifier> {_value} </identifier>")
            self.output.append(f"<identifier category='subroutine' purpose='used'> {_value} </identifier>")                            
        # (    
        self.eat("symbol")
        self.output.append("<symbol> ( </symbol>")

        # expressionList
        self.compile_expression_list()

        # )
        self.eat("symbol")
        self.output.append("<symbol> ) </symbol>")

    def compile_statements(self):
        """
        Compile statements
        """
        self.output.append("<statements>")
        while self.get_current_token_value() in self.statement_type:
            self.compile_statement()
        self.output.append("</statements>")

    def compile_statement(self):
        """
        Compile a single statement
        """ 
        if self.get_current_token_value() == "let":
            self.compile_let_statement()
        elif self.get_current_token_value() == "do":
            self.compile_do_statement()
        elif self.get_current_token_value() == "if":
            self.compile_if_statement()
        elif self.get_current_token_value() == "while":
            self.compile_while_statement()
        elif self.get_current_token_value() == "return": 
            self.compile_return_statement()         

    def compile_let_statement(self):
        """
        Compile let statement
        """
        self.output.append("<letStatement>")

        # 'let'
        self.eat("keyword")
        self.output.append(f"<keyword> let </keyword>")

        # varName
        _value = self.eat("identifier")
        #self.output.append(f"<identifier> {_value} </identifier>")
        _category = self.subroutine_symbol_table.kind_of(_value).value if self.subroutine_symbol_table.kind_of(_value) else self.class_symbol_table.kind_of(_value).value
        _index = self.subroutine_symbol_table.index_of(_value) if self.subroutine_symbol_table.index_of(_value) is not None else self.class_symbol_table.index_of(_value)
        _type = self.subroutine_symbol_table.type_of(_value) if self.subroutine_symbol_table.type_of(_value) is not None else self.class_symbol_table.type_of(_value)
        self.output.append(f"<identifier category='{_category}' purpose='used' index='{_index}' type='{_type}'> {_value} </identifier>")

        # ('[' expression ']')?
        if self.get_current_token_value() == '[':
            self.output.append(f"<symbol> [ </symbol>")
            self.advance()
            self.compile_expression()
            self.output.append(f"<symbol> ] </symbol>")
            self.advance()

        # '='
        self.eat("symbol")
        self.output.append(f"<symbol> = </symbol>")

        # expression
        self.compile_expression()

        # ';'
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>")
        self.output.append("</letStatement>")
    
    def compile_do_statement(self):
        """
        Compile do statement
        """
        self.output.append("<doStatement>")

        # do
        self.eat("keyword")
        self.output.append(f"<keyword> do </keyword>")

        self.output.append("<term>")

        # subroutineCall
        self.compile_subroutine_call()

        self.output.append("</term>")

        # ;
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>")       

        self.output.append("</doStatement>")      

    def compile_return_statement(self):
        """
        Compiles a return statement.
        """
        self.output.append("<returnStatement>")

        # return
        self.eat("keyword")
        self.output.append(f"<keyword> return </keyword>")

        # expression?
        if self.get_current_token_value() != ";":
            self.compile_expression()
        
        # ;
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>")

        self.output.append("</returnStatement>")

    def compile_if_statement(self):
        """
        Compile if statement
        """
        self.output.append("<ifStatement>")
        # if
        self.eat("keyword")
        self.output.append(f"<keyword> if </keyword>")

        # (
        self.eat("symbol")
        self.output.append(f"<symbol> ( </symbol>") 

        # expression
        self.compile_expression()

        # )
        self.eat("symbol")
        self.output.append(f"<symbol> ) </symbol>")  

        # {
        self.eat("symbol") 
        self.output.append("<symbol> { </symbol>")

        # statements
        self.compile_statements()

        # }
        self.eat("symbol")
        self.output.append("<symbol> } </symbol>") 

        # optional else statement
        if self.get_current_token_value() == 'else':

            # else
            self.eat("keyword")
            self.output.append(f"<keyword> else </keyword>")

            # {
            self.eat("symbol")
            self.output.append("<symbol> { </symbol>") 

            # statements
            self.compile_statements()

            # }
            self.eat("symbol")
            self.output.append("<symbol> } </symbol>")            

        self.output.append("</ifStatement>")

    def compile_while_statement(self):
        """
        Compile while statement
        """
        self.output.append("<whileStatement>")

        # while
        self.eat("keyword")
        self.output.append(f"<keyword> while </keyword>")

        # (
        self.eat("symbol")
        self.output.append(f"<symbol> ( </symbol>") 

        # expression
        self.compile_expression()

        # )
        self.eat("symbol")
        self.output.append(f"<symbol> ) </symbol>")  

        # {
        self.eat("symbol")
        self.output.append("<symbol> { </symbol>")   

        # statements
        self.compile_statements()

        # }
        self.eat("symbol")
        self.output.append("<symbol> } </symbol>")  

        self.output.append("</whileStatement>")

    def compile_subroutine_body(self):
        """
        Compile a subroutine body
        """

        self.output.append("<subroutineBody>")

        # {
        self.eat("symbol")
        self.output.append("<symbol> { </symbol>")

        # varDec*
        while self.get_current_token_value() == "var":
            self.compile_var_dec()

        # statements
        self.compile_statements()

        # }
        self.eat("symbol")
        self.output.append("<symbol> } </symbol>")

        self.output.append("</subroutineBody>")

    def compile_subroutine_dec(self, class_name):
        """
        Compile subroutine 
        """
        self.subroutine_symbol_table.start_subroutine()
        self.output.append("<subroutineDec>")

        # ('constructor' | 'function' | 'method')
        subroutine_type = self.eat("keyword")
        self.output.append(f"<keyword> {subroutine_type} </keyword>")

        # ('void' | type)
        _value = self.get_current_token_value()
        if _value in ["void", "int", "char", "boolean"]:
            self.output.append(f"<keyword> {_value} </keyword>")
        else:
            # self.output.append(f"<identifier> {_value} </identifier>")
            self.output.append(f"<identifier category='class' purpose='used'> {_value} </identifier>")
        self.advance()
        
        # subroutineName
        _value = self.eat("identifier")
        if subroutine_type == "method":
            self.method_names.add(_value)
        # self.output.append(f"<identifier> {_value} </identifier>")
        self.output.append(f"<identifier category='subroutine' purpose='defined'> {_value} </identifier>")

        # '('
        self.eat("symbol")
        self.output.append(f"<symbol> ( </symbol>")

        # parameterList
        self.compile_parameter_list(class_name, subroutine_type)

        # ')'
        self.eat("symbol")
        self.output.append(f"<symbol> ) </symbol>")

        # subroutineBody
        self.compile_subroutine_body()

        self.output.append("</subroutineDec>")

    def compile_class(self):
        """
        Compile class
        """
        self.output.append("<class>")

        # class
        self.eat("keyword")
        self.output.append(f"<keyword> class </keyword>")

        # className
        class_name = self.eat("identifier")
        #self.output.append(f"<identifier> {class_name} </identifier>")
        self.output.append(f"<identifier category='class' purpose='defined' > {class_name} </identifier>")
        self._class_name = class_name

        # {
        self.eat("symbol")
        self.output.append("<symbol> { </symbol>")

        # classVarDec*
        while self.get_current_token_value() in ["field", "static"] and self.get_current_token_type() == "keyword":
            self.compile_class_var_dec()

        # subroutineDec*
        while self.get_current_token_value() in ["constructor", "function", "method"] and self.get_current_token_type() == "keyword":
            self.compile_subroutine_dec(class_name) 

        # }
        self.eat("symbol")
        self.output.append("<symbol> } </symbol>")

        self.output.append("</class>")

    def format_xml_string(self):
        input_string = "\n".join(self.output)

        root = ET.fromstring(input_string)
        rough_string = ET.tostring(root, 'utf-8')

        # Use minidom to format the XML with indentation
        reparsed = xml.dom.minidom.parseString(rough_string)
        formatted_xml = '\n'.join(reparsed.toprettyxml(indent="  ").split('\n')[1:])

        # remove empty lines
        lines = formatted_xml.splitlines()
        non_empty_lines = [line for line in lines if line.strip() != ""]
        return "\n".join(non_empty_lines)

    def save_xml_file(self, tokenized_xml):
        output_file_name = self.output_file + '.xml'
        with open(output_file_name, 'w') as file:
            file.write(tokenized_xml)

    def get_xml_representation(self):
        input_string = "\n".join(self.output)
        return ET.fromstring(input_string)    

class JackCompiler:
    def __init__(self, path):
        self.files = self.list_files(path)

    def list_files(self, path):
        """
        Verify if the input path is a single file or a directory. 
        If it's a directory, return a list of all files in it.

        Args:
        path (str): The path to the file or directory.

        Returns:
        list: A list of file paths if it's a directory, otherwise, an empty list.
        """
        if os.path.isfile(path):
         # The path is a file, return the file in a list
            return [path]
        elif os.path.isdir(path):
            entries = os.listdir(path)
            files = [os.path.join(path, entry) for entry in entries if os.path.isfile(os.path.join(path, entry)) and os.path.join(path, entry).endswith(".jack")]
            return files
        else:
            return []

    def analyze_one_file(self, file):
        tokenizer = JackTokenizer(file)
        codes = tokenizer.remove_comments()
        code_snippet = "\n".join(codes)
        tokenized_xml = tokenizer.tokenize(code_snippet)
        engine = CompilationEngine(tokenized_xml, tokenizer.file_name[:-5])
        engine.compile_class()
        method_names = engine.get_method_names()
        print("=== Method Names:    " + str(method_names))
        class_name = engine.get_class_name()
        print("=== Class Names:    " + class_name)

        result = engine.format_xml_string()
        engine.save_xml_file(result)

        xml = engine.get_xml_representation()
        vm_outputfile_name = tokenizer.file_name[:-5] + ".vm"
        vm_code_generator = VMWriter(vm_outputfile_name, xml, method_names, class_name)
        vm_code_generator.compile()
        print(vm_code_generator.vm_codes)
        vm_code_generator.close()

    def analyze(self):
        for file in self.files:
            self.analyze_one_file(file)

class VMWriter:
    """
    Creates a new output .vm file and prepares it for writing
    """
    def __init__(self, output_file, xml_object, method_names, class_name):
        self.output_file = output_file
        self.xml = xml_object
        self.vm_codes = []
        self.op_map = {
            '+': 'add',
            '-': 'sub',
            '*': 'call Math.multiply 2',
            # '/': 'call Math.divide 2',
            '&': 'and',
            '|': 'or', 
            '<': 'lt', 
            '>': 'gt', 
            '=': 'eq'
        }
        self.unary_op_map = {
            '-': 'neg',
            '~': 'not',            
        }

        self.keyword_replacement = {
            'true': '1',
            'false': '0',
            'null': '', # TODO: update 
            'this': ''  # TODO: update
        }
        self.if_count = 0
        self.while_count = 0
        self.method_names = method_names
        self.class_name = class_name
        self.class_var_count = 0

    def write_push(self, segment: str, index: int):
        code = "push " + segment + " " + str(index)
        self.vm_codes.append(code)

    def write_pop(self, segment: str, index: int):
        code = "pop " + segment + " " + str(index)
        self.vm_codes.append(code)

    def write_arithmetic(self, command:str):
        self.vm_codes.append(command)

    def write_label(self, label: str):
        code = "label " + label
        self.vm_codes.append(code)
    
    def write_goto(self, label: str):
        code = "goto " + label
        self.vm_codes.append(code)
    
    def write_if(self, label: str):
        code = "if-goto " + label
        self.vm_codes.append(code)

    def write_call(self, name: str, n_args: int):
        code = "call " + name + " " + str(n_args)
        self.vm_codes.append(code)

    def write_function(self, name: str, n_locals: int):
        code = "function " + name + " " + str(n_locals)
        self.vm_codes.append(code)

    def write_return(self):
        self.vm_codes.append("return")

    def close(self):
        with open(self.output_file, 'w') as file:
            code_text = "\n".join(self.vm_codes)
            file.write(code_text) 

    def count_subroutine_local_variables(self, subroutine_dec):
        """
        Count the number of local variables in a subroutine body.
        Args:
            subroutine_dec (Element): An XML element representing the subroutine declaration.
        Returns:
            int: The number of local variables.
        """
        local_var_count = 0
        for child in subroutine_dec:
            if child.tag == "subroutineBody":
                for grand_child in child:
                    if grand_child.tag == "varDec":
                        """
                        <varDec>
                            <keyword> var </keyword>
                            <keyword> int </keyword>
                            <identifier> i </identifier>
                            <symbol> , </symbol>
                            <identifier> j </identifier>
                            <symbol> ; </symbol>
                        </varDec>
                        <varDec>
                            <keyword> var </keyword>
                            <identifier> String </identifier>
                            <identifier> s </identifier>
                            <symbol> ; </symbol>
                        </varDec>
                        """
                        for local in grand_child:
                            if local.tag == "identifier" and local.attrib["category"] == "local":
                                local_var_count += 1
        return local_var_count
    
    def count_subroutine_parameters(self, subroutine_dec):
        """
        Count the number of parameters in a subroutine.
        Args:
            subroutine_dec (Element): An XML element representing the subroutine declaration.
        Returns:
            int: The number of parameters.
        """        
        parameter_count = 0
        for child in subroutine_dec:
            if child.tag == "parameterList":
                for parameter in child:
                    if parameter.tag == "identifier" and parameter.attrib['category'] == "argument":
                        parameter_count += 1
        return parameter_count

    def get_subroutine_name(self, class_name, subroutine_dec):
        for child in subroutine_dec:
            if (child.tag == "identifier") and (child.attrib["category"] == "subroutine"):
                return class_name + "." + child.text.strip()
        return None
    
    def get_class_name(self):
        for id in self.xml:
            if (id.tag == 'identifier') and (id.attrib["category"] == "class") and (id.attrib["purpose"] == "defined"):
                return id.text.strip()
        return None
    
    def get_expression_list_var_count(self, expression_list):
        return len(expression_list.findall("./expression"))

    def compile_subroutine_dec(self, class_name, subroutine_dec):
        # part.1 subroutine name
        subroutine_name = self.get_subroutine_name(class_name, subroutine_dec)
        n_locals = self.count_subroutine_local_variables(subroutine_dec)
        # n_parameters = self.count_subroutine_parameters(subroutine_dec)
        self.write_function(subroutine_name, n_locals)

        # part.2 handle different subroutines
        if subroutine_dec.find("./keyword").text.strip() == "constructor":
            self.write_push("constant", self.class_var_count)
            self.write_call("Memory.alloc", 1)
            self.write_pop("pointer", 0)
        elif subroutine_dec.find("./keyword").text.strip() == "method":
            self.write_push("argument", 0)
            self.write_pop("pointer", 0) # THIS = argument 0
        

        # part.3 subroutine body
        self.compile_subroutine_body(subroutine_dec.find("./subroutineBody"))


    def compile_parameter_list(self, parameter_list):
        return

    def compile_subroutine_body(self, subroutine_body):
        # part 1 varName


        # part 2 statements
        self.compile_statements(subroutine_body.find("./statements"))
    
    def compile_statements(self, statements):
        for statement in statements:
            self.compile_statement(statement)
            
    def compile_statement(self, statement):
        if statement.tag == "doStatement":
            self.compile_do_statement(statement)
        elif statement.tag == "letStatement":
            self.compile_let_statement(statement)
        elif statement.tag == "returnStatement":
            self.compile_return_statement(statement)
        elif statement.tag == "ifStatement":
            self.compile_if_statement(statement)
        elif statement.tag == "whileStatement":
            self.compile_while_statement(statement)
            
    def compile_return_statement(self, statement):
        expression = statement.find("./expression")
        if expression is None:
            self.write_return()
        else:
            self.compile_expression(expression)
            self.write_return()
    
    def compile_do_statement(self, statement):
        term = statement.find("./term")
        self.compile_term(term)
        self.write_pop("temp", 0)
    
    def compile_if_statement(self, statement):
        expression = statement.find("./expression")
        self.compile_expression(expression)
        self.write_arithmetic("not")
        false_label = "IF_LABEL_FALSE_" + str(self.if_count)
        self.if_count += 1
        next_label =  "IF_LABEL_NEXT_" + str(self.if_count)
        self.if_count += 1
        self.write_if(false_label)
        statements = statement.findall("./statements")
        self.compile_statements(statements[0])
        self.write_goto(next_label)
        self.write_label(false_label)

        # case 1: if ... else ...
        if len(statement.findall("./keyword")) == 2: # [if, else]
            self.compile_statements(statements[1])

        self.write_label(next_label)
    
    def compile_while_statement(self, statement):
        while_true = "WHILE_LABEL_TRUE_" + str(self.while_count)
        self.while_count += 1
        while_false = "WHILE_LABEL_FALSE_" + str(self.while_count)
        self.while_count += 1
        self.write_label(while_true)
        expression = statement.find("./expression")
        self.compile_expression(expression)
        self.write_arithmetic("not")
        self.write_if(while_false)
        statements = statement.find("./statements")
        self.compile_statements(statements)
        self.write_goto(while_true)
        self.write_label(while_false)

    def compile_let_statement(self, statement):
        # case 1: expression = varName;
        if len(statement.findall("./identifier")) == 1:
            expression = statement.find("./expression")
            self.compile_expression(expression)
            var = statement.find("./identifier")
            _index = var.attrib["index"]
            _category = var.attrib["category"]
            if _category == "field":
                self.write_pop("this", int(_index))
            else:
                self.write_pop(_category, int(_index))
        # case 2:  expression = varName[expression];
        else:
            print("_________AAAA______")
            return
            # TODO: add code here

    def compile_subroutine_call(self, subroutine_name, expression_list, is_object_method_call):

        parameter_count = self.get_expression_list_var_count(expression_list) + is_object_method_call
        self.compile_expression_list(expression_list)
        self.write_call(subroutine_name, parameter_count)
        
    def compile_expression_list(self, expression_list):
        expressions = expression_list.findall('./expression')
        for expression in expressions:
            self.compile_expression(expression)

    def compile_expression(self, expression):
        terms = expression.findall("./term")
        self.compile_term(terms[0])
        operators = expression.findall("./symbol")
        operators_count = 0 if operators is None else len(operators)
        for i in range(operators_count):
            self.compile_term(terms[i+1])
            self.write_arithmetic(self.op_map[operators[i].text.strip()])

    def compile_term(self, term):  
        # handle integerConstant
        if list(term)[0].tag == "integerConstant":
            element = term.find("./integerConstant")
            self.write_push("constant", int(element.text.strip()))
        elif term.find("./stringConstant"):
            return  # TODO: handle string
        elif term.find("./keyword") is not None and len(term.findall("./keyword")) == 1: 
            element = term.find("./keyword")
            keyword_text = element.text.strip()
            if keyword_text == 'true':
                # 'true': '-1'
                self.write_push("constant", 1)
                self.write_arithmetic('neg')
            elif keyword_text == 'false' or keyword_text == 'null': 
                # 'false': '0'; 'null': '0'
                self.write_push("constant", 0)
            elif keyword_text == 'this':
                self.write_push("pointer", 0)
            else:
                return

        # handle varName    
        elif term.find("./identifier") is not None and len(term.findall("./identifier")) == 1 and term.find("./identifier").attrib["category"] != "subroutine":
            element = term.find("./identifier")
            _category = element.attrib["category"]
            if _category == "field":
                _category = "this"
            _index = element.attrib["index"]
            self.write_push(_category, int(_index))
        
        # handle unaryOp term
        elif len(term.findall("./symbol")) == 1 and len(term.findall("./term")) == 1:
            _term = term.find("./term")
            self.compile_term(_term)
            unary_op = term.find("./symbol").text.strip()
            self.write_arithmetic(self.unary_op_map[unary_op])

        #'(' expression ')'
        elif list(term)[0].text.strip() == "(":
            expression = term.find("./expression")
            self.compile_expression(expression)

        # subroutine_call . ( )
        elif len(term.findall("./symbol")) >= 2:
            symbols = term.findall("./symbol")
            identifiers = term.findall("./identifier")
            subroutine_name = ""
            is_object_method_call = 0
            expression_list = term.find("./expressionList")
            if symbols[0].text.strip() == '.':
                if identifiers[0].attrib['category'] != "class":  # This is a method call.
                    # Push the reference of 'this' object onto the stack
                    _segment = identifiers[0].attrib['category']
                    _index = identifiers[0].attrib['index']
                    self.write_push(_segment, int(_index))
                    is_object_method_call = 1

                    subroutine_name = identifiers[0].attrib['type'] + "." + identifiers[1].text.strip()
                elif identifiers[0].attrib['category'] == 'subroutine' and identifiers[0].text.strip() in self.method_names: # This is also a method call.
                    # <identifier category="subroutine" purpose="used"> draw </identifier>
                    subroutine_name = self.class_name + "." + identifiers[0].text.strip()
                else:
                    # Output.printInt
                    # <identifier category="class" purpose="used"> Output </identifier>
                    # <symbol> . </symbol>
                    # <identifier category="subroutine" purpose="used"> printInt </identifier>
                    subroutine_name = identifiers[0].text.strip() + "." + identifiers[1].text.strip()
            else:
                subroutine_name = identifiers[0].text.strip()
                # this is a method call within defining class itself.
                if subroutine_name in self.method_names:
                    subroutine_name = self.class_name + "." + subroutine_name
                    self.write_push("pointer", 0)
                    is_object_method_call = 1
            
            self.compile_subroutine_call(subroutine_name, expression_list, is_object_method_call)
       
    def compile_class_var_dec(self, class_var_dec):
        vars = class_var_dec.findall("./identifier")
        for var in vars:
            if var.attrib["category"] == "field" and var.attrib["purpose"] == "defined":
                self.class_var_count += 1

    def compile(self):
        # part.1 classVarDec*
        class_var_list = self.xml.findall("./classVarDec")
        for class_var in class_var_list:
            self.compile_class_var_dec(class_var)

        # part.2 subroutineDec
        class_name = self.get_class_name()

        subroutine_dec_list = self.xml.findall("./subroutineDec")
        for sub_routine_dec in subroutine_dec_list:
            self.compile_subroutine_dec(class_name, sub_routine_dec)
        return

def main():
    path = sys.argv[1]
    jack_analyzer = JackCompiler(path)
    jack_analyzer.analyze()

if __name__ == '__main__':
	main()