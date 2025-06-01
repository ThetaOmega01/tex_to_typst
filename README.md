# LaTeX to Typst Converter

Automatically converts standard LaTeX to Typst format via clipboard monitoring using Pandoc.

## Requirements

- Python 3.13+
- [Pandoc](https://pandoc.org/)
- [uv](https://docs.astral.sh/uv/)

## Installation

Install Pandoc and run:

```sh
uv sync
```

## Usage

```sh
uv run tex_to_typst.py
```

Copy LaTeX content to clipboard - it will automatically be converted to Typst and replace the current clipboard.

It can be used with common LaTeX OCR tools for image to typst workflow.