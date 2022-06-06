# include global dependencies

# - standard library
from sys import argv, exit
from os import system, listdir, mkdir, path, sep, kill
from re import sub
from functools import reduce
from operator import itemgetter
from copy import deepcopy
#   - for server option
from subprocess import Popen, signal
from time import sleep, time
from traceback import print_exc

# - external library
from markdown import markdown
from css_html_js_minify import process_single_css_file #, process_single_js_file

# set default values

# - build
tag_flow = '<==' # inserts a partial or a content file value, e.g. '<== partial.html [n]' or '<== key'
tag_path = '==>' # provides the URL parts required to reach the root directory, e.g. '==>path/to/file'

pre_attr = 'data-'
name_out = 'public'

# - serve
server_loop_secs = 3


# handle CLI options

exclude_content =    True if '--exclude-content'    in argv else False
exclude_lists_main = True if '--exclude-lists-main' in argv else False
is_beta =            True if '--beta'               in argv else False

# define additional available key-value pair handlers

# - in base files using .item templates
pairs_base = {
  'total':      lambda total, used: str(total),
  'total-attr': lambda total, used: get_data_attr('type-total', str(total)),
  'extra':      lambda total, used: '0' if used >= total else str(total - used),
  'extra-attr': lambda total, used: get_data_attr('type-extra', '0' if used >= total else str(total - used))
}

# - in .list templates
pairs_list = {
  'this-list':       lambda s, names, i: sep.join(s.split(sep)[1:]).replace(sep, f' {sep} ').upper() if sep in s else s.upper(),
  'first-url':       lambda s, names, i: names[0],
  'prev-extra':      lambda s, names, i: '0' if i - 2 < 0 else str(0 + i - 1),
  'prev-extra-attr': lambda s, names, i: get_data_attr('page-prev-extra', '0' if i - 2 < 0 else str(0 + i - 1)),
  'prev-url':        lambda s, names, i: '' if i - 1 < 0 else names[i - 1],
  'prev-n':          lambda s, names, i: '' if i - 1 < 0 else str(i),
  'this-url':        lambda s, names, i: names[i],
  'this-n':          lambda s, names, i: str(i + 1),
  'next-url':        lambda s, names, i: '' if i + 1 >= len(names) else names[i + 1],
  'next-n':          lambda s, names, i: '' if i + 1 >= len(names) else str(i + 2),
  'next-extra':      lambda s, names, i: '0' if i + 2 >= len(names) else str(len(names) - i - 2),
  'next-extra-attr': lambda s, names, i: get_data_attr('page-next-extra', '0' if i + 2 >= len(names) else str(len(names) - i - 2)),
  'last-url':        lambda s, names, i: names[-1]
}

# - in .item templates inserted with 'tags'
pairs_item_tag = {
  'tag-url':  lambda subpath, tag: f'==>{sep.join([subpath, url_part_prepare(tag), ""])}',
  'tag-name': lambda subpath, tag: tag
}

# define utilities

def get_source_file(path):
  with open(path, 'r') as f:
    return f.readlines()

def get_source_path(root, *parts):
  return path.join(root if '.' != root[0] else root.lstrip('.'), *parts)

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

def get_template_subpath(p, stop = -2): # default stop value for .page and .list; -3 for .item
  filename = p.split(sep)[-1]
  filename_parts = filename.split('.')
  return sep.join(filename_parts[0:stop])

def read_by_path(d, p):
  path_parts = p.split(sep)
  if 1 == len(path_parts):
    return d[path_parts[0]]
  return read_by_path(d[path_parts[0]], sep.join(path_parts[1:]))

def read_by_path_incl_tags(d, p):
  path_parts = p.split(sep)
  # final path part assumed to be content file tag value
  if 1 == len(path_parts) and path_parts[0] not in list(d.keys()):
    return (dict(list(filter(lambda item: 'tags' in item[1] and path_parts[0] in list(map(lambda tag: tag.lower().replace(' ', '_').replace(sep, '_'), item[1]['tags'])), d.items()))), path_parts[0])
  # final path part assumed to be directory
  if 1 == len(path_parts):
    return (d[path_parts[0]], None)
  return read_by_path_incl_tags(d[path_parts[0]], sep.join(path_parts[1:])) # recurses

def write_by_path(d, p, value):
  path_parts = p.split(sep)
  if 1 == len(path_parts):
    d[path_parts[0]] = value
    return d
  if path_parts[0] not in d: d[path_parts[0]] = {}
  d[path_parts[0]] = write_by_path(d[path_parts[0]], sep.join(path_parts[1:]), value)
  return d

def delete_by_path(d, p):
  path_parts = p.split(sep)
  if 1 == len(path_parts):
    del d[path_parts[0]]
    return
  delete_by_path(d[path_parts[0]], sep.join(path_parts[1:]))

def get_data_attr(stem, value):
  return f'{pre_attr}{stem}="{value}"'

def get_with_indent(line, size):
  return line if '' == line.strip() else ' ' * size + line

def url_part_prepare(string):
  return sub(r'[^a-zA-Z0-9]', '-', string.lower())

def get_depth_part(subpath):
  return sep.join(['..'] * len(subpath.split(sep)))

def get_for_output(line, subpath):
  return line.replace(tag_path, get_depth_part(subpath))

def handle_mkdir(path):
  try:
    mkdir(path)
  except FileExistsError:
    pass

def ensure_out_dir(subdir = None):
  name_out_local = name_out
  if is_beta:
    name_out_local = name_out_local + sep + 'beta'
    handle_mkdir(name_out)
  out_path = name_out_local if subdir is None else get_source_path(name_out_local, subdir)
  if not path.exists(out_path):
    handle_mkdir(out_path)

def get_output_url_values(path, to_save = False):
  path_parts = path.split(sep)
  path_bare = sep.join(path_parts[:-1])
  filename_parts = path_parts[-1].split('.')
  basename = '.'.join(filename_parts[:-1])
  ext = filename_parts[-1]
  is_feature = 'index' != basename and -1 == basename.find('page-') and ext not in ['css', 'js']
  if not is_feature:
    return (is_feature, path_bare, path)
  path_bare_new = sep.join([path_bare, basename]) if path_bare else basename
  path_full_new = sep.join([path_bare_new, 'index.html']) if to_save else path_bare_new + sep
  return (is_feature, path_bare_new, path_full_new)

def output_lines(path, content):
  name_out_local = name_out
  (is_feature, path_bare, path_full) = get_output_url_values(path, True)
  if is_beta:
    name_out_local = name_out_local + sep + 'beta'
    handle_mkdir(name_out)
  if is_feature:
    handle_mkdir(name_out_local + sep + path_bare)
  source_path = get_source_path(name_out_local, path_full)
  with open(source_path, 'w') as f:
    f.write(content)
  if 'css' == path_full.split('.')[-1]:
    process_single_css_file(source_path, overwrite=True)
#  # js minification not verified locally
#  if 'js' == path_full.split('.')[-1]:
#    process_single_js_file(source_path, overwrite=True)

def prime_workflow(*functions):
  '''Returns function returning result of data passed to functions chained'''
  def flow(data = None):
    for function in functions:
      data = function(data) if data is not None else function()
    return data
  return flow


# define processors

def get_page_path(content_path):
  content_path_parts = content_path.split(sep)
  page_subpath = sep.join(content_path_parts[1:-1])
  page_filename = '.'.join([*content_path_parts[-1].split('.')[0:-1], 'html'])
  return get_output_url_values(sep.join([page_subpath, page_filename]))[2]

def extract_img_src(markdown_str):
  start = markdown_str.index('(') + 1
  end = markdown_str.rindex(')')
  return markdown_str[start:end]

def remove_a_hrefs(html_str):
  return sub(r' href=".*"', '', html_str)

def get_tags_as_list(tags_string):
  tags_string_content = raw = tags_string.replace('[', '').replace(']', '')
  tags_raw = tags_string_content.split(',') if len(tags_string_content) > 0 else []
  return list(map(lambda tag_raw: tag_raw.replace('"', '').strip(), tags_raw)) # remove string delimiters

def add_weight_to_dict(weights_dict, key, value_string):
  value = None if not value_string else int(value_string)
  if 'weight' == key:
    weights_dict['others'] = value
  else:
    weights_dict[key[7:].replace(sep, '_')] = value
  return weights_dict

def extract_content(acc, line):
  line_stripped = line.strip()
  # handle head section
  # - head delimiters
  if '---' == line_stripped:
    if not acc['in_head']: acc['in_head'] = True; return acc
    acc['in_head'] = False; return acc
  # - key-value pairs
  if acc['in_head']:
    # handle blank line
    if '' == line_stripped: return acc
    # set key and value
    line_parts_raw = line.split(':')
    line_parts = [line_parts_raw[0], ':'.join(line_parts_raw[1:])]
    [key, value] = list(map(lambda part: part.strip(), line_parts))
    # handle specifics
    if 'tags' == key: acc['pairs']['tags'] = get_tags_as_list(value); return acc
    if 'weight' == key[0:6]: acc['pairs']['weights'] = add_weight_to_dict(acc['pairs']['weights'], key, value); return acc
    # handle remainder
    acc['pairs'][key] = value.replace('"', '') # remove string delimiters
  # handle body section
  else:
    if not acc['pairs']['image'] and '![' == line_stripped[0:2] and ')' == line_stripped[-1]:
      acc['pairs']['image'] = extract_img_src(line_stripped)
    if not acc['pairs']['intro'] and len(line_stripped) > 0 and line_stripped[0] not in ['#', '!']:
      acc['pairs']['intro'] = remove_a_hrefs(markdown(line))
    acc['lines_body'].append(line)
  return acc

def format_content(content_path, tree_src):
  cache_in = {
    'in_head': False,
    'lines_body': [],
    'pairs': {
      'weights': {},
      'image': '',
      'intro': ''
    }
  }
  content_file = read_by_path(tree_src, content_path)
  cache_out = reduce(extract_content, content_file, cache_in)
  lines_body, pairs = itemgetter('lines_body', 'pairs')(cache_out)

  pairs['body'] = list(map(lambda line: line + '\n', markdown(''.join(lines_body), extensions=['tables', 'fenced_code', 'attr_list']).split('\n'))) # 'tables' for tables using - and |, 'fenced_code' for code blocks using ```, 'attr_list' for links using #-prefixed heading
  pairs['url'] = get_page_path(content_path)
  tree_src = write_by_path(tree_src, content_path, pairs)
  return tree_src

def get_tag_values(line):
  [indent_raw, args_raw] = line.split(tag_flow)
  indent = len(indent_raw)
  args = args_raw.strip().split(' ')
  source = args[0]
  number = 1 if 1 == len(args) else int(args[1]) if args[1] not in ['all', 'tags'] else 'tags' if 'tags' == args[1] else None
  return (indent, source, number)

def generate_tag0_list(content_file, indent, source, tree_src):
  tag0 = content_file['tags'][0] if 'tags' in content_file and len(content_file['tags']) > 0 else None
  subpath_raw, source_filename = source.split(':')
  subpath = subpath_raw.replace('.', sep)
  content_files = read_by_path_incl_tags(tree_src['content'], subpath.replace('tag0', tag0.replace(' ', '_').replace(sep, '_').lower()) if tag0 is not None else '')[0]
  lines = []
  for content_file in content_files.items():
    lines.extend(populate_lines(read_by_path(tree_src['partials'], source_filename), content_file[1]))
  lines = list(map(lambda line: get_with_indent(line, indent), lines))
  return ''.join(lines)

def generate_tags(content_file, indent, source, tree_src):
  lines = []
  subpath = source.split(".")[0]
  tags = content_file['tags']
  for tag in tags:
    tag_item_pairs_i = (dict((k, v(subpath, tag)) for k, v in pairs_item_tag.items()))
    lines.extend(populate_lines(read_by_path(tree_src['partials'], source), tag_item_pairs_i))
  lines = list(map(lambda line: get_with_indent(line, indent), lines))
  return ''.join(lines)

def group_by_has_weight(tag):
  def group(acc, file):
    if tag in file[1]['weights']:
      acc[0].append(file)
    else:
      acc[1].append(file)
    return acc
  return group

def sort_content_files(content_files, tag):
  content_files_sorted = sorted(content_files, key = lambda file: file[1]['date'], reverse = True)
  if tag:
    weighted, unweighted = reduce(group_by_has_weight(tag.lower()), content_files_sorted, ([], []))
    weighted_sorted = sorted(weighted, key = lambda file: file[1]['weights'][tag.lower()])
    content_files_sorted = [*weighted_sorted, *unweighted]
  return content_files_sorted

def populate_lines(base_lines, content_file, tree_src = {}): # tree_src required for use of tags content value
  lines = []
  for base_line in base_lines:
    if tag_flow not in base_line: lines.append(base_line); continue
    (indent, source, number) = get_tag_values(base_line)
    if '.tag0:' in source: lines.append(generate_tag0_list(content_file, indent, source, tree_src)); continue
    if 'tags' == number and 'tags' in content_file: lines.append(generate_tags(content_file, indent, source, tree_src)); continue
    if source not in list(content_file.keys()): lines.append(base_line); continue #raise KeyError(f'No {source} for {content_path}')
    source_value = content_file[source]
    if 'url' == source: source_value = sep.join([tag_path, source_value])
    if 'photo' == source: source_value = tag_path + source_value
    if list == type(source_value): lines.extend(list(map(lambda line: get_with_indent(line, indent), source_value))); continue
    source_line = source_value if source_value and '\n' == source_value[-1] else source_value + '\n' if source_value else ''
    if source_line: lines.append(get_with_indent(source_line, indent))
  return lines

def generate_items(base_lines, content_files, number = None, offset = 0):
  content_files_batch = content_files[offset:offset + number]
  lines = []
  for content_file in content_files_batch:
    lines.extend(populate_lines(base_lines, content_file[1]))
  return lines

# workflow: complete_base_line

# utilities

def update_to_use_base_line(cache):
  cache['lines'].append(cache['line']['content'])
  cache['line']['is_done'] = True
  return cache

def generate_template_pairs(cache, subpath, total, used):
  new_dict = (dict((subpath.replace(sep, '.') + '.' + k, v(total, used)) for k, v in pairs_base.items()))
  cache['pairs_temp'] = {**cache['pairs_temp'], **new_dict}
  return cache

# primaries

def parse_tag_if_used_else_use_base(cache):
  if tag_flow not in cache['line']['content'] or cache['line']['is_item']: # relevant only for list generation where one .item sought
    return update_to_use_base_line(cache)
  (indent, source, number) = get_tag_values(cache['line']['content'])
  cache['line']['tag_values'] = {'indent': indent, 'source': source, 'number': number}
  return cache

def if_tag_src_is_not_html_use_base(cache):
  if cache['line']['is_done']:
    return cache
  if 'html' != cache['line']['tag_values']['source'].split('.')[-1]\
    or ('tags' == cache['line']['tag_values']['number']): # and check_file_page(cache['file_path'])): # is .page template
    return update_to_use_base_line(cache)
  return cache

def if_lines_are_item_list_use_base(cache):
  if cache['line']['is_done']:
    return cache
  lines_path_end = cache['file_path'].split(sep)[-1]
  tag_source_end = cache['line']['tag_values']['source'].split(sep)[-1]
  cache['line']['source_is_item'] = check_file_item(tag_source_end)
  if check_file_list(lines_path_end) and cache['line']['source_is_item']:
    return update_to_use_base_line(cache)
  return cache

def if_tag_src_is_generic_item_note(cache):
  if cache['line']['is_done']:
    return cache
  # remove content type prefix from source if indicates generic .item template
  source = cache['line']['tag_values']['source']
  cache['line']['tag_values']['source_filename'] = source if 1 == len(source.split(':')) else source.split(':')[1]
  return cache

def if_generic_item_for_tag0_use_base(cache):
  if cache['line']['is_done']:
    return cache
  source, source_filename = itemgetter('source', 'source_filename')(cache['line']['tag_values'])
  if source_filename != source and 'tag0' in source.split(':')[0].split('.'):
    return update_to_use_base_line(cache)
  return cache

def confirm_partial_file_else_throw(cache):
  if cache['line']['is_done']:
    return cache
  partials_file = read_by_path(cache['tree_src']['partials'], cache['line']['tag_values']['source_filename'])
  if not partials_file:
    raise KeyError(f'No partial for {cache["line"]["tag_values"]["source"]}')
  return cache

def recurse_for_any_nested_partials(cache):
  if cache['line']['is_done']:
    return cache
  tree_src = cache['tree_src']
  cache['tree_src'] = complete_base(get_source_path('partials', cache['line']['tag_values']['source_filename']), tree_src)
  return cache

def retrieve_toplevel_partial(cache):
  if cache['line']['is_done']:
    return cache
  cache['lines_partial'] = read_by_path(cache['tree_src']['partials'], cache['line']['tag_values']['source_filename'])
  return cache

def identify_content_subpath(cache):
  if cache['line']['is_done']:
    return cache
  source, source_filename = itemgetter('source', 'source_filename')(cache['line']['tag_values'])
  subpath = get_template_subpath(source, -3) if source == source_filename else source.split(':')[0].replace('.', sep) # use full path if generic .item
  cache['subpath'] = subpath
  return cache

def get_content_file_subset(cache):
  if cache['line']['is_done']:
    return cache
  path_read = read_by_path_incl_tags(cache['tree_src']['content'], cache['subpath']) if not exclude_content and cache['subpath'] else ({}, None) # returns list of str-dict tuples
  content_items = list(path_read[0].items())
  tag = path_read[1]
  content_files = list(filter(lambda item: check_file_md(item[0]), content_items))
  content_files_sorted = sort_content_files(content_files, tag if tag else None if not 'tag' in cache or cache['tag'] is None else cache['tag'].replace(' ', '_').replace(sep, '_'))
  cache['content_files'] = list(filter(lambda item: 'tags' in item[1] and cache['tag'] in item[1]['tags'], content_files_sorted)) if cache['tag'] else content_files_sorted
  return cache

def generate_items_else_multiply(cache):
  if cache['line']['is_done']:
    return cache
  tree_src, lines_partial, line = itemgetter('tree_src', 'lines_partial', 'line')(cache)
  source, number = itemgetter('source', 'number')(line['tag_values'])
  cache['lines_partial'] = generate_items(lines_partial, cache['content_files'], number)\
      if not exclude_content and line['source_is_item'] else lines_partial * number
  return cache

def set_pairs_if_tag_src_is_item(cache):
  if cache['line']['is_done']:
    return cache
  tree_src, line = itemgetter('tree_src', 'line')(cache)
  if line['source_is_item']:
    source, number = itemgetter('source', 'number')(line['tag_values'])
    subpath = cache['subpath']
    if '' == subpath: # source indicates use of generic .item template, i.e. prefix identifies subpath
      subpath = source.split(':')[0].replace('.', sep)
    path_read = read_by_path_incl_tags(tree_src['content'], subpath) if not exclude_content else ({}, None)
    content_filenames = list(filter(lambda key: '_' != key[0], path_read[0].keys())) # remove any '_tag_set'
    total = len(list(filter(lambda item: check_file_md(item), content_filenames)))
    cache = generate_template_pairs(cache, subpath, total, number)
  return cache

def extend_lines(cache):
  if cache['line']['is_done']:
    return cache
  lines_partial, line = itemgetter('lines_partial', 'line')(cache)
  cache['lines'].extend([get_with_indent(line_plus, line['tag_values']['indent']) for line_plus in lines_partial])
  return cache

complete_base_line = prime_workflow(
  # accepts and returns cache dict
  parse_tag_if_used_else_use_base,
  if_tag_src_is_not_html_use_base,
  if_lines_are_item_list_use_base, # handling .list w/ .item in generate_list
  if_tag_src_is_generic_item_note,
  if_generic_item_for_tag0_use_base,
  confirm_partial_file_else_throw,
  recurse_for_any_nested_partials,
  retrieve_toplevel_partial,
  identify_content_subpath,
  get_content_file_subset,
  generate_items_else_multiply,
  set_pairs_if_tag_src_is_item,
  extend_lines
)

# workflow: complete_base_file

def complete_base_lines(cache):
  base_lines = itemgetter('base_lines')(cache)
  for base_line in base_lines:
    cache['line']['content'] = base_line
    cache['line']['is_done'] = False
    cache = complete_base_line(cache) # workflow, recurses
  return cache

def populate_with_values_if_list(cache):
  pairs_temp = cache['pairs_temp']
  if len(list(pairs_temp.items())) > 0:
    file_path, lines = itemgetter('file_path', 'lines')(cache)
    cache['lines'] = populate_lines(lines, pairs_temp)
  return cache

def replace_any_path_tag_if_page(cache):
  file_path, lines = itemgetter('file_path', 'lines')(cache)
  # replace any path tag in a .page template with URL parts sufficient to reach project root
  is_page = check_file_page(file_path.split(sep)[-1])
  if is_page:
    subpath = get_template_subpath(file_path, -2) if is_page else ''
    cache['lines'] = list(map(lambda line: get_for_output(line, sep.join(['..', subpath])), lines))
  return cache

complete_base_file = prime_workflow(
  # accepts and returns cache dict
  complete_base_lines, # calls workflow complete_base_line
  populate_with_values_if_list,
  replace_any_path_tag_if_page
)

def get_cache(tree_src, base_lines_path, base_lines, tag = None):
  return {
    'tree_src': tree_src,
    'file_path': base_lines_path,
    'base_lines': base_lines,
    'pairs_temp': {},
    'lines': [],
    'line': {
      'is_done': False,
      'is_item': False # relevant only for list generation where one .item is sought
    },
    'tag': tag # relevant only for list generation where list is list for tag
  }

def complete_base(base_lines_path, tree_src):

  base_lines = read_by_path(tree_src, base_lines_path)

  cache_new = get_cache(tree_src, base_lines_path, base_lines)
  cache_out = complete_base_file(cache_new) # workflow, recurses
  tree_src, lines = itemgetter('tree_src', 'lines')(cache_out)

  tree_src = write_by_path(tree_src, base_lines_path, lines)
  return tree_src

def generate_pages(page_base_path, tree_src):

  page_subpath = get_template_subpath(page_base_path)
  tree_src_lvl = read_by_path(tree_src['content'], page_subpath)

  for page_content_name in tree_src_lvl:
    if check_file_md(page_content_name):

      page_base_lines = read_by_path(tree_src, page_base_path)
      page_content_path = get_source_path(page_subpath, page_content_name)
      page_content = read_by_path(tree_src['content'], page_content_path)

      page_lines = populate_lines(page_base_lines, page_content, tree_src)
      page_path = tree_src_lvl[page_content_name]['url']
      tree_src = write_by_path(tree_src, get_source_path('static', page_path), page_lines)

  delete_by_path(tree_src, page_base_path)
  return tree_src

# workflow: generate_list_line

def if_tag_src_is_item_note_i_else_use_base(cache):
  if cache['line']['is_done']:
    return cache
  list_pair_keys = pairs_list.keys()
  tag_values, index = itemgetter('tag_values', 'index')(cache['line'])
  if tag_values['source'] in list_pair_keys:
    return update_to_use_base_line(cache)
  # source assumed to be .item forming list - note index
  cache['line']['tag_values'] = {'index': index, **tag_values}
  cache['line']['is_item'] = True
  return cache

generate_list_line = prime_workflow(
  # accepts and returns cache dict
  parse_tag_if_used_else_use_base,
  if_tag_src_is_item_note_i_else_use_base,
  if_tag_src_is_generic_item_note,
  confirm_partial_file_else_throw
)

# workflow: generate_list_file

def identify_listed_content(cache):
  subpath = get_template_subpath(cache['file_path'])
  cache['subpath'] = subpath
  cache['tree_src_lvl'] = read_by_path(cache['tree_src']['content'], subpath)
  return cache

def extract_item_tag_values(cache):
  base_lines = itemgetter('base_lines')(cache)
  for base_line, i in zip(base_lines, range(len(base_lines))):
    cache['line']['content'] = base_line
    cache['line']['index'] = i
    cache['line']['is_done'] = False
    cache = generate_list_line(cache) # workflow
  cache['line']['is_done'] = False # reset to prevent skipping by line-oriented functions in pipe
  return cache

def generate_list_page_names(cache):
  content_filenames = list(filter(lambda item: check_file_md(item[0]), cache['content_files']))
  list_pages_required = len(content_filenames) // cache['line']['tag_values']['number'] + 1
  list_page_names = ['index.html']
  list_page_names.extend([f'page-{str(n + 2)}.html' for n in range(list_pages_required - 1)])
  cache['list_page_names'] = list_page_names
  return cache

generate_list_file = prime_workflow(
  # accepts and returns cache dict
  identify_listed_content,
  extract_item_tag_values, # calls workflow generate_list_line
  get_content_file_subset,
  generate_list_page_names,
  retrieve_toplevel_partial
)

def generate_list(list_base_path, tree_src, tag = None):

  list_base_lines = read_by_path(tree_src, list_base_path)

  cache_new = get_cache(tree_src, list_base_path, list_base_lines, tag)
  cache_out = generate_list_file(cache_new) # workflow #, recurses

  subpath, list_page_names, lines, lines_partial, line = itemgetter('subpath', 'list_page_names', 'lines', 'lines_partial', 'line')(cache_out)
  index, indent, number = itemgetter('index', 'indent', 'number')(line['tag_values']) # number taken as number per list page

  # add subpath part if list for tag
  subpath = subpath + sep + url_part_prepare(tag) if tag else subpath

  for i in range(len(list_page_names)):

    offset = i * number
    list_page_items = generate_items(lines_partial, cache_out['content_files'], number, offset)

    list_page_lines = [*lines[0:index], *[get_with_indent(line, indent) for line in list_page_items], *lines[index:]]

    list_page_pairs_i = (dict((k, v(tag if tag else subpath, list_page_names, i)) for k, v in pairs_list.items()))
    list_page_lines = populate_lines(list_page_lines, list_page_pairs_i)

    list_page_path = get_source_path('static', subpath, list_page_names[i])
    tree_src = write_by_path(tree_src, list_page_path, list_page_lines)

  return tree_src

def generate_lists(list_base_path, tree_src):

  list_subpath = get_template_subpath(list_base_path)
  tree_src_lvl = read_by_path(tree_src['content'], list_subpath)

  if '_tag_set' in tree_src_lvl:
    tag_set = tree_src_lvl['_tag_set']
    for tag in tag_set:
      tree_src = generate_list(list_base_path, tree_src, tag)

  if not exclude_lists_main: tree_src = generate_list(list_base_path, tree_src)
  delete_by_path(tree_src, list_base_path)
  return tree_src

def init_output_dir():
  name_out_local = name_out
  if is_beta:
    name_out_local = name_out + sep + 'beta'
  ensure_out_dir()
  if path.exists('static/assets'):
    ensure_out_dir('assets')
    system(f'cp -r static/assets/* {name_out_local}/assets/')
  if not exclude_content and path.exists('content/images'):
    ensure_out_dir('images')
    system(f'cp -r content/images/* {name_out_local}/images/') #ln -s content/images/* {name_out}/images/')

# workflow: finalise_content

def add_beta_url_part(lines):
  # TODO: reduce duplication
  if is_beta:
    lines_updated = []
    for line in lines:
      tag_path_i = line.find(tag_path)
      if -1 != tag_path_i:
        url_char_1_i = tag_path_i + 3
        if sep == line[url_char_1_i]:
          line = line.replace(tag_path + sep, tag_path + sep + 'beta' + sep)
          lines_updated.append(line)
          continue
      else:
        href_i = line.find('href="')
        if -1 != href_i:
          url_char_1_i = href_i + 6
          if sep == line[url_char_1_i]:
            if '/api' == line[url_char_1_i:url_char_1_i + 4] or '/files' == line[url_char_1_i:url_char_1_i + 6]:
              lines_updated.append(line); continue
            line = line.replace('href="' + sep, 'href="' + sep + 'beta' + sep)
            lines_updated.append(line)
            continue
        else:
          src_i = line.find('src="')
          if -1 != src_i:
            url_char_1_i = src_i + 5
            if sep == line[url_char_1_i]:
              if '/api' == line[url_char_1_i:url_char_1_i + 4] or '/files' == line[url_char_1_i:url_char_1_i + 6]:
                lines_updated.append(line); continue
              line = line.replace('src="' + sep, 'src="' + sep + 'beta' + sep)
              lines_updated.append(line)
              continue
      lines_updated.append(line)
    return lines_updated
  return lines

def remove_path_tags(lines):
  return list(map(lambda line: line.replace(tag_path, ''), lines))

def join_lines(lines):
  return ''.join(lines)

finalise_content = prime_workflow(
  # accepts and returns lines list
  add_beta_url_part,
  remove_path_tags,
  join_lines
)


# define key tasks

# workflow: generate_site

def get_source_tree(dirs = ['partials', 'content', 'static'], root = '.'):

  tree_src = {}

  for item_name in dirs:

    # handle items skipped
    if 'content' == item_name and exclude_content: continue
    if item_name in ['assets', 'images']: continue
    if '.' == item_name[0]: continue

    item_path = get_source_path(root, item_name)
    # handle item absence
    if not path.exists(item_path):
      if 'content' == item_path:
        tree_src['content'] = {}
      continue
    # handle item nesting
    if path.isdir(item_path):
      tree_src[item_name] = get_source_tree(listdir(item_path), item_path) # recurse
      continue

    tree_src[item_name] = get_source_file(item_path)

  return tree_src

def prepare_content(tree_src, root = 'content'):

  # handle items skipped
  if exclude_content: return tree_src

  tree_src_lvl = read_by_path(tree_src, root)
  tag_set = set([])

  for item_name in tree_src_lvl:

    item_path = get_source_path(root, item_name)
    # handle item nesting
    if dict == type(tree_src_lvl[item_name]):
      tree_src = prepare_content(tree_src, item_path) # recurse
      continue
    # handle content file
    if check_file_md(item_name):
      tree_src = format_content(item_path, tree_src)
    if 'tags' in tree_src_lvl[item_name]:
      tag_set.update(tree_src_lvl[item_name]['tags'])

  tree_src = write_by_path(tree_src, root + '/_tag_set', tag_set)
  return tree_src

def insert_partials(tree_src, root = '.'):
  tree_src_lvl = tree_src if '.' == root else read_by_path(tree_src, get_source_path(root))
  for item_name in tree_src_lvl:
    item_path = get_source_path(root, item_name)
    if dict == type(tree_src_lvl[item_name]) and not check_file_md(item_name):
      tree_src = insert_partials(tree_src, item_path) # recurse
      continue
    if check_file_html(item_name):
      tree_src = complete_base(item_path, tree_src)
  return tree_src

def include_content(tree_src, root = '.'):
  if exclude_content: return tree_src
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
      tree_src = generate_lists(item_path, tree_src)
  return tree_src

def output_static(tree_src, root = 'static'):
  if 'static' == root: init_output_dir()
  tree_src_lvl = read_by_path(tree_src, root)
  for item_name in tree_src_lvl:
    item_path = sep.join([*root.split(sep)[1:], item_name])
    if dict == type(tree_src_lvl[item_name]) and not check_file_md(item_name):
      ensure_out_dir(item_path)
      output_static(tree_src, get_source_path(root, item_name)) # recurse
      continue
    content = finalise_content(tree_src_lvl[item_name])
    output_lines(item_path, content)

generate_site = prime_workflow(
  get_source_tree,
  prepare_content,
  insert_partials,
  include_content,
  output_static
)

def check_source_updated(time_secs_current, dirs = ['partials', 'content', 'static'], root = '.'):
  for item_name in dirs:
    if 'content' == item_name and exclude_content: continue
    if item_name in ['assets', 'images']: continue
    if '.' == item_name[0]: continue
    item_path = get_source_path(root, item_name)
    if not path.exists(item_path):
      continue
    if path.isdir(item_path):
      if check_source_updated(time_secs_current, listdir(item_path), item_path): # recurse
        return True
      continue
    item_secs_modified = int(str(path.getmtime(item_path)).split('.')[0])
    if time_secs_current - item_secs_modified < server_loop_secs:
      return True
  return False


# init

generate_site()

if not 'server' in argv:
  exit()

print(f'View site at localhost:8000 | Press Ctrl+C here to stop')
pid = None
try:
  server_loop_secs = float(server_loop_secs + server_loop_secs / 10)
  pid = Popen(['python3', '-m', 'http.server', '-d', name_out]).pid
  while True:
    sleep(server_loop_secs)
    time_secs_current = int(str(time()).split('.')[0])
    if check_source_updated(time_secs_current):
      print(f'Source modified - updating {name_out}/')
      generate_site()
except KeyboardInterrupt:
  exit()
except Exception:
  print_exc()
  kill(pid, signal.SIGKILL)
  exit()
