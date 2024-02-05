import sys
import os
import re
import xml.etree.ElementTree as ET
import xml.dom.minidom

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

    def compile_var_desc(self):
        """
        Compiles a var declaration.
        """
        self.output.append("<varDec>")

        # 'var'
        self.eat("keyword") # 'var' is a keyword
        self.output.append(f"<keyword> var </keyword>")

        # 'type' which can be either a primitive type or a className (identifier)
        if self.get_current_token_type() in ["keyword", "identifier"]:
            type_token = self.get_current_token_value()
            type_token_type = self.get_current_token_type()
            self.output.append(f"<{type_token_type}> {type_token} </{type_token_type}>")
            self.advance()
        else:
            raise ValueError("Expected type keyword or identifier, but actual value is {type_token_type}")
        
        # varName(s)
        while True:
            _value = self.eat("identifier")
            self.output.append(f"<identifier> {_value} </identifier>")
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
        _value = self.eat("keyword") 
        self.output.append(f"<keyword> {_value} </keyword>")

        # 'type' which can be either a primitive type or a className (identifier)
        if self.get_current_token_type() in ["keyword", "identifier"]:
            type_token = self.get_current_token_value()
            type_token_type = self.get_current_token_type()
            self.output.append(f"<{type_token_type}> {type_token} </{type_token_type}>")
            self.advance()
        else:
            raise ValueError("Expected type keyword or identifier, but actual value is {type_token_type}") 

        # varName(s)
        while True:
            _value = self.eat("identifier")
            self.output.append(f"<identifier> {_value} </identifier>")
            if self.get_current_token_value() == ";":
                break
            self.eat("symbol") # Comma
            self.output.append(f"<symbol> , </symbol>")
        
        # ';'
        self.eat("symbol")
        self.output.append(f"<symbol> ; </symbol>") 

        self.output.append("</classVarDec>")

    def compile_parameter_list(self):
        """
        Compiles a (possibly empty) parameter list. 
        Does not handle the enclosing "()".
        """
        self.output.append("<parameterList>")

        # Check if there is at least one parameter
        if self.get_current_token_type() in ["keyword", "identifier"]:
            # parameter(s)
            while True:
                # type
                if self.get_current_token_type() in ["keyword", "identifier"]:
                    type_token_type = self.get_current_token_type()
                    type_token_value = self.get_current_token_value()
                    self.output.append(f"<{type_token_type}> {type_token_value} </{type_token_type}>")
                    self.advance()
                else:
                    raise ValueError("Expected type keyword or identifier for parameter")

                # varName
                _value = self.eat("identifier")
                self.output.append(f"<identifier> {_value} </identifier>")

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
            self.output.append(f"<identifier> {_value} </identifier>")
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
            self.output.append(f"<identifier> {_value} </identifier>")

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
        self.output.append(f"<identifier> {_value} </identifier>")

        # Check for '.' indicating a method call on an object or class
        if self.get_current_token_value() == '.':
            self.eat("symbol")
            self.output.append(f"<symbol> . </symbol>") 
            _value = self.eat("identifier")
            self.output.append(f"<identifier> {_value} </identifier>")

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
        self.output.append(f"<identifier> {_value} </identifier>")

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

        # subroutineCall
        self.compile_subroutine_call()

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
            self.compile_var_desc()

        # statements
        self.compile_statements()

        # }
        self.eat("symbol")
        self.output.append("<symbol> } </symbol>")

        self.output.append("</subroutineBody>")

    def compile_subroutine_dec(self):
        """
        Compile subroutine 
        """
        self.output.append("<subroutineDec>")

        # ('constructor' | 'function' | 'method')
        _value = self.eat("keyword")
        self.output.append(f"<keyword> {_value} </keyword>")

        # ('void' | type)
        _value = self.get_current_token_value()
        if _value in ["void", "int", "char", "boolean"]:
            self.output.append(f"<keyword> {_value} </keyword>")
        else:
            self.output.append(f"<identifier> {_value} </identifier>")
        self.advance()
        
        # subroutineName
        _value = self.eat("identifier")
        self.output.append(f"<identifier> {_value} </identifier>")

        # '('
        self.eat("symbol")
        self.output.append(f"<symbol> ( </symbol>")

        # parameterList
        self.compile_parameter_list()

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
        _value = self.eat("identifier")
        self.output.append(f"<identifier> {_value} </identifier>")

        # {
        self.eat("symbol")
        self.output.append("<symbol> { </symbol>")

        # classVarDec*
        while self.get_current_token_value() in ["field", "static"] and self.get_current_token_type() == "keyword":
            self.compile_class_var_dec()

        # subroutineDec*
        while self.get_current_token_value() in ["constructor", "function", "method"] and self.get_current_token_type() == "keyword":
            self.compile_subroutine_dec() 

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

class JackAnalyzer:
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
        # tokenizer.save_token_file(tokenized_xml)
        engine = CompilationEngine(tokenized_xml, tokenizer.file_name[:-5])
        engine.compile_class()
        result = engine.format_xml_string()
        engine.save_xml_file(result)

    def analyze(self):
        for file in self.files:
            self.analyze_one_file(file)

def main():
    path = sys.argv[1]
    jack_analyzer = JackAnalyzer(path)
    jack_analyzer.analyze()

if __name__ == '__main__':
	main()