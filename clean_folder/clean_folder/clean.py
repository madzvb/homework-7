# sorter.py
"""
    Sort files by extension. Can unpack supported archives.
"""
""" Default file processing settings:
    {
        "archives"  :   {
            "extensions"    :   ["zip", "tar", "tgz", "gz", "7zip", "7z", "iso", "rar"],
            "functions"     :   ["unpack","move"]
        },
        "video"     :   {
            "extensions"    :   ["avi", "mp4", "mov", "mkv"],
            "functions"     :   ["move"]
        },
        "audio"     :   {
            "extensions"    :   ["wav", "mp3", "ogg", "amr"],
            "functions"     :   ["move"]
        },
        "documents" :   {
            "extensions"    :   ["doc", "docx", "txt", "pdf", "xls", "xlsx", "ppt", "pptx", "rtf", "xml", "ini"],
            "functions"     :   ["move"]
        },
        "images"    :   {
            "extensions"    :   ["jpeg", "png", "jpg", "svg"],
            "functions"     :   ["move"]
        },
        "software"    :   {
            "extensions"    :   ["exe", "msi", "bat" , "dll"],
            "functions"     :   ["move"]
        },
        "other"     :   {
            "extensions"    :   [],
            "functions"     :   ["move"]
        }
    }
    Supported functions:
            #   copy, move, remove, unpack, delete(used for removing archives)
            #   order sensitive

TODO: 
    add regexp to extensions processing
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import os
import sys
import shutil


args = None

def make_translate_table() -> dict:
    """Create translation table from cyrillic to latin. Also replace all other character with symbol - '_' except digits"""
    translation_table = {}
    latin = ("a", "b", "v", "g", "d", "e", "e", "j", "z", "i", "j", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u",
             "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya", "je", "i", "ji", "g")

    # Make cyrillic tuplet
    cyrillic_symbols = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяєіїґ"
    cyrillic_list = []
    for c in cyrillic_symbols:
        cyrillic_list.append(c)

    cyrillic = tuple(cyrillic_list)

    # Fill tranlation table
    for c, l in zip(cyrillic, latin):
        translation_table[ord(c)] = l
        translation_table[ord(c.upper())] = l.upper()

    # From symbol [NULL] to '/'. See ASCI table for more details.
    for i in range(0, 48):
        translation_table[i] = '_'
    # From ':' to '@'. See ASCI table for more details.
    for i in range(58, 65):
        translation_table[i] = '_'
    # From symbol '[' to '`'. See ASCI table for more details.
    for i in range(91, 97):
        translation_table[i] = '_'
    # From symbol '{' to [DEL]. See ASCI table for more details.
    for i in range(123, 128):
        translation_table[i] = '_'
    return translation_table

# name = '!@#$%^&*()абвгдеёжзийклмнопрстуфхцчшщъыьэюяєіїґ_АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯЄІЇГ_0123456789'
# normalize = make_translate_function()
# name = normalize(name)

def _make_translate_function():
    translation = make_translate_table()

    def translate(name):
        """Normalize parameter - name"""
        return name.translate(translation)
    return translate

def _make_destination(normalize, destination_root: Path, name: Path, split = True) -> Path:
    """Create destination path with normalization, if normalization if ON"""

    if split:
        file_name = name.stem
        ext_name = name.suffix
    else:
        file_name = name
        ext_name = ''
    
    if normalize:
        destination_name = normalize(file_name)
    else:
        destination_name = file_name
    
    destination_name += ext_name
    destination = Path(destination_root) / destination_name
    return destination

def _make_copy_file_function(destination_root: Path) -> Path:
    normalize = None
    if not args.use_original_names:
        normalize = _make_translate_function()

    def copy_file(name: Path) -> str:
        """Move file to destination directory"""

        if not name.exists():
            print(f"Error: Skip coping file - '{name}'. File doesn't exists.")
            return name
        
        destination = _make_destination(normalize, destination_root, name)

        if args.overwrite or not destination.exists():
            if args.verbose >= 3:
                print(f"Copy file - '{name}' to '{destination}'.")
            try:
                shutil.copy2(name, destination)
            except Exception as e:
                print(f"Error: {e}")
        else:
            if args.verbose >= 1:
                print(f"Warning: Skip coping file - '{name}' to '{destination}'. File already exists.")
        
        return destination
    
    return copy_file

def _make_move_file_function(destination_root: Path):
    normalize = None
    if not args.use_original_names:
        normalize = _make_translate_function()

    def move_file(name: Path) -> Path:
        """Move file to destination directory"""

        if not name.exists():
            print(f"Error: Skip moving file - '{name}'. File doesn't exists.")
            return name
        
        destination = _make_destination(normalize, destination_root, name)

        if args.overwrite or not destination.exists():
            if args.verbose >= 3:
                print(f"Move file - '{name}' to '{destination}'.")
            try:
                shutil.move(name, destination)
            except Exception as e:
                print(f"Error: {e}")
        else:
            if args.verbose >= 1:
                print(f"Warning: Skip moving file - '{name}' to '{destination}'. File already exists.")
        
        return destination
    
    return move_file

def _make_unpack_file_function(destination_root: Path):
    normalize = None
    if not args.use_original_names:
        normalize = _make_translate_function()

    def unpack_file(name: Path) -> Path:
        """Unpack archive to destination directory"""

        if not name.exists():
            print(f"Error: Skip unpacking file - '{name}'. File doesn't exists.")
            return name
        
        directory_name = name.stem
        destination = _make_destination(normalize, destination_root, directory_name, False)
        
        if not destination.exists():
            if args.verbose >= 3:
                print(f"Create directory - '{destination}'.")
            try:
                destination.mkdir()
            except Exception as e:
                print(f"Error: {e}")
        
        if args.overwrite or not os.listdir(destination):
            try:
                if args.verbose >= 3:
                    print(f"Unpack archive - '{name}' to '{destination}'.")
                shutil.unpack_archive(name, destination)
            except shutil.ReadError as e:
                print(f"Error: {e}")
                destination.rmdir()
            except Exception as e:
                print(f"Error: {e}")
        else:
            if args.verbose >= 1:
                print(f"Warning: Skip unpacking file - '{name}' to '{destination}'. '{destination}' already exists.")
        
        return destination
    
    return unpack_file

def _make_delete_file_function(destination_root: Path):
    normalize = None
    if not args.use_original_names:
        normalize = _make_translate_function()

    def delete_file(name: Path) -> Path:
        """Remove archive if it was unpacked successfully"""

        if not name.exists():
            print(f"Error: Skip deleting file - '{name}'. File doesn't exists.")
            return name
        
        directory_name = name.stem
        destination = _make_destination(normalize, destination_root, directory_name,False)
        
        if destination.exists():  # Check if archive was unpacked
            if args.verbose >= 3:
                print(f"Remove file - '{name}'.")
            try:
                name.unlink(True)
            except Exception as e:
                print(f"Error: {e}")
        
        return name
    
    return delete_file


def _remove_file(name: Path) -> Path:
    """Just remove file"""

    if name.exists():
        if args.verbose >= 3:
            print(f"Remove file - '{name}'.")
        try:
            name.unlink(True)
        except Exception as e:
            print(f"Error: {e}")
    else:
        if args.verbose >= 1:
            print(f"Warning: Skip removing file - '{name}'. File doesn't exists.")
    
    return name

def sort(root_dir: Path,current_dir: Path, dir2ext: dict, ext2dir: dict, result: dict) -> dict:
    dirs = []
    files = []

    # Filling files and subdirectories lists to process
    for f in os.listdir(current_dir):
        pathname = Path(current_dir) / f
        if pathname.is_dir():
            name = pathname.name
            if name in dir2ext:  # Exclude destination directories
                continue
            dirs.append(pathname)
        elif pathname.is_file():
            files.append(pathname)
        else:  # ignore all other filesystem entities
            pass

    # Process subdirectories
    if dirs:
        for sub_dir in dirs:
            if args.verbose > 0:
                print(f"Processing directory - '{sub_dir}'.")
            result = sort(root_dir,sub_dir, dir2ext, ext2dir, result)
            if not args.keep_empty_dir and sub_dir.exists() and not len(os.listdir(sub_dir)):
                if args.verbose >= 3:
                    print(f"Remove empty directory - '{sub_dir}'.")
                try:
                    sub_dir.rmdir()
                except Exception as e:
                    print(f"Error: {e}")

    # Fill result dictionary with files in current path
    files_result = {}  # Current directory's files to be processed
    for pathname in files:
        name = pathname.name
        if name == 'sorter.py':  # Exclude script
            continue
        ext = pathname.suffix.replace('.', '').lower()
        if len(ext2dir) == 1 and '*' in ext2dir:
            target_dir = ext2dir['*']
        elif not ext in ext2dir:  # All unknown extensions put to other
            target_dir = 'other'
        else:
            target_dir = ext2dir[ext]

        if not target_dir in result:
            result[target_dir] = {}
        if not target_dir in files_result:
            files_result[target_dir] = {}

        if not ext in result[target_dir]:
            result[target_dir][ext] = []
        if not ext in files_result[target_dir]:
            files_result[target_dir][ext] = []

        result[target_dir][ext].append(pathname)
        files_result[target_dir][ext].append(pathname)

    # Process files
    for dest, exts in files_result.items():
        for ext, files in exts.items():
            functions = dir2ext[dest]['functions'] if dest in  dir2ext else None
            if functions:
                dest_dir = Path(root_dir) / dest
                if not dest_dir.exists(): # Create destination directory if no exists
                    if args.verbose >= 2:
                        print(f"Create directory - '{dest_dir}'.")
                    dest_dir.mkdir()
                for function in functions: # Apply functions to files
                    for name in map(function, files):
                        continue
            else:
                print(f"Error: skip processing '{files}'. No functions to apply.")
    return result

def _parse_argmunets():
    """Parse comand-line options"""

    parser = argparse.ArgumentParser(
        description="Sort files by extension. Can unpack supported archives.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog = "Usage examples:\n\
            clean.py -v -o /usr/home/root/downloads /usr/home/root/must_be_sorted -s settings.json\n\
        or  clean.py -v -o /usr/home/root/downloads /usr/home/root/must_be_sorted -d images -e jpg bmp jpeg -f move"
    )  # ,exit_on_error=False
    parser.add_argument(
        "directories",
        help="Directories list to process, if not specified used current directory.",
        type = Path,
        action="store",
        nargs='*'
    )
    parser.add_argument(
        "-k", "--keep-empty-dir",
        help="Don't remove empty directories.",
        action="store_true",
        required=False
    )
    parser.add_argument(
        "-u", "--use-original-names",
        help="Don't normalize file and directory(for unpacking archives) names.",
        action="store_true",
        default=False,
        required=False
    )
    parser.add_argument(
        "-o", "--overwrite",
        help="Overwrite existing files and directories.",
        action="store_true",
        default=False,
        required=False
    )
    parser.add_argument(
        "-v", "--verbose",
        help = ("increase output verbosity.\n\
    0 - Only errors printout\n\
    1 - Add warnings\n\
    2 - Add destination directory creation\n\
    3 - Add all filesystem modification\n\
    4 - Add internal script structures"),
        action="count",
        default=0,
        required=False
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s", "--settings",
        help="Specify path to settings(JSON) file. Ex: settings.json",
        type = Path,
        metavar="settings.json",
        default="settings.json",
        required=False
    )
    group.add_argument(
        "-d", "--destination",
        help="Destination directory.",
        type = Path,
        metavar="destination",
        action="store",
        default=None,
        required=False
    )
    parser.add_argument(
        "-e", "--extensions",
        help="File's extensions. Ex: 'jpg jpeg png bmp'",
        metavar="extensions",
        action="store",
        default="*",
        required=False,
        nargs='*'
    )
    parser.add_argument(
        "-f", "--functions",
        help = "Functions' list(order sensitive).\n\
    A list of next functions:\n\
    copy, move, unpack, delete(check if archive already unpacked), remove.\n\
    Ex: 'unpack move' - will unpack archive file to destination directory\n\
    and move it to same path.",
        metavar="functions",
        action="store",
        default="move",
        required=False,
        nargs='*'
    )
    return parser.parse_args()

def _prepeare_dir2ext() -> dict:
    dir2ext = {}
    if args.destination:  # and args.extensions and args.functions:
        dir2ext[args.destination] = {}
        dir2ext[args.destination]['extensions'] = args.extensions
        dir2ext[args.destination]['functions'] = args.functions
    elif args.settings.exists():
        # Load settings from file
        with open(args.settings, 'r') as settings:
            dir2ext = json.load(settings)
    else:
        # Default settings
        # Supported functions:
        #   copy, move, remove, unpack, delete(used for removing archives)
        #   order sensitive
        dir2ext = {
            'archives'  :   {
                'extensions'    :   ['zip', 'tar', 'tgz', 'gz', '7zip', '7z', 'iso', 'rar'],
                'functions'     :   ['unpack', 'move']
            },

            'video'     :   {
                'extensions'    :   ['avi', 'mp4', 'mov', 'mkv'],
                'functions'     :   ['move']
            },
            'audio'     :   {
                'extensions'    :   ['wav', 'mp3', 'ogg', 'amr'],
                'functions'     :   ['move']
            },
            'documents' :   {
                'extensions'    :   ['doc', 'docx', 'txt', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'rtf', 'xml', 'ini'],
                'functions'     :   ['move']
            },
            'images'    :   {
                'extensions'    :   ['jpeg', 'png', 'jpg', 'svg'],
                'functions'     :   ['move']
            },
            'software'  :   {
                'extensions'    :   ['exe', 'msi', 'bat', 'dll'],
                'functions'     :   ['move']
            },
            'other'     :   {
                'extensions'    :   [],
                'functions'     :   ['move']
            }
        }
    return dir2ext

def main():

    global args
    args = _parse_argmunets()

    if not len(args.directories):
        # If no directories specified, use current
        path = Path().cwd()
        args.directories.append(path)

    dir2ext = _prepeare_dir2ext()

    # Generate mapping - extension to directory,
    # used to resolve desctination directory by file extension
    ext2dir = {}
    for dest_dir, extensions in dir2ext.items():
        for ext in extensions['extensions']:
            ext2dir[ext] = dest_dir

    # Replace function name with real functions
    for target_directory in args.directories:
        print(type(target_directory))
        if dir2ext: # Check for settings
            _dir2ext = deepcopy(dir2ext)
            for dest_dir, extensions in _dir2ext.items():
                # Fill dir2ext.extensions['functions']
                if 'functions' in extensions and extensions['functions']:
                    # Convert string to list of string
                    if isinstance(extensions['functions'], str):
                        function = extensions['functions']
                        extensions['functions'] = []
                        extensions['functions'].append(function)
                    functions = []
                    for function in extensions['functions']:
                        if function:
                            function = function.lower()
                            # Find closure
                            function_name = ('_make_' + function + '_file_function')
                            if function_name in globals():
                                functions.append(
                                    globals()[function_name](Path(target_directory) / dest_dir)
                                )
                            else:
                                # Find usual
                                function_name = ('_' + function + '_file')
                                if function_name in globals():
                                    functions.append(globals()[function_name])
                                else:
                                    print(f"Error: '{function}' not found.")
                    extensions['functions'] = functions

            result = {}
            if target_directory.exists():
                result = sort(target_directory,target_directory, _dir2ext, ext2dir, result)
                if args.verbose >= 4:
                    print(f"Processed dictionary for path - '{target_directory}': {result}.")
            else:
                print(f"Error: Directory - '{target_directory}' doesn't exists.")
            
        else:
            print(f"Error: no processing settings specified.")

if __name__ == '__main__':
    main()