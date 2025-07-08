"""
Simple test file to verify VS Code test discovery is working.
"""

def test_simple_pass():
    """Simple test that always passes."""
    assert True


def test_simple_math():
    """Simple math test."""
    assert 2 + 2 == 4


class TestSimpleClass:
    """Simple test class."""
    
    def test_method(self):
        """Simple test method."""
        assert "hello" == "hello"