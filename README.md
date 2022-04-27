# tino

Provisionally named work in progress.

- [Goal](#goal)
- [Done](#done)
- [Todo](#todo)
- [Code](#code)
  - [Overview](#overview)
  - [Organisation](#organisation)
    - [Inclusion](#inclusion)
    - [Templates](#templates)
  - [Requirements](#requirements)
  - [CLI commands](#cli-commands)
  - [Notes](#notes)

## Goal

Generate a website from a set of three source directories, producing complete HTML files from content, base and partial files, including item templates populated with content file values and paginated list templates, and saving to an output directory, with no config files required.

## Done

- recursive insertion, for arbitrarily deep trees, of:
  - partials into HTML files using the `<== partial.html [n]` syntax
  - content file values into `.page` and `.item` templates using the `<== key` syntax, with Markdown to HTML conversion, currently ordering items by date descending only
- generation of paginated content lists based on `.list` templates, incl. population with pagination values
- static file save to default output directory, for an arbitrarily deep static tree
- partial live serving - file tree update on change, without page reload

## Todo

- extend to support tag equivalents, incl. list pages using a `.tags.list` template, outputting to a <tags>/ subdirectory for the content type
- extend use of path tag to other nested files
- revise remaining commands to equivalent Python method calls
- extend live serving to reload page and revise to diff
- memoise completed partial filenames
- refactor and comment

## Code

### Overview

The current code when run from a project directory (see [Organisation](#organisation) below) will replicate the structure of the static/ directory in the output directory (public/ by default), with any base HTML files which contain partial inclusion syntax (see [Inclusion](#inclusion) below) extended using the relevant partial files.

If the site is to include content categories, e.g. blog, docs, with pages populated from Markdown files, the relevant content files are placed in a content/ directory in appropriately named subdirectories, e.g. content/blog/, content/docs/, and the appropriate templates are used (see [Templates](#templates) below).

### Organisation

Default source directory structure:

- static/, for base HTML files marked with the locations at which partials and content head data or body text is to be inserted, with all images stored in static/assets/
- content/, for content files containing head data and body text, organised as an arbitrarily deep tree by type, e.g. blog/, docs/, initially for files written in Markdown, with all images stored in content/images
- partials/, for HTML files to be inserted into other HTML files, including other partial files

#### Inclusion

##### File inclusion

Default file inclusion syntax:

- in all HTML files: `<== partial.html [n]`, i.e. insert partial.html here, once or n times
- in HTML `.page` and `.item` templates: `<== key`, i.e. insert the given value from the content file here, using the key `body` for content file body text

For example:

```html
<ul>
  <== blog.news.item.li.html 5
</ul>
```

##### Path inclusion

Default path inclusion syntax for path parts to root is `==>`. For example, the attribute `href="==>assets/logo.svg"` in a `.page` template for blog/news/, i.e. for a page two levels deep, becomes in the output file `href="../../assets/logo.svg"`.

##### Content file values

Each content file has a meta section of colon-separated key-value pairs demarcated above and below by a single line reading `---`. This section is followed by the lines of body text, which can use Markdown.

For example:

```md
---
key_1: value_1
key_2: value_2
---

body
```

#### Templates

Available template types:

- `.page` - a static directory template representing a complete page in a content category, e.g. a blog post, with one page generated per content file in the category
- `.item` - a partial directory template representing a component on a page, e.g. a summary of a blog post, with a maximum of one item generated per content file, up to the number requested
- `.list` - a static directory template representing one page of a paginated list containing with one `.item` template for each content file in a content category, e.g. a list of all blog posts

Specifically:

- any HTML file in static/ with a name of the form type.page.html is a template to be populated with values from the content subdirectory of that type, e.g. blog.news.item.html from files in content/blog/news/; one output file is to be generated per file in the subdirectory, each named for the source content file, e.g. content/blog/news/post1.md becoming blog/news/post1.html
- any HTML file in partials/ with a name of the form [type.]item.description.html is a template to be populated with values from the content subdirectory of that type, if the type is present, e.g. blog.news.item.li.html from files in content/blog/news/, before being inserted one or more times, e.g. to provide a list in which each `li` element summarises one content item; if no type is present in the name, this is provided in the item inclusion syntax by prefixing the name with the type followed by a colon (':'), e.g. `<== type:item.description.html`
- any HTML file in static/ with a name of the form type.list.html is a template to be completed with the content of one `.item` file in partials/, each `.item` generated once per file in the content subdirectory of that type, e.g. blog.news.list.html relates to files in content/blog/news/; one output file is to be generated per page of the paginated list, each currently named `page-` plus the page number, e.g. content/blog/news/page-1.html for the first

##### Additional values

In addition to values provided in the meta section of the content file (see [Content file values](#content-file-values) above), the following are available for use in `.item` templates:

- `image` - the URL of the first image on its own line in the body of the content file
- `intro` - the first non-heading, non-image line of the body of the content file, converted from Markdown to HTML, with any `a` element `href` value removed
- `body` - the body of the content file, converted from Markdown to HTML
- `href` - the URL of the output file

The following values are available for use in files applying `.item` templates, excluding `.list` templates, for the purpose of populating control elements:

- `.total` - the total number of content files of the type, preceded with the dot-separated type, e.g. blog.news.available
- `.total-attr` - the total number of content files of the type as the value in an attribute named by default `data-type-total`, preceded with the dot-separated type, e.g. blog.news.total-attr
- `.extra` - the number of content files of the type not used in the file, preceded with the dot-separated type, e.g. blog.news.extra
- `.extra-attr` - the number of content files of the type not used in the file as the value in an attribute named by default `data-type-extra`, preceded with the dot-separated type, e.g. blog.news.extra-attr

The following values are available for use in `.list` templates for the purpose of populating control elements:

- `first-url` - the URL of the output file for the first list page of the set
- `last-url` - the URL of the output file for the last list page of the set
- `prev-url` - the URL of the output file for the previous list page in the set
- `this-url` - the URL of the output file for the current list page
- `next-url` - the URL of the output file for the next list page in the set
- `prev-n` - the number of the previous list page in the set
- `this-n` - the number of the current list page
- `next-n` - the number of the next list page in the set
- `prev-extra` - the number of list pages before `prev-n`
- `prev-extra-attr` - the number of list pages before `prev-n` as the value in an attribute named by default `data-page-prev-extra`
- `next-extra` - the number of list pages after `next-n`
- `next-extra-attr` - the number of list pages after `next-n` as the value in an attribute named by default `data-page-next-extra`

### Requirements

The following dependencies are used:

- Python 3
- [Python-Markdown](https://github.com/Python-Markdown/markdown)

The tino root directory requires the three default source directories - content/, partials/ and static/.

Once complete, all files in the static/ directory are copied into the default output directory public/.

### CLI commands

The main file can be run for the default behaviour with the command `python3 tino.py`.

#### Development

A development live server listening at `localhost:8000` can be run with the command `python3 tino.py server`.

##### Options

- `--exclude-content` - do not load content files and pass any templates unpopulated to the output directory

### Notes

- dot-prefixed files are not loaded

#### Pre-release

- ensure existing site section URLs valid
- ensure existing site images used also by apps remain or are relocated
