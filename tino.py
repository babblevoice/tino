# include global dependencies

# - standard library
from sys import argv
from os import system, listdir, mkdir, path
from copy import deepcopy

# - external library
#

# configure project
tag = '<=='
out = 'dist'

# handle arguments
if 'server' in argv:
  print(f'View site at localhost:8000 | Press Ctrl+C here to stop')
  system(f'python3 -m http.server -d {out}')

# define utilities

def get_source_file(path):
  with open(path, 'r') as f:
    return f.readlines()

def get_source_path(root, *parts):
  rel_path_raw = '/'.join(parts) if root in ['', '.'] else root + '/' + '/'.join(parts)
  rel_path = rel_path_raw if '/' != rel_path_raw[-1] else rel_path_raw[0:-1]
  return rel_path

def check_file_type(ext):
  return lambda filename: ext == filename.split('.')[-1]

check_file_html = check_file_type('html')
check_file_md   = check_file_type('md')

def check_file_role(infix, index = -2): # default index value for .page and .list; -3 for .item
  def check(filename):
    filename_parts = filename.split('.')
    return len(filename_parts) > 2 and infix == filename.split('.')[index]
  return check

check_file_page = check_file_role('page')
check_file_item = check_file_role('item', -3)
check_file_list = check_file_role('list')

def get_subpath(p, stop = -2): # default stop value for .page and .list; -3 for .item
  filename = p.split('/')[-1]
  filename_parts = filename.split('.')
  return '/'.join(filename_parts[0:stop])

def read_by_path(d, p):
  path_parts = p.split('/')
  if 1 == len(path_parts):
    return d[path_parts[0]]
  return read_by_path(d[path_parts[0]], '/'.join(path_parts[1:]))

def write_by_path(d, p, value):
  path_parts = p.split('/')
  if 1 == len(path_parts):
    d[path_parts[0]] = value
    return d
  if path_parts[0] not in d: d[path_parts[0]] = {}
  d[path_parts[0]] = write_by_path(d[path_parts[0]], '/'.join(path_parts[1:]), value)
  return d

def delete_by_path(d, p):
  path_parts = p.split('/')
  if 1 == len(path_parts):
    del d[path_parts[0]]
    return
  delete_by_path(d[path_parts[0]], '/'.join(path_parts[1:]))

def get_with_indent(line, size):
  return ' ' * size + line

def ensure_out_dir(subdir = None):
  out_path = out if subdir is None else out + '/' + subdir
  if not path.exists(out_path):
    mkdir(out_path)

def output_lines(filename, content):
  with open(out + '/' + filename, 'w') as f:
    f.write(content)

def prime_workflow(*functions):
  '''Returns function returning result of data passed to functions chained'''
  def flow(data = None):
    for function in functions:
      data = function(data) if data is not None else function()
    return data
  return flow

# define processors

def get_page_path(content_path):
  content_path_parts = content_path.split('/')
  page_subpath = '/'.join(content_path_parts[1:-1])
  page_filename = '.'.join([*content_path_parts[-1].split('.')[0:-1], 'html'])
  return '/'.join([page_subpath, page_filename])

def format_content(content_path, tree_src):

  pairs = {}
  lines_body = []
  is_meta = False

  tree_src_lvl = read_by_path(tree_src, content_path)

  for line in tree_src_lvl:
    line_stripped = line.strip()
    if '' == line_stripped: continue
    if '---' == line_stripped:
      if not is_meta: is_meta = True; continue
      is_meta = False; continue
    if is_meta:
      [key_raw, value_raw] = line.split(':')
      pairs[key_raw.strip()] = value_raw.strip().replace('"', '')
    else:
      lines_body.append(line)

  pairs['body'] = ''.join(lines_body)
  pairs['href'] = get_page_path(content_path)
  tree_src = write_by_path(tree_src, content_path, pairs)
  return tree_src

def get_tag_values(line):
  [indent_raw, args_raw] = line.split(tag)
  indent = len(indent_raw)
  args = args_raw.strip().split(' ')
  source = args[0]
  number = 1 if 1 == len(args) else int(args[1]) if 'all' != args[1] else None
  return (indent, source, number)

def populate_lines(base_lines, content_file, content_path):
  lines = []
  for base_line in base_lines:
    if tag not in base_line: lines.append(base_line); continue
    (indent, source, number) = get_tag_values(base_line)
    if source not in list(content_file.keys()): raise KeyError(f'No {source} for {content_path}')
    source_value = content_file[source] if '\n' == content_file[source][-1] else content_file[source] + '\n'
    lines.append(get_with_indent(source_value, indent))
  return lines

def generate_items(base_lines, content_dir, source, number = None, offset = 0):
  subpath = get_subpath(source, -3)
  content_items = list(read_by_path(content_dir, subpath).items()) # returns list of str-dict tuples
  content_files = list(filter(lambda item: check_file_md(item[0]), content_items))
  content_files_sorted = sorted(content_files, key = lambda file: file[1]['date'], reverse = True)
  content_files_subset = content_files_sorted[offset:offset + number]
  lines = []
  for content_file in content_files_subset:
    lines.extend(populate_lines(base_lines, content_file[1], content_file[0]))
  return lines

def complete_base_lines(base_lines_path, tree_src):

  base_lines = read_by_path(tree_src, base_lines_path)
  lines = []

  for base_line in base_lines:

    if tag not in base_line: lines.append(base_line); continue
    (indent, source, number) = get_tag_values(base_line)

    if 'html' != source.split('.')[-1] or (check_file_list(base_lines_path.split('/')[-1]) and\
      check_file_item(source.split('/')[-1])): # handling .list with .item in generate_list
      lines.append(base_line)
      continue

    partials_file = read_by_path(tree_src['partials'], source)
    if not partials_file: raise KeyError(f'No partial for {source}')

    tree_src = complete_base_lines(get_source_path('partials', source), tree_src) # recurse

    base_lines_complete = read_by_path(tree_src['partials'], source)
    base_lines_multiplied = generate_items(base_lines_complete, tree_src['content'], source, number)\
      if check_file_item(source.split('/')[-1]) else base_lines_complete * number

    lines.extend([get_with_indent(line, indent) for line in base_lines_multiplied])

  tree_src = write_by_path(tree_src, base_lines_path, lines)
  return tree_src

def generate_pages(page_base_path, tree_src):

  page_subpath = get_subpath(page_base_path)
  tree_src_lvl = read_by_path(tree_src['content'], page_subpath)

  for page_content_name in tree_src_lvl:

    if check_file_md(page_content_name):

      page_base_lines = read_by_path(tree_src, page_base_path)
      page_content_path = get_source_path(page_subpath, page_content_name)
      page_content = read_by_path(tree_src['content'], page_content_path)

      page_lines = populate_lines(page_base_lines, page_content, page_content_path)
      page_path = tree_src_lvl[page_content_name]['href']
      tree_src = write_by_path(tree_src, 'static/' + page_path, page_lines)

  delete_by_path(tree_src, page_base_path)
  return tree_src

def generate_list(list_base_path, tree_src):

  list_subpath = get_subpath(list_base_path)
  tree_src_lvl = read_by_path(tree_src['content'], list_subpath)

  list_base_lines = read_by_path(tree_src, list_base_path)
  lines = []
  tag_line_index = 0
  tag_line = ''

  for base_line, i in zip(list_base_lines, range(len(list_base_lines))):
    if tag not in base_line: lines.append(base_line); continue
    tag_line_index = i
    tag_line = base_line

  (indent, source, number) = get_tag_values(tag_line) # number taken as number per list page

  partials_file = read_by_path(tree_src['partials'], source)
  if not partials_file: raise KeyError(f'No partial for {source}')

  content_filenames = list(filter(lambda key: check_file_md(key), list(tree_src_lvl.keys())))
  list_pages_required = len(content_filenames) // number + 1
  list_page_names = [f'page-{str(n + 1)}.html' for n in range(list_pages_required)]

  partial_lines = read_by_path(tree_src['partials'], source)

  for i in range(len(list_page_names)):

    offset = i * number
    list_page_items = generate_items(partial_lines, tree_src['content'], source, number, offset)

    list_page_lines = [*lines[0:tag_line_index], *[get_with_indent(line, indent) for line in list_page_items], *lines[tag_line_index:]]
    list_page_path = get_source_path('static', list_subpath, list_page_names[i])
    tree_src = write_by_path(tree_src, list_page_path, list_page_lines)

  delete_by_path(tree_src, list_base_path)
  return tree_src

# define key tasks

def get_source_tree(dirs = ['partials', 'content', 'static'], root = '.'):
  tree_src = {}
  for item_name in dirs:
    item_path = get_source_path(root, item_name)
    if path.isdir(item_path):
      tree_src[item_name] = get_source_tree(listdir(item_path), item_path) # recurse
      continue
    tree_src[item_name] = get_source_file(item_path)
  return tree_src

def prepare_content(tree_src, root = 'content'):
  tree_src_lvl = read_by_path(tree_src, root)
  for item_name in tree_src_lvl:
    item_path = get_source_path(root, item_name)
    if dict == type(tree_src_lvl[item_name]):
      tree_src = prepare_content(tree_src, item_path) # recurse
      continue
    if check_file_md(item_name):
      tree_src = format_content(item_path, tree_src)
  return tree_src

def insert_partials(tree_src, root = '.'):
  tree_src_lvl = tree_src if '.' == root else read_by_path(tree_src, get_source_path(root))
  for item_name in tree_src_lvl:
    item_path = get_source_path(root, item_name)
    if dict == type(tree_src_lvl[item_name]) and not check_file_md(item_name):
      tree_src = insert_partials(tree_src, item_path) # recurse
      continue
    if check_file_html(item_name):
      tree_src = complete_base_lines(item_path, tree_src)
  return tree_src

def include_content(tree_src, root = '.'):
  tree_src_copy = deepcopy(tree_src) # allow for dict size change on iteration
  tree_src_lvl = tree_src_copy if '.' == root else read_by_path(tree_src_copy, get_source_path(root))
  for item_name in tree_src_lvl:
    item_path = get_source_path(root, item_name)
    if dict == type(tree_src_lvl[item_name]) and not check_file_md(item_name):
      tree_src = include_content(tree_src, item_path) # recurse
      continue
    if check_file_page(item_name):
      tree_src = generate_pages(item_path, tree_src)
    if check_file_list(item_name):
      tree_src = generate_list(item_path, tree_src)
  return tree_src

def output_static(tree_src, root = 'static'):
  if 'static' == root: ensure_out_dir()
  tree_src_lvl = read_by_path(tree_src, root)
  for item_name in tree_src_lvl:
    item_path = '/'.join([*root.split('/')[1:], item_name])
    if dict == type(tree_src_lvl[item_name]) and not check_file_md(item_name):
      ensure_out_dir(item_path)
      output_static(tree_src, get_source_path(root, item_name)) # recurse
      continue
    content = ''.join(tree_src_lvl[item_name])
    output_lines(item_path, content)

# init

generate_site = prime_workflow(
  get_source_tree,
  prepare_content,
  insert_partials,
  include_content,
  output_static
)()
