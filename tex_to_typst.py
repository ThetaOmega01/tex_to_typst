import pyperclip
import subprocess
import time
import re

POLL_INTERVAL_SECONDS = 0.5  # How often to check the clipboard (in seconds)


def is_likely_latex(text):
    """
    Checks if the given text is likely LaTeX using common patterns.
    This is a heuristic and not a full LaTeX validator.
    """
    if not text or not isinstance(text, str):
        return False

    # Try to match common LaTeX patterns:
    # - \command (e.g., \frac, \alpha)
    # - LaTeX math delimiters: \[, \], $$m etc.
    # - LaTeX environments: \begin{...}
    # - Common math structures: ^{...}, _{...}, ^x, _x,
    patterns = [
        r"\\[a-zA-Z]+",  # \command (e.g., \frac, \alpha)
        r"\\\[",  # \[ (start of display math) - matches literal '\['
        r"\\\(",  # \( (start of inline math) - matches literal '\('
        r"\$\$",  # $$ (alternative display math)
        r"\\begin\{[a-zA-Z*]+\}",  # \begin{environment}
        r"\^\{",  # ^{ (superscript with braces)
        r"\_\{",  # _{ (subscript with braces)
        r"\^\S",  # ^. (superscript with a single non-space char, e.g., x^2, x^*)
        r"\_\S",  # _. (subscript with a single non-space char, e.g., x_1, x_i)
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def has_math_delimiters(text):
    """
    Checks if the text already has LaTeX math delimiters.
    Returns True if delimiters are found, False otherwise.
    """
    if not text:
        return False
    
    # Check for common math delimiters
    delimiter_patterns = [
        r"\$.*\$",           # Inline math: $...$
        r"\$\$.*\$\$",       # Display math: $$...$$
        r"\\\[.*\\\]",       # Display math: \[...\]
        r"\\\(.*\\\)",       # Inline math: \(...\)
        r"\\begin\{(equation|align|gather|eqnarray|displaymath|math)\}",  # Math environments
    ]
    
    for pattern in delimiter_patterns:
        if re.search(pattern, text, re.DOTALL):
            return True
    
    return False


def preprocess_latex_input(latex_input):
    """
    Preprocesses LaTeX input to ensure proper math delimiters for Pandoc conversion.
    If the input contains LaTeX math commands but no delimiters, wraps it in $$ delimiters.
    Returns a tuple: (processed_input, is_raw_math_flag)
    """
    if not latex_input or not isinstance(latex_input, str):
        return latex_input, False
    
    # If it already has math delimiters, return as-is
    if has_math_delimiters(latex_input):
        return latex_input, False
    
    # Check if it contains LaTeX math commands but no delimiters
    math_command_patterns = [
        r"\\(frac|sqrt|sum|int|prod|lim|sin|cos|tan|log|ln|exp|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|phi|omega|infty|partial|nabla|cdot|times|div|pm|mp infty|leq|geq|neq|approx|equiv|propto|subset|supset|in|notin|cup|cap|forall|exists|mathbb|mathcal|mathrm|operatorname)\b",  # Common math commands
        r"\^\{",             # Superscript with braces
        r"\_\{",             # Subscript with braces
        r"\^\S",             # Superscript with single char
        r"\_\S",             # Subscript with single char
    ]
    
    contains_math_commands = any(re.search(pattern, latex_input) for pattern in math_command_patterns)
    
    # If it contains math commands but no delimiters, wrap in display math
    if contains_math_commands:
        return f"$${latex_input}$$", True  # Return flag indicating we added delimiters
    
    # Otherwise, return as-is
    return latex_input, False


def post_process_typst_output(typst_text, is_raw_math=False):
    """   
    Pandoc converts () and [] to \\(\\) and \\[\\] to eliminate ambiguity,
    but regular parentheses work fine.
    If is_raw_math is True, also removes outer $ delimiters since they were added
    by our preprocessing for raw LaTeX input.
    """
    if not typst_text:
        return typst_text

    processed_text = typst_text

    # Replace \( and \) with ( and )
    processed_text = re.sub(r"\\(\()", r"(", processed_text)
    processed_text = re.sub(r"\\(\))", r")", processed_text)

    # Replace \[ and \] with [ and ]
    processed_text = re.sub(r"\\(\[)", r"[", processed_text)
    processed_text = re.sub(r"\\(\])", r"]", processed_text)

    # If this was raw LaTeX input, remove the outer $ delimiters that Pandoc added
    if is_raw_math:
        # Remove outer $ delimiters (both inline $ $ and display $$ $$)
        processed_text = processed_text.strip()
        if processed_text.startswith('$') and processed_text.endswith('$'):
            # Handle both $ $ and $$ $$ cases
            if processed_text.startswith('$$') and processed_text.endswith('$$'):
                processed_text = processed_text[2:-2].strip()
            else:
                processed_text = processed_text[1:-1].strip()

    return processed_text


def convert_latex_to_typst(latex_input):
    """
    Converts a LaTeX string to Typst using Pandoc.
    Returns the Typst string or None if conversion fails.
    """
    try:
        # Preprocess the input to ensure proper math delimiters
        processed_input, is_raw_latex = preprocess_latex_input(latex_input)
        
        pandoc_command = ["pandoc", "-f", "latex", "-t", "typst"]
        process = subprocess.Popen(
            pandoc_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        typst_output, error_output = process.communicate(input=processed_input)

        if process.returncode != 0:
            print("\n[Pandoc Error] Conversion failed.")
            print(
                f"Pandoc stderr:\n{error_output if error_output.strip() else '[No stderr]'}"
            )
            return None

        # Post-process with the raw LaTeX flag
        return post_process_typst_output(typst_output, is_raw_latex)

    except FileNotFoundError:
        print("[Error] Pandoc command not found.")
        print("Please ensure Pandoc is installed and added to your system's PATH.")
        raise SystemExit("Pandoc not found. Exiting.")
    except Exception as e:
        print(f"[Error] An unexpected error occurred during Pandoc conversion: {e}")
        return None


def main():
    print("  Smart Auto Mathpix LaTeX to Typst Converter is RUNNING...")
    print(f"  Monitoring clipboard every {POLL_INTERVAL_SECONDS} seconds.")
    print("  Will only process content recognized as LaTeX.")
    print("  Press Ctrl+C to stop the script.")
    print("  " + "-" * 56)

    last_clipboard_content = ""
    try:
        # Initialize with current clipboard content to avoid processing it on first run
        last_clipboard_content = pyperclip.paste()
    except pyperclip.PyperclipException as e:
        print(f"  [Warning] Could not read initial clipboard content: {e}")
        print("           Make sure you have a clipboard manager installed.")

    while True:
        try:
            current_clipboard_content = pyperclip.paste()

            # Process only if clipboard has new, non-empty content
            if (
                current_clipboard_content
                and current_clipboard_content != last_clipboard_content
            ):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n  New clipboard content detected at {timestamp}:")

                # Display a snippet for brevity
                snippet = (
                    (current_clipboard_content[:70] + "...")
                    if len(current_clipboard_content) > 70
                    else current_clipboard_content
                )
                print(
                    f"    '{snippet.replace(chr(10), ' ')}'"
                )  # Replace newlines for compact display

                if is_likely_latex(current_clipboard_content):
                    print("    Recognized as likely LaTeX. Processing...")
                    latex_input = current_clipboard_content

                    typst_output = convert_latex_to_typst(latex_input)

                    if typst_output is not None:
                        # Post-process the Typst output to clean up escaped characters
                        # Should it cause issues, comment this line out.
                        typst_output = post_process_typst_output(typst_output)
                        try:
                            pyperclip.copy(typst_output)
                            print("    Typst output copied to clipboard.")
                            typst_snippet = (
                                (typst_output[:150] + "...")
                                if len(typst_output) > 150
                                else typst_output
                            )
                            print(
                                f"      --- Typst Snippet ---\n      {typst_snippet.replace(chr(10), ' ').strip()}\n      ---------------------"
                            )
                            last_clipboard_content = typst_output  # Update with our output to prevent re-processing
                        except pyperclip.PyperclipException as e:
                            print(
                                f"    [Warning] Could not copy Typst to clipboard: {e}"
                            )
                            # If copy fails, keep last_clipboard_content as current_clipboard_content
                            # to avoid repeatedly trying to process the same LaTeX input if it's stuck.
                            last_clipboard_content = current_clipboard_content
                    else:
                        # Pandoc conversion failed, error already printed by convert_latex_to_typst
                        # Update last_clipboard_content to avoid re-processing faulty LaTeX
                        last_clipboard_content = current_clipboard_content
                else:
                    print("    Not recognized as LaTeX. Skipping conversion.")
                    last_clipboard_content = current_clipboard_content  # Update to prevent re-evaluating non-LaTeX

            # If clipboard content changed (e.g., cleared, or became something already processed/skipped)
            # but no action was taken above, ensure last_clipboard_content is up-to-date.
            elif current_clipboard_content != last_clipboard_content:
                last_clipboard_content = current_clipboard_content

            time.sleep(POLL_INTERVAL_SECONDS)

        except pyperclip.PyperclipException as e:
            print(f"\n  [Clipboard Error] Could not access the clipboard: {e}")
            print("  Make sure you have a clipboard manager installed.")
            print(f"  Retrying in {POLL_INTERVAL_SECONDS * 5} seconds...")
            time.sleep(POLL_INTERVAL_SECONDS * 5)
        except KeyboardInterrupt:
            print("\n\n  Script stopped by user.")
            break
        except Exception as e:
            print(f"\n  [Unexpected Error] An error occurred: {e}")
            print(f"  Retrying in {POLL_INTERVAL_SECONDS * 2} seconds...")
            time.sleep(POLL_INTERVAL_SECONDS * 2)


if __name__ == "__main__":
    main()
