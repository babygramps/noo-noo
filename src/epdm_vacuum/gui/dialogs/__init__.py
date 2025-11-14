"""
GUI Dialogs Package

Contains dialog windows for the application:
- Sequence editor dialog
- I/O action dialog
- Other dialogs as needed
"""

from .sequence_editor import SequenceEditorDialog
from .io_action_dialog import IOActionDialog

__all__ = ["SequenceEditorDialog", "IOActionDialog"]

