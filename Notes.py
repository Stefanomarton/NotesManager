#!/usr/bin/python
import os
import click
import subprocess

# Importing rich for rich text rendering
from rich.console import Console

# Create a console object to print colored and formatted text
console = Console()


@click.group()
def notes():
    """Manage your files and notes."""
    pass


@notes.command()
@click.option(
    "--directory",
    default="~/GoogleDrive",
    help="Directory to store all notes and files",
)
@click.option("--pdf-only", is_flag=True, help="Search for PDF files only")
@click.option("--uni", is_flag=True, help="Search in ~/GoogleDrive/Universitá only")
def open_file(directory, pdf_only, uni):
    """Open a note file, PDF, or EPUB using the appropriate viewer."""
    # Expand the tilde '~' symbol to the user's home directory
    directory = os.path.expanduser(directory)

    if pdf_only:
        allowed_file_types = {".pdf"}
    else:
        allowed_file_types = {".pdf", ".epub", ".md"}  # Add more file types as needed

    if uni:
        directory = os.path.join(directory, "Università")

    files = get_file_list(directory, allowed_file_types)
    if not files:
        console.print("[red]Error:[/red] No files found.")
        return

    selected_file = fzf_select(files)
    if not selected_file:
        console.print("[red]Error:[/red] No file selected.")
        return

    file_extension = os.path.splitext(selected_file)[1]
    if file_extension == ".md":
        # Open Markdown (.md) files using nvim or your preferred text editor
        subprocess.run(["nvim", selected_file])
    elif file_extension == ".pdf":
        # Open PDF files using zathura or your preferred PDF reader detached from the terminal
        subprocess.Popen(["zathura", selected_file], preexec_fn=os.setpgrp)
    elif file_extension == ".epub":
        # Open EPUB files using ebook-viewer or your preferred EPUB reader
        subprocess.run(["ebook-viewer", selected_file])
    else:
        console.print("[red]Error:[/red] Unsupported file type.")


def get_file_list(directory, allowed_file_types):
    """Get a list of files in the specified directory based on allowed file types."""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext.lower() in allowed_file_types:
                files.append(os.path.join(root, filename))
    return files


def fzf_select(files):
    """Use fzf to interactively select a file."""
    # Get the file names without the '~/GoogleDrive/' part for user selection
    file_names = [
        file.replace(os.path.expanduser("~/GoogleDrive/"), "") for file in files
    ]

    # Join the file names back with newline characters for fzf input
    fzf_input = "\n".join(file_names)

    # Prepare the fzf command with the original files list for the preview
    fzf_cmd = ["fzf"]

    try:
        # Run fzf command and capture the selected file name
        selected_file_name = subprocess.check_output(
            fzf_cmd, input=fzf_input, text=True
        ).strip()

        # Retrieve the full path of the selected file using the original list
        selected_file = next(
            file for file in files if file.endswith(selected_file_name)
        )

        # Display the file using the appropriate viewer based on its extension
        open_file_with_appropriate_viewer(selected_file)
    except subprocess.CalledProcessError:
        return None


@notes.command()
@click.argument("note_name", type=click.Path(exists=False))
@click.option(
    "--directory",
    "-d",
    default="~/GoogleDrive",
    help="Specify the directory where the note should be created.",
)
def create(note_name, directory):
    """Create a note in the default dir"""
    # Expand the tilde (~) in the directory path
    directory = os.path.expanduser(directory)

    # Check if the note already exists
    note_path = os.path.join(directory, f"{note_name}.md")
    if os.path.exists(note_path):
        click.secho(f"Error: Note '{note_name}' already exists.", fg="red")
        return
    else:
        # Create the new note file
        with open(note_path, "w") as file:
            file.write("# " + note_name)
        click.secho(f"Success: Note '{note_name}' created in {directory}.", fg="green")

    # Open the newly created note with the default text editor
    try:
        subprocess.run([os.environ.get("EDITOR", "vi"), note_path], check=True)
    except subprocess.CalledProcessError as e:
        click.secho(f"Error opening the note with the text editor: {e}", fg="red")
        return


@notes.command()
@click.argument("project_name")
@click.option("--template", default="default", help="Project template to use")
@click.option(
    "-g",
    "--git",
    is_flag=True,
    help="Initialize a Git repository in the project folder",
)
@click.option(
    "--directory",
    default="~/GoogleDrive/Projects",
    help="Specify a custom project folder path",
)
def create_project(project_name, template, git, directory):
    """Create a new project folder based on a template."""
    # Project templates (you can add more as needed)

    project_templates = {
        "default": {
            "notes": ["notes.md"],
            "notes/reference": [],
        },
        "webapp": {
            "src": ["src", "app.py", "static", "templates"],
            "data": ["data"],
            "docs": ["docs"],
            "README.md": "",
        },
    }

    # Expand the user directory in the provided project folder path
    directory = os.path.expanduser(directory)

    # Create the project folder path
    project_path = os.path.join(directory, project_name)

    # Check if the project folder already exists
    if os.path.exists(project_path):
        console.print(f"[red]Error:[/red] Project '{project_name}' already exists.")
        return

    # Check if the specified template exists
    if template not in project_templates:
        console.print(f"[red]Error:[/red] Template '{template}' not found.")
        return

    # Create the project folder
    os.makedirs(project_path)

    # Copy files and folders from the template to the project folder
    template_files = project_templates[template]
    for folder, items in template_files.items():
        folder_path = os.path.join(project_path, folder)
        os.makedirs(folder_path)
        for item in items:
            if isinstance(item, str):  # File
                with open(os.path.join(folder_path, item), "w") as file:
                    pass
            else:  # Directory
                os.makedirs(os.path.join(folder_path, item))

    console.print(
        f"[green]Success:[/green] Project '{project_name}' created with template '{template}'."
    )

    # Initialize a Git repository if the --git flag is specified
    if git:
        git_init(project_path)


def git_init(project_path):
    """Initialize a Git repository in the project folder."""
    try:
        subprocess.run(["git", "init"], cwd=project_path, check=True)
        console.print("[green]Success:[/green] Git repository initialized.")
    except subprocess.CalledProcessError:
        console.print("[red]Error:[/red] Failed to initialize Git repository.")


@notes.command()
@click.option(
    "--directory",
    default="~/GoogleDrive/Projects",
    help="Directory to store all notes and files",
)
def search_project(directory):
    """Search and open files within the project directory and its subfolders."""
    # Expand the tilde '~' symbol to the user's home directory
    directory = os.path.expanduser(directory)

    first_level_folders = get_first_level_folders(directory)
    if not first_level_folders:
        console.print(
            "[red]Error:[/red] No first-level folders found in the project directory."
        )
        return

    selected_folder_name = fzf_select_project(first_level_folders)
    if not selected_folder_name:
        # console.print("[red]Error:[/red] No folder selected.")
        return

    selected_folder = os.path.join(directory, selected_folder_name)
    folders, files = get_folders_and_files(selected_folder)

    if not folders and not files:
        console.print(
            f"No files or subfolders found in the selected folder '{selected_folder}'."
        )
        return

    if folders:
        console.print("Subfolders in the selected folder:")

    if files:
        console.print("Files in the selected folder:")

    selected_item = fzf_select(folders + files)
    if not selected_item:
        console.print("[red]Error:[/red] No item selected.")
        return

    if os.path.isdir(selected_item):
        # If the selected item is a folder, show its contents
        files_in_folder = get_files_in_folder(selected_item)
        if files_in_folder:
            selected_file = fzf_select(files_in_folder)
            if selected_file:
                open_file_with_appropriate_viewer(selected_file)
            else:
                console.print("[red]Error:[/red] No file selected in the folder.")
        else:
            console.print("[red]Error:[/red] No files found in the selected folder.")
    else:
        # If the selected item is a file, directly open it
        open_file_with_appropriate_viewer(selected_item)


def get_first_level_folders(directory):
    """Get a list of first-level folders in the specified directory without '~/GoogleDrive/Projects' in the names."""
    folders = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if (
                entry.is_dir()
                and not entry.name.startswith(".")
                and entry.path != os.path.expanduser("~/GoogleDrive/Projects")
            ):
                folders.append(
                    entry.name
                )  # Append only the folder name without the path
    return folders


def get_folders_and_files(directory):
    """Get a list of folders and files in the specified directory and its subdirectories."""
    folders = []
    files = []
    for root, _, entries in os.walk(directory):
        for entry in entries:
            full_path = os.path.join(root, entry)
            if os.path.isdir(full_path) and not full_path.startswith("."):
                folders.append(full_path)
            elif os.path.isfile(full_path):
                files.append(full_path)
    return folders, files


def get_files_in_folder(folder):
    """Get a list of files in the specified folder."""
    files = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file():
                files.append(entry.path)
    return files


def fzf_select_project(items):
    """Use FZF to interactively select an item from the list and return the full path of the selected folder."""
    fzf_cmd = ["fzf"]
    try:
        # Run FZF command and capture the selected item
        fzf_process = subprocess.Popen(
            fzf_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,  # Redirect stdout only
            text=True,
        )
        selected_item, _ = fzf_process.communicate(input="\n".join(items))
        selected_item = selected_item.strip()
        return selected_item
    except subprocess.CalledProcessError:
        return None


def open_file_with_appropriate_viewer(file_path):
    """Open the file using the appropriate viewer based on its extension."""
    file_extension = os.path.splitext(file_path)[1]
    if file_extension == ".md":
        # Open Markdown (.md) files using nvim or your preferred text editor
        subprocess.run(["nvim", file_path])
    elif file_extension == ".pdf":
        # Open PDF files using zathura or your preferred PDF reader detached from the terminal
        subprocess.Popen(["zathura", file_path], start_new_session=True)
    else:
        console.print("[red]Error:[/red] Unsupported file type.")


if __name__ == "__main__":
    notes()
