"""Compare two Android lint XML reports and list the issues the first adds.

Usage: compare_lint.py HEAD_XML HEAD_ROOT [BASE_XML BASE_ROOT]

HEAD_ROOT and BASE_ROOT are the checkout folders, so file paths can be compared
between the two. An issue is matched by its check, file and message, not its line,
so code that only moves does not count as new.

Writes a Markdown summary to standard output. Exits 1 if the head report has issues
the base report does not, 0 otherwise (and always 0 when no base report is given).
"""
import collections
import os
import sys
import xml.etree.ElementTree as ET


def read(path, root):
    issues = []
    root = os.path.abspath(root)
    for issue in ET.parse(path).getroot().iter("issue"):
        loc = issue.find("location")
        f = loc.get("file", "") if loc is not None else ""
        line = loc.get("line", "") if loc is not None else ""
        if os.path.isabs(f):
            f = os.path.relpath(f, root)
        issues.append({
            "severity": issue.get("severity", ""),
            "id": issue.get("id", ""),
            "file": f.replace("\\", "/"),
            "line": line,
            "message": issue.get("message", ""),
        })
    return issues


def key(i):
    return (i["id"], i["file"], i["message"])


def main(argv):
    head = read(argv[0], argv[1])
    base = read(argv[2], argv[3]) if len(argv) >= 4 else None

    by_severity = collections.Counter(i["severity"] for i in head)
    print("## Android lint")
    print()
    counts = ", ".join("%s %d" % kv for kv in sorted(by_severity.items())) or "none"
    if base is None:
        print("%d issues (%s)." % (len(head), counts))
        return 0
    print("%d issues (%s); the base branch has %d." % (len(head), counts, len(base)))
    print()
    remaining = collections.Counter(key(i) for i in base)
    new = []
    for i in head:
        k = key(i)
        if remaining[k] > 0:
            remaining[k] -= 1
        else:
            new.append(i)
    gone = collections.Counter(k[0] for k, n in remaining.items() for _ in range(n))

    if gone:
        print("Cleared by this change: " + ", ".join("%s %d" % kv for kv in sorted(gone.items())))
        print()
    if not new:
        print("No new lint issues compared with the base branch.")
        return 0

    print("**%d new lint issue%s compared with the base branch:**" % (len(new), "" if len(new) == 1 else "s"))
    print()
    print("| Check | Severity | Where | Message |")
    print("|-------|----------|-------|---------|")
    for i in sorted(new, key=lambda i: (i["file"], int(i["line"] or 0))):
        where = "%s:%s" % (i["file"], i["line"]) if i["line"] else i["file"]
        print("| %s | %s | `%s` | %s |" % (i["id"], i["severity"], where,
                                          i["message"].replace("|", "\\|").replace("\n", " ")))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
