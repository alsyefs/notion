# backend/terminal_style.py
import os


class PrintStyle:
    """
    Handles terminal styling, colors, and formatted output blocks.
    Change the color constants here to update the theme across the entire app.
    """

    # Theme Constants
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    DIM = "\033[2m"
    HEADER = BOLD + CYAN

    @staticmethod
    def stylize_path(path):
        """
        Converts an absolute path to a relative path from the current working directory.
        This makes it shorter to read but keeps it clickable in most terminals (VS Code, etc).
        """
        try:
            rel_path = os.path.relpath(path, os.getcwd())
            # Check if relative path is actually shorter/cleaner, else return original
            if len(rel_path) < len(path):
                return f".{os.sep}{rel_path}"
            return path
        except ValueError:
            return path

    @classmethod
    def print_header(cls, title):
        """Prints a major section header (Double Box)."""
        print(
            f"\n{cls.BOLD}{cls.CYAN}╔════════════════════════════════════════════════════════════════╗{cls.RESET}"
        )
        print(f"{cls.BOLD}{cls.CYAN}║ {title.center(62)} ║{cls.RESET}")
        print(
            f"{cls.BOLD}{cls.CYAN}╚════════════════════════════════════════════════════════════════╝{cls.RESET}"
        )

    @classmethod
    def print_header(cls, title):
        """Prints a major section header (Double Box)."""
        print(
            f"\n{cls.BOLD}{cls.MAGENTA}╔════════════════════════════════════════════════════════════════╗{cls.RESET}"
        )
        print(f"{cls.BOLD}{cls.MAGENTA}║ {title.center(62)} ║{cls.RESET}")
        print(
            f"{cls.BOLD}{cls.MAGENTA}╚════════════════════════════════════════════════════════════════╝{cls.RESET}"
        )

    @classmethod
    def print_subheader(cls, title):
        """Prints a subsection header (Single Line)."""
        print(f"\n{cls.BLUE}--- {title.upper()} ---{cls.RESET}")

    @classmethod
    def print_step(cls, step, total, message):
        """Prints a execution step in a standardized format."""
        print(f"\n{cls.BOLD}{cls.CYAN}[{step}/{total}] ➤ {message}...{cls.RESET}")

    @classmethod
    def print_success(cls, message, label="SUCCESS"):
        """Prints a success message with a green checkmark."""
        print(f"  {cls.GREEN}✅ {label}: {message}{cls.RESET}")

    @classmethod
    def print_saved(cls, label, path):
        """Prints a file saved message with a clickable relative path."""
        clean_path = cls.stylize_path(path)
        print(f"  {cls.GREEN}💾 {label}:{cls.RESET} {cls.DIM}{clean_path}{cls.RESET}")

    @classmethod
    def print_warning(cls, message, label="WARNING"):
        """Prints a warning message with a yellow alert."""
        print(f"  {cls.YELLOW}⚠️  {label}: {message}{cls.RESET}")

    @classmethod
    def print_error(cls, message, label="ERROR"):
        """Prints an error message with a red alert."""
        print(f"  {cls.RED}❌ {label}: {message}{cls.RESET}")

    @classmethod
    def print_info(cls, message):
        """Prints a neutral info message."""
        print(f"  ℹ️  {message}")

    @classmethod
    def print_divider(cls):
        """Prints a horizontal divider line."""
        print(
            f"{cls.CYAN}──────────────────────────────────────────────────────────────────{cls.RESET}"
        )


class TextHelper:
    """
    Handles general text manipulation: cleaning, truncating, and formatting.
    """

    @staticmethod
    def clean_text(text):
        """
        Removes special characters, smart quotes, and emojis.
        Useful for preparing text for PDFs or simple console output.
        """
        if text is None:
            return ""
        if isinstance(text, float):  # Handle NaN
            return ""
        if not isinstance(text, str):
            return str(text)

        replacements = {
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "–": "-",
            "—": "-",
            "…": "...",
            "🙌": "",
            "🚀": "",
            "📂": "",
            "🚨": "",
            "👴": "",
            "⚖️": "Licensing: ",
            "⚠️": "Warning: ",
        }
        for char, rep in replacements.items():
            text = text.replace(char, rep)
        return text

    @staticmethod
    def truncate_text(text, max_length=60):
        """
        Truncates text to a specific length and adds ellipses.
        """
        if not isinstance(text, str):
            return str(text)
        return f"{text[:max_length-3]}..." if len(text) > max_length else text
