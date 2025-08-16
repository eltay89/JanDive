class BaseTool:
    def __init__(self, config=None):
        self.config = config or {}
        self.name = ""
        self.description = ""
    
    def execute(self, **kwargs):
        raise NotImplementedError("Execute method must be implemented by subclasses")