"""Bit-flag enum for background task control in GEDCOM processing workflow.

This module defines DoActionsType, a Flag enum used to coordinate background
operations between the UI and worker thread. Multiple operations can be combined
using bitwise OR, and the enum provides helper methods for checking flags and
determining whether parsing should occur based on current state.
"""
from enum import Flag, auto


class DoActionsType(Flag):
    """Bit-flag enum for coordinating background GEDCOM processing operations.
    
    This enum acts as a state machine for the background worker thread, allowing
    multiple operations to be combined and checked independently. The flags control
    parsing, geocoding, and output generation workflows.
    
    Flags:
        NONE: No operations pending (IDLE state, value=0).
        PARSE: Parse GEDCOM file and geocode all addresses (value=1).
        GENERATE: Generate output files (HTML/KML/SUM) from parsed data (value=2).
        REPARSE_IF_NEEDED: Conditionally parse only if not already parsed (value=4).
    
    Flag Combinations:
        Flags can be combined using bitwise OR (|) operator:
        - PARSE | GENERATE: Parse then generate in sequence
        - GENERATE | REPARSE_IF_NEEDED: Generate, parsing first if needed
    
    Usage Examples:
        >>> # Create action flags
        >>> action = DoActionsType.NONE                           # Idle state
        >>> action = DoActionsType.PARSE                          # Single operation
        >>> action = DoActionsType.PARSE | DoActionsType.GENERATE # Multiple ops
        
        >>> # Check if specific flag is set
        >>> if DoActionsType.PARSE in action:
        ...     print("Will parse")
        
        >>> # Use helper methods
        >>> if action.has_parse():
        ...     print("Parse flag is set")
        
        >>> # Check if should parse based on state
        >>> if action.should_parse(already_parsed=False):
        ...     print("Need to parse")
        
        >>> # Get human-readable description
        >>> print(action.describe())  # "PARSE | GENERATE"
    
    Thread Safety:
        Flag checks are atomic operations. The enum itself is immutable after
        creation, making it safe to pass between threads.
    
    See Also:
        background_actions.BackgroundActions: Worker thread that consumes these flags.
        visual_map_actions.VisualMapActions: UI actions that trigger background work.
    """
    NONE = 0                    # 0 - No operations (IDLE state)
    PARSE = auto()              # 1 - Parse GEDCOM and geocode addresses
    GENERATE = auto()           # 2 - Generate output files (HTML/KML/SUM)
    REPARSE_IF_NEEDED = auto()  # 4 - Conditional parse (only if not already done)
    
    def has_parse(self) -> bool:
        """Check if PARSE flag is set.
        
        Returns:
            bool: True if PARSE flag is set, False otherwise.
        
        Example:
            >>> action = DoActionsType.PARSE | DoActionsType.GENERATE
            >>> action.has_parse()
            True
        """
        return bool(self & DoActionsType.PARSE)
    
    def has_generate(self) -> bool:
        """Check if GENERATE flag is set.
        
        Returns:
            bool: True if GENERATE flag is set, False otherwise.
        
        Example:
            >>> action = DoActionsType.PARSE | DoActionsType.GENERATE
            >>> action.has_generate()
            True
        """
        return bool(self & DoActionsType.GENERATE)
    
    def has_reparse_if_needed(self) -> bool:
        """Check if REPARSE_IF_NEEDED flag is set.
        
        Returns:
            bool: True if REPARSE_IF_NEEDED flag is set, False otherwise.
        
        Example:
            >>> action = DoActionsType.REPARSE_IF_NEEDED
            >>> action.has_reparse_if_needed()
            True
        """
        return bool(self & DoActionsType.REPARSE_IF_NEEDED)
    
    def should_parse(self, already_parsed: bool = False) -> bool:
        """Determine if parsing operation should occur based on flags and current state.
        
        This method implements conditional parsing logic:
        - Always parse if PARSE flag is set
        - Parse if REPARSE_IF_NEEDED is set AND not already parsed
        - Don't parse otherwise
        
        This allows efficient workflows where generation can be triggered without
        redundant re-parsing if data is already loaded.
        
        Args:
            already_parsed: Whether GEDCOM file has been parsed in current session.
                           Typically comes from gOp.parsed flag. Default: False.
        
        Returns:
            bool: True if parsing should occur, False if it can be skipped.
        
        Examples:
            >>> action = DoActionsType.PARSE
            >>> action.should_parse(already_parsed=True)   # True (explicit PARSE)
            True
            >>> action.should_parse(already_parsed=False)  # True (explicit PARSE)
            True
            
            >>> action = DoActionsType.REPARSE_IF_NEEDED
            >>> action.should_parse(already_parsed=True)   # False (already done)
            False
            >>> action.should_parse(already_parsed=False)  # True (need to parse)
            True
            
            >>> action = DoActionsType.GENERATE
            >>> action.should_parse(already_parsed=False)  # False (no parse flag)
            False
        
        See Also:
            background_actions.BackgroundActions._run_parse(): Uses this to decide
            whether to execute parse operation.
        """
        return self.has_parse() or (self.has_reparse_if_needed() and not already_parsed)
    
    def doing_something(self) -> bool:
        """Check if any operation flags are set (worker is not idle).
        
        Returns:
            bool: True if any flags are set (not NONE), False if idle (NONE).
        
        Example:
            >>> DoActionsType.NONE.doing_something()
            False
            >>> DoActionsType.PARSE.doing_something()
            True
            >>> (DoActionsType.PARSE | DoActionsType.GENERATE).doing_something()
            True
        
        Note:
            This is used by the background worker thread to determine if work
            is pending and the main loop should process actions.
        """
        return self != DoActionsType.NONE
    
    def describe(self) -> str:
        """Return human-readable description of the active flags.
        
        Converts the bit-flags into a readable string format suitable for
        logging and debugging. Multiple flags are joined with " | " separator.
        
        Returns:
            str: Description of active flags, or "IDLE" if NONE, or
                 "UNKNOWN(value)" if unrecognized flag combination.
        
        Examples:
            >>> DoActionsType.NONE.describe()
            'IDLE'
            >>> DoActionsType.PARSE.describe()
            'PARSE'
            >>> (DoActionsType.PARSE | DoActionsType.GENERATE).describe()
            'PARSE | GENERATE'
            >>> (DoActionsType.GENERATE | DoActionsType.REPARSE_IF_NEEDED).describe()
            'GENERATE | REPARSE_IF_NEEDED'
        
        Note:
            Used internally by __repr__() and useful for logging messages.
        """
        if self == DoActionsType.NONE or not self:
            return "IDLE"
        parts = []
        if self.has_parse():
            parts.append("PARSE")
        if self.has_generate():
            parts.append("GENERATE")
        if self.has_reparse_if_needed():
            parts.append("REPARSE_IF_NEEDED")
        return " | ".join(parts) if parts else f"UNKNOWN({self.value})"
    
    def __repr__(self) -> str:
        """Return string representation for debugging and logging.
        
        Returns:
            str: String in format "DoActionsType(description)" where description
                 is the human-readable flag combination from describe().
        
        Example:
            >>> repr(DoActionsType.PARSE)
            'DoActionsType(PARSE)'
            >>> repr(DoActionsType.PARSE | DoActionsType.GENERATE)
            'DoActionsType(PARSE | GENERATE)'
        """
        return f"DoActionsType({self.describe()})"
