# tino

Provisionally named work in progress.

## Goal

Replicate a website source directory, generating complete HTML files from various base and partial files, including item templates populated with content file head data and body text, and saving to an output directory.

## Done

- recursive insertion of:
  - partials into HTML files using the `<== partial.html [n]` syntax, for an arbitrarily deep partials tree
  - content file values into static .page templates using the `<== key` syntax, for an arbitrarily deep content tree
  - content file values into partials .item templates using the `<== key` syntax, for an arbitrarily deep content tree, excl. href value and for ordering by date descending only
- generation of paginated content lists based on .list templates, excl. links
- static file save to default output directory, for an arbitrarily deep static tree

## Todo

- implement href and related insertions for templates
- extend to support tags
- add Markdown parsing
- upgrade to live serving
- memo updated filenames
- refactor

## Organisation

Default source directory structure:

- static/, for base HTML files marked with the locations at which partials and content head data or body text is to be inserted
- content/, for content files containing head data and body text, organised as an arbitrarily deep tree by type, e.g. blog/, docs/, initially for files written in Markdown
- partials/, for HTML files to be inserted into other HTML files, including other partial files

### Templates

Available template types:

- `.page` - a static directory template representing a complete page in a content category, e.g. a blog post, with one page generated per content file in the category
- `.item` - a partial directory template representing a component on a page, e.g. a summary of a blog post, with a maximum of one item generated per content file, up to the number requested
- `.list` - a static directory template representing one page of a paginated list containing with one `.item` template for each content file in a content category, e.g. a list of all blog posts

Specifically:

- any HTML file in static/ with a name of the form type.page.html is a template to be populated with values from the content subdirectory of that type, e.g. blog.news.item.html from files in content/blog/news/; one output file is to be generated per file in the subdirectory, each named for the source content file, e.g. content/blog/news/post1.md becoming blog/news/post1.html
- any HTML file in partials/ with a name of the form type.item.description.html is a template to be populated with values from the content subdirectory of that type, e.g. blog.news.item.li.html from files in content/blog/news/, before being inserted one or more times, e.g. to provide a list in which each `li` element summarises one content item
- any HTML file in static/ with a name of the form type.list.html is a template to be completed with the content of one `.item` file in partials/, each `.item` generated once per file in the content subdirectory of that type, e.g. blog.news.list.html relates to files in content/blog/news/; one output file is to be generated per page of the paginated list, each currently named `page-` plus the page number, e.g. content/blog/news/page-1.html for the first

## Requirements

The following dependencies are used:

- Python 3

The tino root directory requires the three default source directories - content/, partials/ and static/.

## Generation

Default inclusion syntax:

- in all HTML files: `<== partial.html [n]`, i.e. insert partial.html here, once or n times
- in HTML `.page` and `.item` templates: `<== key`, i.e. insert the given value from the content file here, using the key `body` for content file body text

For example:

```html
<ul>
  <== blog.news.item.li.html 5
</ul>
```

Once complete, all files in the static/ directory are copied into the default output directory dist/.

## CLI commands

The main file can be run for the default behaviour with the command `python3 tino.py`.

### Development

A development server listening at `localhost:8000` can be run with the command `python3 tino.py server`.
