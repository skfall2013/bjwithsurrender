import os


def header(text):
    # Intentional asymmetrical spacing due to displayed output
    return f"\n ♦️♦️♦️{text} ♦️♦️♦️ \n"


def clear(): 
    """Clear the terminal screen (operating system dependent)."""
    # Windows 
    if os.name == 'nt':
        os.system('cls') 
    # Mac/Linux 
    else: 
        os.system('clear')


def money_format(money):
    """Format a monetary value as a string."""
    return "${:0,.2f}".format(money).replace('$-', '-$')


def pct_format(percent):
    """Format a percent value as a string."""
    return "{0:+.2f}%".format(percent)


def zero_division_pct(numerator, denominator):
    """Get a percentage value through division, handling zero division errors."""
    try:
        return numerator / denominator * 100.0
    except ZeroDivisionError:
        return 0.0
