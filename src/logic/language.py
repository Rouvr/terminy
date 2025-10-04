
"""
Fallback language implementation for the logic layer.

This module provides a dummy Language class that acts as a fallback when
the GUI language module (which depends on PySide6) cannot be imported.
This ensures the logic layer can function independently of GUI dependencies.
"""

try:
    from src.gui.language import Language # type: ignore
except ImportError:
    # Fallback implementation when GUI dependencies are not available
    class Language:
        """
        Dummy language implementation that returns keys as-is.
        
        This fallback ensures that logic components can still call Language.get()
        without crashing when GUI components are unavailable (e.g., in headless
        environments, tests, or when PySide6 is not installed).
        """
        
        @staticmethod
        def get(key: str, locale=None) -> str:
            """
            Return the key as-is since no translations are available.
            
            Args:
                key: The language key to translate
                locale: Ignored in fallback implementation
                
            Returns:
                The original key string
            """
            return key
        
        @staticmethod
        def load_translations(lang_dir=None) -> bool:
            """Dummy implementation - no translations to load."""
            return False
        
        @staticmethod
        def get_current_locale():
            """Return None since no locale system is available."""
            return None
        
        @staticmethod
        def save_locale(locale):
            """Dummy implementation - cannot save locale without GUI layer."""
            pass
        
        @staticmethod
        def dump_requests():
            """Return empty list since no requests are tracked."""
            return []