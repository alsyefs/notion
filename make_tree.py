# Utility script to generate a directory tree while excluding specific folders
# Usage: python make_tree.py
import os

# Define folders to ignore
EXCLUDE_DIRS = {
    "__pycache__",
    "notion",
    "coverage_report_html",
    "venv",
    ".git",
    ".idea",
    "__init__",
}

# Limits for the 'attachments' folder structure
MAX_ATTACHMENT_FOLDERS = 0  # Limit how many subfolders to show inside 'attachments/'
MAX_ATTACHMENT_FILES = 0  # Limit how many files to show inside those subfolders


def generate_tree(startpath):
    output_lines = []

    # Recursive function to walk directories with custom logic
    def walk_dir(current_path, level, inside_attachments=False):
        try:
            # Sort entries for consistent order
            entries = sorted(os.listdir(current_path))
        except PermissionError:
            return

        # Separate directories and files
        dirs = []
        files = []
        for entry in entries:
            full_path = os.path.join(current_path, entry)
            if os.path.isdir(full_path):
                if entry not in EXCLUDE_DIRS:
                    dirs.append(entry)
            else:
                files.append(entry)

        # Logic to handle 'attachments' folder limits
        is_attachments_root = os.path.basename(current_path) == "attachments"

        # If we are at the root 'attachments' folder, we are now "inside" the structure
        if is_attachments_root:
            inside_attachments = True

        has_more_dirs = False
        has_more_files = False

        if inside_attachments:
            # 1. Limit folders ONLY at the root of 'attachments/'
            if is_attachments_root and len(dirs) > MAX_ATTACHMENT_FOLDERS:
                dirs = dirs[:MAX_ATTACHMENT_FOLDERS]
                has_more_dirs = True

            # 2. Limit files recursively everywhere inside 'attachments/' (root or subfolders)
            if len(files) > MAX_ATTACHMENT_FILES:
                files = files[:MAX_ATTACHMENT_FILES]
                has_more_files = True

        indent = "    " * level

        # Process directories
        for d in dirs:
            output_lines.append(f"{indent}{d}/")
            # Pass 'inside_attachments' flag down to children
            walk_dir(os.path.join(current_path, d), level + 1, inside_attachments)

        if has_more_dirs:
            output_lines.append(f"{indent}...")

        # Process files
        for f in files:
            if f in ["tree.txt", "make_tree.py"]:
                continue
            output_lines.append(f"{indent}{f}")

        if has_more_files:
            output_lines.append(f"{indent}...")

    # Start the recursion
    root_name = os.path.basename(os.path.abspath(startpath))
    output_lines.append(f"{root_name}/")
    walk_dir(startpath, 1)

    # Write to file
    with open("tree.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"Tree structure saved to {os.path.abspath('tree.txt')}")


if __name__ == "__main__":
    generate_tree(".")
