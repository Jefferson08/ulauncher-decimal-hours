import ast
import re

from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.client.Extension import Extension
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem


ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
    ast.Constant,
    ast.Num,
    ast.Load,
)


def safe_eval_expression(expression):
    tree = ast.parse(expression, mode="eval")

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError("Unsupported syntax")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed")

    return float(_eval_node(tree.body))


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed")
        return node.value

    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.USub):
            return -value
        raise ValueError("Unsupported unary operation")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right

        raise ValueError("Unsupported binary operation")

    raise ValueError("Unsupported expression")


def format_hhmm_from_minutes(total_minutes):
    sign = "-" if total_minutes < 0 else ""
    total_minutes = abs(int(total_minutes))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{sign}{hours}:{minutes:02d}"


def decimal_hours_to_hhmm(value):
    minutes = int(round(value * 60))
    return format_hhmm_from_minutes(minutes)


def parse_hm_input(value):
    text = value.strip().lower().replace(" ", "")
    if not text:
        raise ValueError("Invalid input")

    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return int(round(float(text)))

    match_colon = re.fullmatch(r"(\d+):(\d{1,2})", text)
    if match_colon:
        hours = int(match_colon.group(1))
        minutes = int(match_colon.group(2))
        if minutes >= 60:
            raise ValueError("Minutes in HH:MM must be < 60")
        return hours * 60 + minutes

    match_hm = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", text)
    if match_hm and (match_hm.group(1) is not None or match_hm.group(2) is not None):
        hours = int(match_hm.group(1) or 0)
        minutes = int(match_hm.group(2) or 0)
        return hours * 60 + minutes

    raise ValueError("Invalid input")


def build_invalid_format_item():
    help_text = "Use: hd 1.5 | hd 1.5+2.25 | hm 1:30 | hm 1h20m | hm 90m"
    return ExtensionResultItem(
        icon="images/icon.png",
        name="Formato inválido",
        description="Use: hd 1.5, hd 1.5+2.25, hm 1:30, hm 1h20m, hm 90m",
        on_enter=CopyToClipboardAction(help_text),
    )


class DecimalHoursQueryListener(EventListener):
    def on_event(self, event, extension):
        argument = (event.get_argument() or "").strip()
        keyword = (event.get_keyword() or "").strip()

        keyword_decimal = (extension.preferences.get("keyword_decimal") or "hd").strip()
        keyword_minutes = (extension.preferences.get("keyword_minutes") or "hm").strip()

        try:
            if keyword == keyword_decimal:
                decimal_total = safe_eval_expression(argument)
                hhmm = decimal_hours_to_hhmm(decimal_total)
                decimal_text = f"{decimal_total:.2f}"

                return [
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=f"{hhmm} ({decimal_text})",
                        description="ENTER copia decimal",
                        on_enter=CopyToClipboardAction(decimal_text),
                    ),
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=f"Copiar HH:MM: {hhmm}",
                        description="ENTER copia HH:MM",
                        on_enter=CopyToClipboardAction(hhmm),
                    ),
                ]

            if keyword == keyword_minutes:
                total_minutes = parse_hm_input(argument)
                hhmm = format_hhmm_from_minutes(total_minutes)
                decimal_text = f"{(total_minutes / 60):.2f}"

                return [
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=f"{decimal_text} ({hhmm})",
                        description="ENTER copia decimal",
                        on_enter=CopyToClipboardAction(decimal_text),
                    ),
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name=f"Copiar HH:MM: {hhmm}",
                        description="ENTER copia HH:MM",
                        on_enter=CopyToClipboardAction(hhmm),
                    ),
                ]

        except Exception:
            return [build_invalid_format_item()]

        return [build_invalid_format_item()]


class DecimalHoursExtension(Extension):
    def __init__(self):
        super(DecimalHoursExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, DecimalHoursQueryListener())


if __name__ == "__main__":
    DecimalHoursExtension().run()
