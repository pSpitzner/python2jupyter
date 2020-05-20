"""
This module translates .py files to .ipynb and vice versa
"""
import os
import sys
import json
import argparse

# Path to directory
HERE = os.path.abspath(os.path.dirname(__file__))

TRIPLE_QUOTES = ["\"\"\"", "\'\'\'"]
FOUR_SPACES = "{:<4}".format("")
EIGHT_SPACES = "{:<8}".format("")
TWELVE_SPACES = "{:<12}".format("")

# do we want to parse single line `#` comments as md?
NO_ONE_LINE_COMMENTS = True

# whether to undindent block comments so they are parsed with markdown
UNINDENT_BLOCK_COMMENTS = True

# optionall, place a google colab badge in the beginning
ADD_GOOGLE_COLAB_BADGE = True

def p2j(source_filename, target_filename, overwrite):
    """Convert Python scripts to Jupyter notebooks.

    Args:
        source_filename (str): Path to Python script.
        target_filename (str): Path to name of Jupyter notebook. Optional.
        overwrite (bool): Whether to overwrite an existing Jupyter notebook.
    """

    target_filename = _check_files(
        source_filename, target_filename, overwrite, conversion="p2j")

    # Check if source file exists and read
    try:
        with open(source_filename, 'r') as infile:
            data = [l.rstrip('\n') for l in infile]
    except FileNotFoundError:
        print("Source file not found. Specify a valid source file.")
        sys.exit(1)

    # Read JSON files for .ipynb template
    with open(HERE + '/templates/cell_code.json') as file:
        CODE = json.load(file)
    with open(HERE + '/templates/cell_markdown.json') as file:
        MARKDOWN = json.load(file)
    with open(HERE + '/templates/metadata.json') as file:
        MISC = json.load(file)

    # Initialise variables
    final = {}              # the dictionary/json of the final notebook
    cells = []              # an array of all markdown and code cells
    arr = []                # an array to store individual lines for a cell
    num_lines = len(data)   # no. of lines of code

    # Initialise variables for checks
    is_block_comment = False
    is_running_code = False
    is_running_comment = False
    next_is_code = False
    next_is_nothing = False
    next_is_function = False

    # Read source code line by line
    for i, line in enumerate(data):

        # Skip if line is empty
        if line == "":
            continue

        buffer = ""

        # Labels for current line
        contains_triple_quotes = TRIPLE_QUOTES[0] in line or TRIPLE_QUOTES[1] in line
        is_code = line.startswith("# pylint") or line.startswith("#pylint") or \
            line.startswith("#!") or line.startswith("# -*- coding") or \
            line.startswith("# coding=") or line.startswith("##") or \
            line.startswith("# FIXME") or line.startswith("#FIXME") or \
            line.startswith("# TODO") or line.startswith("#TODO") or \
            line.startswith("# This Python file uses the following encoding:") or \
            NO_ONE_LINE_COMMENTS
        is_end_of_code = i == num_lines-1
        starts_with_hash = line.startswith("#")

        # Labels for next line
        try:
            next_is_code = not data[i+1].startswith("#")
        except IndexError:
            pass
        try:
            next_is_nothing = data[i+1] == ""
        except IndexError:
            pass
        try:
            next_is_function = data[i+1].startswith(FOUR_SPACES) or (
                next_is_nothing and data[i+2].startswith(FOUR_SPACES))
        except IndexError:
            pass

        # Sub-paragraph is a comment but not a running code
        if not is_running_code and (is_running_comment or
                                    (starts_with_hash and not is_code) or
                                    contains_triple_quotes):

            if contains_triple_quotes:
                is_block_comment = not is_block_comment

            buffer = line.replace(TRIPLE_QUOTES[0], "\n").\
                replace(TRIPLE_QUOTES[1], "\n")

            if not is_block_comment:
                # remove `#` from comments
                if len(buffer) > 1:
                    buffer = buffer[2:] if buffer[1].isspace() else buffer[1:]
                else:
                    buffer = ""

            if is_block_comment and UNINDENT_BLOCK_COMMENTS:
                # this is dirty, remove first four white spaces
                if buffer[0:4] == "    ":
                    buffer = buffer[4:]


            # Wrap this sub-paragraph as a markdown cell if
            # next line is end of code OR
            # (next line is a code but not a block comment) OR
            # (next line is nothing but not a block comment)
            if is_end_of_code or (next_is_code and not is_block_comment) or \
                    (next_is_nothing and not is_block_comment):
                arr.append("{}".format(buffer))
                MARKDOWN["source"] = arr
                cells.append(dict(MARKDOWN))
                arr = []
                is_running_comment = False
            else:
                if is_block_comment and next_is_nothing:
                    buffer = buffer + "\n\n"
                else:
                    buffer = buffer + "\n"
                arr.append("{}".format(buffer))
                is_running_comment = True
                continue
        else:  # Sub-paragraph is a comment but not a running code
            buffer = line

            # Wrap this sub-paragraph as a code cell if
            # (next line is end of code OR next line is nothing) AND NOT
            # (next line is nothing AND next line is part of a function)
            if (is_end_of_code or next_is_nothing) and not (next_is_nothing and next_is_function):
                arr.append("{}".format(buffer))
                CODE["source"] = arr
                cells.append(dict(CODE))
                arr = []
                is_running_code = False
            else:
                buffer = buffer + "\n"

                # Put another newline character if in a function
                try:
                    if data[i+1] == "" and (data[i+2].startswith("    #") or
                                            data[i+2].startswith("        #") or
                                            data[i+2].startswith("            #")):
                        buffer = buffer + "\n"
                except IndexError:
                    pass

                arr.append("{}".format(buffer))
                is_running_code = True
                continue

    # add the google colab badge
    if ADD_GOOGLE_COLAB_BADGE:
        MARKDOWN["source"] = [colab_badge(target_filename)]
        # cells.append(dict(MARKDOWN))
        cells = [dict(MARKDOWN)] + cells

    # Finalise the contents of notebook
    final["cells"] = cells
    final.update(MISC)

    # Write JSON to target file
    with open(target_filename, 'w') as outfile:
        json.dump(final, outfile)
        print("Notebook written to {}".format(target_filename))


def _check_files(source_file, target_file, overwrite, conversion):
    """File path checking

    Check if
    1) Name of source file is valid.
    2) Target file already exists. If not, create.

    Does not check if source file exists. That will be done
    together when opening the file.
    """

    if conversion == "p2j":
        expected_src_file_ext = ".py"
        expected_tgt_file_ext = ".ipynb"
    else:
        expected_src_file_ext = ".ipynb"
        expected_tgt_file_ext = ".py"

    file_base = os.path.splitext(source_file)[0]
    file_ext = os.path.splitext(source_file)[-1]

    if file_ext != expected_src_file_ext:
        print("Wrong file type specified. Expected {} ".format(expected_src_file_ext) +
              "extension but got {} instead.".format(file_ext))
        sys.exit(1)

    # Check if target file is specified and exists. If not specified, create
    if target_file is None:
        target_file = file_base + expected_tgt_file_ext
    if not overwrite and os.path.isfile(target_file):
        # FileExistsError
        print("File {} exists. ".format(target_file) +
              "Add -o flag to overwrite this file, " +
              "or specify a different target filename using -t.")
        sys.exit(1)

    return target_file


def j2p(source_filename, target_filename, overwrite):
    """Convert Jupyter notebooks to Python scripts

    Args:
        source_filename (str): Path to Jupyter notebook.
        target_filename (str): Path to name of Python script. Optional.
        overwrite (bool): Whether to overwrite an existing Python script.
        with_markdown (bool, optional): Whether to include markdown. Defaults to False.
    """

    target_filename = _check_files(
        source_filename, target_filename, overwrite, conversion="j2p")

    # Check if source file exists and read
    try:
        with open(source_filename, 'r') as infile:
            myfile = json.load(infile)
    except FileNotFoundError:
        print("Source file not found. Specify a valid source file.")
        sys.exit(1)

    final = [''.join(["# " + line.lstrip() for line in cell["source"] if not line.strip() == ""])
             if cell["cell_type"] == "markdown" else ''.join(cell["source"])
             for cell in myfile['cells']]
    final = '\n\n'.join(final)
    final = final.replace("<br>", "")

    with open(target_filename, "a") as outfile:
        outfile.write(final)
        print("Python script {} written.".format(target_filename))


def _git_url(file_path):
    import subprocess as sp
    # this get's us the git base directory, need to append the filename of ipynb
    output = sp.getoutput(f'{HERE}/git_url.sh {file_path}')
    # replace prefix if cloned via ssh
    output = output.replace('git@github.com:', "https://github.com/")
    return output

def colab_badge(file_path):
    """
        take the target file path (ipynb) and add a badge for google colab
    """
    url = _git_url(file_path) + os.path.basename(file_path)
    print(f"Generating google colab badge for {url}")
    url = url.replace("https://github.com/", "https://colab.research.google.com/github/")
    badge = f"[![Open In Colab]" + \
        f"(https://colab.research.google.com/assets/colab-badge.svg)]({url})"
    return badge

def main():
    """Parse arguments and perform file checking"""

    # Get source and target filenames
    parser = argparse.ArgumentParser(
        description="Convert a Python script to Jupyter notebook and vice versa",
        usage="p2j myfile.py")
    parser.add_argument('source_filename',
                        help='Python script to parse')
    parser.add_argument('-r', '--reverse',
                        action='store_true',
                        help="To convert Jupyter to Python scripto")
    parser.add_argument('-t', '--target_filename',
                        help="Target filename of Jupyter notebook. If not specified, " +
                        "it will use the filename of the Python script and append .ipynb")
    parser.add_argument('-o', '--overwrite',
                        action='store_true',
                        help='Flag whether to overwrite existing target file. Defaults to false')
    args = parser.parse_args()

    if args.reverse:
        j2p(source_filename=args.source_filename,
            target_filename=args.target_filename,
            overwrite=args.overwrite)
    else:
        p2j(source_filename=args.source_filename,
            target_filename=args.target_filename,
            overwrite=args.overwrite)


if __name__ == "__main__":
    main()
