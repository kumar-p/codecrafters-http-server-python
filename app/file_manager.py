"""Secure file operations with path traversal protection."""

from pathlib import Path
from logging import Logger


class FileSecurityError(Exception):
    """Raised when file operation violates security policy."""

    pass


class FileManager:
    """
    Secure file operations with path traversal protection.

    Security features:
    - Validates all paths stay within base directory
    - Resolves symlinks and relative paths
    - Enforces file size limits
    - Uses binary read/write for safety
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

    def __init__(self, base_directory: str, logger: Logger):
        """
        Initialize FileManager with a base directory.

        Args:
            base_directory: Directory to confine all file operations
            logger: Logger instance for debug/error messages

        Raises:
            ValueError: If base_directory doesn't exist or isn't a directory
        """
        self.base_dir = Path(base_directory).resolve()
        self.logger = logger

        if not self.base_dir.exists():
            raise ValueError(f"Base directory does not exist: {base_directory}")
        if not self.base_dir.is_dir():
            raise ValueError(f"Base directory is not a directory: {base_directory}")

    def read_file(self, filename: str) -> bytes:
        """
        Read file as bytes with security validation.

        Args:
            filename: Relative filename within base directory

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            FileSecurityError: If path violates security policy or file too large
        """
        file_path = self._validate_path(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        if not file_path.is_file():
            raise FileSecurityError(f"Path is not a file: {filename}")

        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise FileSecurityError(
                f"File too large: {file_size} bytes (max: {self.MAX_FILE_SIZE})"
            )

        self.logger.debug(f"Reading file: {file_path}")
        return file_path.read_bytes()

    def write_file(self, filename: str, content: bytes) -> None:
        """
        Write file as bytes with security validation.

        Args:
            filename: Relative filename within base directory
            content: File contents as bytes

        Raises:
            FileSecurityError: If path violates security policy or content too large
            PermissionError: If write permission denied
        """
        if len(content) > self.MAX_FILE_SIZE:
            raise FileSecurityError(
                f"Content too large: {len(content)} bytes (max: {self.MAX_FILE_SIZE})"
            )

        file_path = self._validate_path(filename)

        # Ensure parent directory exists within base_dir
        parent = file_path.parent
        if not parent.exists():
            # Validate parent is also within base_dir
            self._validate_path(str(parent.relative_to(self.base_dir)))
            parent.mkdir(parents=True, exist_ok=True)

        self.logger.debug(f"Writing file: {file_path}")
        file_path.write_bytes(content)

    def file_exists(self, filename: str) -> bool:
        """
        Check if file exists (with path validation).

        Args:
            filename: Relative filename within base directory

        Returns:
            True if file exists and is a file, False otherwise
        """
        try:
            file_path = self._validate_path(filename)
            return file_path.is_file()
        except (FileSecurityError, ValueError):
            return False

    def _validate_path(self, filename: str) -> Path:
        """
        Validate path prevents directory traversal attacks.

        Args:
            filename: Relative filename to validate

        Returns:
            Resolved absolute path within base_dir

        Raises:
            FileSecurityError: If path escapes base_dir or contains dangerous characters
        """
        # Prevent null bytes and other dangerous characters
        if "\0" in filename or "\x00" in filename:
            raise FileSecurityError("Null bytes in filename")

        # Create path and resolve to absolute (handles .., symlinks, etc)
        requested_path = (self.base_dir / filename).resolve()

        # Critical: Verify resolved path is still within base_dir
        try:
            requested_path.relative_to(self.base_dir)
        except ValueError:
            raise FileSecurityError(f"Path traversal attempt detected: {filename}")

        return requested_path
