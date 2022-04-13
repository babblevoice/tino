# include global dependencies

# - standard library
from sys import argv
from os import system, listdir, mkdir, path

# - external library
#

# configure project
tag = '<=='
src = ['partials', 'content', 'static']
out = 'dist'

# handle arguments
if 'server' in argv:
  print(f'View site at localhost:8000 | Press Ctrl+C here to stop')
  system(f'python3 -m http.server -d {out}')

# define utilities

def load_lines_f(path):
  with open(path, 'r') as f:
    return f.readlines()

def confirm_html(filename):
  return 'html' == filename.split('.')[-1]

def get_indented(line, size):
  return ' ' * size + line

def ensure_out_d():
  if not path.exists(out):
    mkdir(out)

def save_lines_f(filename, content):
  with open(out + '/' + filename, 'w') as f:
    f.write(content)

# define handlers

def get_inclusion_data(line):
  [indent, source] = line.split(tag)
  return (len(indent), source.strip())

def update_lines_f(dirname, filename, lines_s):
  lines_f_updated = []
  for line in lines_s[dirname][filename]:
    if tag not in line: lines_f_updated.append(line); continue
    (indent_size, source) = get_inclusion_data(line)
    if source not in lines_s['partials']: lines_f_updated.append(line); continue
    lines_s_updated = update_lines_f('partials', source, lines_s) #recurse
    lines_f_updated.extend([get_indented(line, indent_size) for line in lines_s_updated['partials'][source]])
  lines_s[dirname][filename] = lines_f_updated
  return lines_s

# define key tasks

def load_lines_s(src):
  lines_s = {}
  for dirname in src:
    lines_s[dirname] = {}
    filenames = listdir('./' + dirname)
    for filename in filenames:
      lines_s[dirname][filename] = load_lines_f(dirname + '/' + filename)
  return lines_s

def update_lines_s(lines_s):
  for dirname in lines_s:
    for filename in lines_s[dirname]:
      if confirm_html(filename):
        lines_s = update_lines_f(dirname, filename, lines_s)
  return lines_s

def output_static(lines_s):
  ensure_out_d()
  for filename in lines_s['static']:
    content = ''.join(lines_s['static'][filename])
    #print(filename + ':\n' + content)
    save_lines_f(filename, content)

# init (no pipe)
output_static(
  update_lines_s(
    load_lines_s(src)
  )
)
