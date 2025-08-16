from tools.base_tool import BaseTool
import re
import ast
import operator

class CalculatorTool(BaseTool):
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "calculator"
        self.description = "Perform mathematical calculations safely"
    
    def _is_safe_expression(self, expression):
        """Check if the expression is safe to evaluate"""
        # Allow only numbers, operators, parentheses, and whitespace
        allowed_chars = re.compile(r'^[0-9+\-*/(). ]+$')
        if not allowed_chars.match(expression):
            return False
        
        # Additional safety check using AST
        try:
            node = ast.parse(expression, mode='eval')
            # Only allow certain node types
            allowed_nodes = (ast.Expression, ast.Constant, ast.Num, ast.BinOp, 
                            ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, 
                            ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Load)
            
            for n in ast.walk(node):
                if not isinstance(n, allowed_nodes):
                    return False
            return True
        except Exception:
            return False
    
    def _safe_eval(self, expression):
        """Safely evaluate a mathematical expression"""
        # Define allowed operators
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        def eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Num):  # For older Python versions
                return node.n
            elif isinstance(node, ast.BinOp):
                left = eval_node(node.left)
                right = eval_node(node.right)
                return operators[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_node(node.operand)
                return operators[type(node.op)](operand)
            else:
                raise ValueError("Unsupported operation")
        
        node = ast.parse(expression, mode='eval')
        return eval_node(node.body)
    
    def execute(self, expression):
        """
        Perform a mathematical calculation safely.
        
        Args:
            expression (str): Mathematical expression to evaluate
            
        Returns:
            dict: Result of the calculation
        """
        try:
            # Basic security check
            if not self._is_safe_expression(expression):
                return {"error": "Invalid or unsafe expression"}
            
            # Evaluate the expression safely
            result = self._safe_eval(expression)
            
            # Check for reasonable result size
            if abs(result) > 1e10:
                return {"error": "Result too large"}
            
            return {"expression": expression, "result": result}
        except Exception as e:
            return {"error": f"Calculation failed: {str(e)}"}