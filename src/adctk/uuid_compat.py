# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
import uuid
import warnings

class UUID7Generator:
    """A wrapper class that provides UUIDv7 generation.
    
    It uses the native standard library `uuid.uuid7` if available (Python >= 3.14).
    Otherwise, it falls back to the third-party `uuid_utils`.
    """
    
    # Class-level flag to store the resolved generation function
    _uuid7_func = None

    @classmethod
    def _initialize(cls) -> None:
        """Dynamically detects the best available UUIDv7 implementation."""
        if hasattr(uuid, "uuid7"):
            cls._uuid7_func = uuid.uuid7
            return

        try:
            import uuid_utils
            cls._uuid7_func = uuid_utils.uuid7
            return
        except ImportError:
            pass

        try:
            import uuid6
            cls._uuid7_func = uuid6.uuid7
            warnings.warn(
                "Standard 'uuid.uuid7' and 'uuid_utils' not found. "
                "Falling back to slower, pure-Python 'uuid6' package.",
                RuntimeWarning
            )
            return
        except ImportError:
            pass

        raise ImportError(
            "No valid UUIDv7 implementation found. Please upgrade to "
            "Python >= 3.14 or install 'uuid-utils' via 'pip install uuid-utils'."
        )

    @classmethod
    def uuid7(cls) -> uuid.UUID:
        """Generates a UUIDv7 object using the best available backend.
        
        Returns:
            uuid.UUID: A standard Python UUID object.
        """
        if cls._uuid7_func is None:
            cls._initialize()
            
        return cls._uuid7_func()


# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    try:
        # Generate a UUIDv7
        my_uuid = UUID7Generator.uuid7()
        
        print(f"Generated UUID: {my_uuid}")
        print(f"Object Type:    {type(my_uuid)}")
        print(f"UUID Version:   {my_uuid.version}")
        
    except ImportError as e:
        print(f"Error: {e}")

