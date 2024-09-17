import os

def print_directory_tree(root_dir, prefix="", exclude_dirs=None):
    """
    Print the directory tree starting from the given root directory.

    :param root_dir: The root directory to start the tree.
    :param prefix: The prefix string for formatting the tree.
    :param exclude_dirs: A list of directories to exclude from the tree.
    """
    if exclude_dirs is None:
        exclude_dirs = []

    items = os.listdir(root_dir)
    # Remove hidden files and directories and excluded directories
    items = [item for item in items if not item.startswith('.') and item not in exclude_dirs]
    # Sort items so directories come first
    items.sort(key=lambda item: (not os.path.isdir(os.path.join(root_dir, item)), item.lower()))

    for index, item in enumerate(items):
        path = os.path.join(root_dir, item)
        if index == len(items) - 1:
            print(prefix + "└── " + item)
            if os.path.isdir(path):
                print_directory_tree(path, prefix + "    ", exclude_dirs)
        else:
            print(prefix + "├── " + item)
            if os.path.isdir(path):
                print_directory_tree(path, prefix + "│   ", exclude_dirs)

if __name__ == "__main__":
    # Set the directory you want to print the structure of
    root_directory = "E:/website project/nh_bill_tracker"
    exclude_directories = ["venv"]

    print(root_directory)
    print_directory_tree(root_directory, exclude_dirs=exclude_directories)
