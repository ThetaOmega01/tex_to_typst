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
    # - LaTeX math delimiters: \[, \], $$
    # - LaTeX environments: \begin{...}
    # - Common math structures: ^{...}, _{...}, ^x, _x
    patterns = [
        r"\\[a-zA-Z]+",  # \command (e.g., \frac, \alpha)
        r"\\\[",  # \[ (start of display math) - matches literal '\['
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


def convert_latex_to_typst(latex_input):
    """
    Converts a LaTeX string to Typst using Pandoc.
    Returns the Typst string or None if conversion fails.
    """
    try:
        pandoc_command = ["pandoc", "-f", "latex", "-t", "typst"]
        process = subprocess.Popen(
            pandoc_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        typst_output, error_output = process.communicate(input=latex_input)

        if process.returncode != 0:
            print("\n[Pandoc Error] Conversion failed.")
            print(
                f"Pandoc stderr:\n{error_output if error_output.strip() else '[No stderr]'}"
            )
            return None

        return typst_output

    except FileNotFoundError:
        print("[Error] Pandoc command not found.")
        print("Please ensure Pandoc is installed and added to your system's PATH.")
        raise SystemExit("Pandoc not found. Exiting.")
    except Exception as e:
        print(f"[Error] An unexpected error occurred during Pandoc conversion: {e}")
        return None


def main():
    print("Smart Auto Mathpix LaTeX to Typst Converter is RUNNING...")
    print(f"Monitoring clipboard every {POLL_INTERVAL_SECONDS} seconds.")
    print("Will only process content recognized as LaTeX.")
    print("Press Ctrl+C to stop the script.")
    print("-" * 60)

    last_clipboard_content = ""
    try:
        # Initialize with current clipboard content to avoid processing it on first run
        last_clipboard_content = pyperclip.paste()
    except pyperclip.PyperclipException as e:
        print(f"[Warning] Could not read initial clipboard content: {e}")
        print("         Make sure you have a clipboard manager installed.")

    while True:
        try:
            current_clipboard_content = pyperclip.paste()

            # Process only if clipboard has new, non-empty content
            if (
                current_clipboard_content
                and current_clipboard_content != last_clipboard_content
            ):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\nNew clipboard content detected at {timestamp}:")

                # Display a snippet for brevity
                snippet = (
                    (current_clipboard_content[:70] + "...")
                    if len(current_clipboard_content) > 70
                    else current_clipboard_content
                )
                print(
                    f"   '{snippet.replace(chr(10), ' ')}'"
                )  # Replace newlines for compact display

                if is_likely_latex(current_clipboard_content):
                    print("   Recognized as likely LaTeX. Processing...")
                    latex_input = current_clipboard_content

                    typst_output = convert_latex_to_typst(latex_input)

                    if typst_output is not None:
                        try:
                            pyperclip.copy(typst_output)
                            print("   Typst output copied to clipboard.")
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
                                f"   [Warning] Could not copy Typst to clipboard: {e}"
                            )
                            # If copy fails, keep last_clipboard_content as current_clipboard_content
                            # to avoid repeatedly trying to process the same LaTeX input if it's stuck.
                            last_clipboard_content = current_clipboard_content
                    else:
                        # Pandoc conversion failed, error already printed by convert_latex_to_typst
                        # Update last_clipboard_content to avoid re-processing faulty LaTeX
                        last_clipboard_content = current_clipboard_content
                else:
                    print("   Not recognized as LaTeX. Skipping conversion.")
                    last_clipboard_content = current_clipboard_content  # Update to prevent re-evaluating non-LaTeX

            # If clipboard content changed (e.g., cleared, or became something already processed/skipped)
            # but no action was taken above, ensure last_clipboard_content is up-to-date.
            elif current_clipboard_content != last_clipboard_content:
                last_clipboard_content = current_clipboard_content

            time.sleep(POLL_INTERVAL_SECONDS)

        except pyperclip.PyperclipException as e:
            print(f"\n[Clipboard Error] Could not access the clipboard: {e}")
            print("Make sure you have a clipboard manager installed.")
            print(f"Retrying in {POLL_INTERVAL_SECONDS * 5} seconds...")
            time.sleep(POLL_INTERVAL_SECONDS * 5)
        except KeyboardInterrupt:
            print("\n\nScript stopped by user.")
            break
        except Exception as e:
            print(f"\n[Unexpected Error] An error occurred: {e}")
            print(f"Retrying in {POLL_INTERVAL_SECONDS * 2} seconds...")
            time.sleep(POLL_INTERVAL_SECONDS * 2)


if __name__ == "__main__":
    main()
