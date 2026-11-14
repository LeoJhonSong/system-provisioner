#!/usr/bin/env python3
"""把pyinfra `--json`的deploy结果重新排成带边框的表格, 每个操作一行 (主机数/成功/失败/
无变化计数), 末尾加总计行——跟pyinfra自带的Results表格同构, 但修了它的列宽bug:
`pyinfra_cli/prints.py`按字符数 (而非终端显示宽度) 算列宽, 操作名一旦含中文就会错位.
这里用`unicodedata.east_asian_width`按实际显示宽度对齐.

纯标准库实现, 跟具体项目/inventory无关, 可原样复制到其他用pyinfra的仓库.

Usage::

    pyinfra @local deploy.py -y --json | tail -1 | python3 tools/pyinfra_table.py
"""

import json
import sys
import unicodedata


def display_width(text):
    """中日韩宽字符按2格算, 其余按1格, 对应终端里的实际占位."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text, width):
    return text + " " * (width - display_width(text))


def render_table(headers, rows):
    widths = [display_width(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], display_width(cell))

    def border():
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def format_row(cells):
        return "| " + " | ".join(pad(cell, width) for cell, width in zip(cells, widths, strict=True)) + " |"

    lines = [border(), format_row(headers), border()]
    lines.extend(format_row(row) for row in rows)
    lines.append(border())
    return "\n".join(lines)


def summarize(operations):
    """每个操作一行: 主机数固定显示数字, 成功/失败/无变化为0时显示'-' (对齐pyinfra原习惯)."""
    rows = []
    totals = [0, 0, 0, 0]
    for op in operations:
        counts = [len(op["success"]), len(op["error"]), len(op["no_change"])]
        hosts = sum(counts)
        totals = [total + count for total, count in zip(totals, [hosts, *counts], strict=True)]
        rows.append([op["name"], str(hosts), *(str(count) if count else "-" for count in counts)])
    rows.append(["总计", str(totals[0]), *(str(total) if total else "-" for total in totals[1:])])
    return rows


def main():
    data = json.load(sys.stdin)
    rows = summarize(data["results"]["operations"])
    print(render_table(["操作", "主机数", "成功", "失败", "无变化"], rows))


if __name__ == "__main__":
    main()
