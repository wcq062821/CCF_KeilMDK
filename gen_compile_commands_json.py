# -*- coding: utf-8 -*-
#********************************************************************************
#Copyright © 2020 Wcq
#File Name: genCCLS.py
#Author: Wcq
#Email: wcq-062821@163.com
#Created: 2020-09-07 16:10:54
#Last Update: 2025-01-24 10:22:23
#         By: Wcq
#Description:
# Usage: Call this script in any directory of the git project to generate `compile_commands.json` under the root directory of the git repository.
#********************************************************************************
import os
import re
import platform
import subprocess

keil_c51_include_dir = "E:/Keil_C51/C51/INC"
outfile = 'compile_commands.json'

def get_platform_path_type():
    return '\\\\' if platform.system() == 'Windows' else '/'

def get_dir_header_files(directory):
    file_list = []
    for entry in os.listdir(directory):
        entry_path = os.path.join(directory, entry)
        if os.path.isdir(entry_path):
            file_list.extend(get_dir_header_files(entry_path))
        elif entry.lower().endswith('.h'):
            file_list.append(os.path.abspath(entry_path))
    return file_list

def find_project_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def find_file(directory, target_file):
    for entry in os.listdir(directory):
        entry_path = os.path.join(directory, entry)
        if os.path.isdir(entry_path):
            result = find_file(entry_path, target_file)
            if result:
                return result
        elif entry.upper().endswith(target_file):
            return os.path.abspath(entry_path)
    return None

def generate_compile_commands_for_51(project_file, root_dir, outfile, path_type):
    with open(project_file, 'r') as f:
        content = f.read()
        src_files = re.findall(r'<FilePath>([\w\\/\.]+\.(?:[CcHhSsAaMm51]+))</FilePath>', content)
        include_dirs = re.findall(r'<IncludePath>([\w\\/\.;]+)</IncludePath>', content)[0].split(';')
        include_dirs = [os.path.abspath(path).replace('\\', path_type) for path in include_dirs]
        include_dirs.append(keil_c51_include_dir.replace('\\', path_type))

        with open(outfile, 'w') as outfile:
            outfile.write('[\n')
            for i, src_file in enumerate(src_files):
                if i > 0:
                    outfile.write(',\n\n')
                abs_src_path = os.path.abspath(src_file).replace('\\', path_type)
                outfile.write(' {\n')
                outfile.write(f'  "directory": "{root_dir}",\n')
                outfile.write('  "arguments": [\n')
                outfile.write('   "clang",\n')
                if abs_src_path.lower().endswith('.h'):
                    outfile.write(f'   "{abs_src_path}",\n')
                else:
                    outfile.write('   "-c",\n')
                    for include_dir in include_dirs:
                        outfile.write(f'   "-I{include_dir}",\n')
                    outfile.write(f'   "-o",\n')
                    outfile.write(f'   "-{os.path.basename(abs_src_path)}.o",\n')
                    outfile.write(f'   "{abs_src_path}",\n')
                outfile.write('  ],\n')
                outfile.write(f'  "file": "{abs_src_path}"\n')
                outfile.write(' }')
            outfile.write('\n]')
            print('Generated compile_commands.json successfully!')

def generate_compile_commands_by_depfile(dep_file, outfile, path_type='/'):
    pathList = set('')
    srcList = set('')
    with open(dep_file, 'r') as fpr, open(outfile, 'w') as fpw:
        buf = fpr.read()
        fpw.write('[\n')
        srcFile = re.findall(r'\nF \((.*?)\)\(.*?\)\((.*?)\)\n', buf, re.S)
        if srcFile:
            curDir = os.path.abspath('..')
            curDir = curDir.replace('\\', path_type)
            firstElement = True
            for eachFile in srcFile:
                arguments = eachFile[1].replace('\n\n', ' ')
                result = re.findall(r'-I(.*?) -D', arguments, re.S)
                if result:
                    include_path_strings = result[0]
                else:
                    include_path_strings = ""
                arguments = arguments.split(' ')
                argumentsTmp = []
                L = None
                for item in arguments:
                    if item.startswith('\"') and (not item.endswith('\"')):
                        L = item[1:]
                    elif item.endswith('\"') and (not item.startswith('\"')) and (L is not None):
                        L = L + " " + item[:-1]
                        argumentsTmp.append(L)
                        L = ""
                    else:
                        argumentsTmp.append(item)
                arguments = argumentsTmp

                srcPath = os.path.abspath(eachFile[0]).replace('\\', path_type)

                if firstElement is False:
                    fpw.write(',\n\n')
                fpw.write(' {\n')
                fpw.write('  "directory": "%s",\n'%curDir)
                fpw.write('  "arguments": [\n')
                fpw.write('   "clang",\n')
                header = False
                cpu = False
                for arg in arguments:
                    if header:
                        header = False
                        fpw.write('%s",\n'%os.path.abspath(arg).replace('\\', path_type))
                        continue
                    if cpu:
                        cpu = False
                        fpw.write('%s",\n'%arg)
                        continue
                    if arg.find('UVISION_VERSION') != -1:
                        continue

                    if arg.startswith('--cpu'):
                        cpu = True
                        fpw.write('   "%s='%arg)
                    elif arg.startswith('-D'):
                        fpw.write('   "-D",\n')
                        fpw.write('   "%s",\n'%arg[2:])
                    elif arg.startswith('-I'):
                        if include_path_strings:
                            include_path_items =  include_path_strings.split(' -I')
                            for include_path in include_path_items: 
                                include_path = include_path.replace('\"', '').strip()
                                abs_include_path = os.path.abspath(include_path).replace('\\', path_type)
                                if not os.path.exists(abs_include_path):
                                    abs_include_path = include_path
                                abs_include_path = abs_include_path.replace('\\', path_type)
                                fpw.write(f'   \"-I{include_path}\"\n')
                            include_path_strings = ""
                    elif (arg == '-o') or (arg == '-c') or (arg.endswith('.o')):
                        fpw.write('   "%s",\n'%arg)

                fpw.write('   "%s",\n'%srcPath)
                fpw.write('  ],\n')
                fpw.write('  "file": "%s",\n'%srcPath)
                fpw.write(' }')
                firstElement = False
            fpw.write('\n]')
            print('gen compile_commands.json finish!')

if __name__ == '__main__':
    path_type = get_platform_path_type()
    root_dir = find_project_root()
    print(f'root_dir : {root_dir}')
    if not root_dir:
        raise Exception("Project root directory not found!")
    outfile = os.path.join(root_dir, outfile)

    project_file = None
    for ext in ['.UVPROJX', '.UVPROJ']:
        project_file = find_file(root_dir, ext)
        if project_file:
            break

    if not project_file:
        raise Exception("project_file not found!")
    print(f'project_file : {project_file}')

    project_dir = os.path.dirname(project_file)
    os.chdir(project_dir)

    dep_file = find_file('.', '.DEP')
    print(f'dep_file : {dep_file}')
    if not dep_file:
        print('Dependency file not found, assuming 51 project')
        generate_compile_commands_for_51(project_file, root_dir, outfile, path_type)
    else:
        generate_compile_commands_by_depfile(dep_file, outfile, path_type)
