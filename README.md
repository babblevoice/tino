# tino

Provisionally named work in progress.

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
