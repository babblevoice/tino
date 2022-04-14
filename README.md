# tino

Provisionally named work in progress.

## Goal

Generate complete HTML files from base and partial files and content file head data and body text and save to an output directory.

Proposed default source directory structure:

- static/, for base HTML files marked with the locations at which partials and content head data or body text is to be inserted
- content/, for content files containing head data and body text, organised in subdirectories by type, e.g. blog, docs, initially for files written in Markdown
- partials/, for HTML files to be inserted into other HTML files, including other partial files

In addition:

- any HTML file in static/ with a name of the form type.item.html is a template to be populated with values from the content subdirectory of that type, e.g. blog.item.html from files in content/blog/; one output file is to be generated per file in the subdirectory, each named for the source content file, e.g. content/blog/post1.md becoming post1.html
- any HTML file in partials/ with a name of the form type.item.description.html is a template to be populated with values from the content subdirectory of that type, e.g. blog.item.li.html from files in content/blog/, before being inserted one or more times, e.g. to provide a list in which each `li` element summarises one content item

Proposed default insertion syntax:

- in all HTML files: `<== partial.html`, i.e. insert partial.html here
  - an optional extended format for populating components: `<== partial.html [content_subdirname [n]]`, i.e. insert partial.html here once or n times per file in the named content subdirectory, populated by the preferred file values per the `<== key` syntax
- in HTML item templates, e.g. type.item.html: `<== key`, i.e. insert the given value from the content file here, using the key `body` for content file body text

## Done

- recursive insertion of partials using the `<== partial.html` syntax, for flat partials/
- static file save to default output directory, for flat static/

## Todo

- implement use of content files
- add Markdown parsing
- upgrade to live serving
- support source directory nesting
- memo updated filenames

## Requirements

The following dependencies are used:

- Python 3

The tino root directory requires the three default source directories - content/, partials/ and static/.

## Generation

Each of the three default directories can contain HTML files into which content from the partials/ directory is to be inserted. The point of insertion is marked on a clear line with the default tag `<==`, followed by the name of the relevant file in the partials/ directory.

For example:

```html
<ul>
  <== li.html
</ul>
```

Once complete, all files in the static/ directory are copied into the default output directory dist/.

## CLI commands

The main file can be run for the default behaviour with the command `python3 tino.py`.

### Development

A development server listening at `localhost:8000` can be run with the command `python3 tino.py server`.
