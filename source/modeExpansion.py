from calculZone import ZoneCalculateur
from dataclasses import dataclass, field

@dataclass
class ZoneModeExpansion(ZoneCalculateur):
    #TODO: Fixer une valuer pour epsilon
    epsilon: float = 0.1 
    
    def algorithm(self):
        pass
