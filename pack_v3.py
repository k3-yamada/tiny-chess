#!/usr/bin/env python3
"""Scope-aware minifier & raw-deflate+base85 packer for <4,096-byte main.py."""

import ast
import base64
import builtins
import io
import keyword
import re
import string
import sys
import tokenize
import zlib
from collections import Counter

COMPOUND_RE = re.compile(r"^(def|class|if|elif|else|for|while|try|except|finally|with)\b")


def strip_spaces(code: str) -> str:
    out = []
    indent = 0
    prev = None
    for tok in tokenize.generate_tokens(io.StringIO(code).readline):
        ttype, tstr = tok.type, tok.string
        if ttype in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT, tokenize.NL):
            continue
        if ttype == tokenize.INDENT:
            indent += 1
            continue
        if ttype == tokenize.DEDENT:
            indent -= 1
            continue
        if ttype == tokenize.NEWLINE:
            out.append("\n")
            prev = None
            continue
        if prev is None:
            out.append(" " * indent)
        else:
            pt = prev[0]
            if (
                (pt in (tokenize.NAME, tokenize.NUMBER) and ttype in (tokenize.NAME, tokenize.NUMBER))
                or (pt == tokenize.NAME and ttype == tokenize.STRING)
                or (pt == tokenize.STRING and ttype == tokenize.NAME)
                or (pt == tokenize.NUMBER and tstr == ".")
            ):
                out.append(" ")
        out.append(tstr)
        prev = (ttype, tstr)
    return "".join(out).strip()


def fold_lines(code: str) -> str:
    raw_lines = code.splitlines()
    merged = []
    for line in raw_lines:
        stripped = line.lstrip(" ")
        ind = len(line) - len(stripped)
        is_compound = bool(COMPOUND_RE.match(stripped))
        if merged and not is_compound:
            p_ind, p_str, p_comp = merged[-1]
            if p_ind == ind and not p_comp:
                merged[-1] = (p_ind, p_str + ";" + stripped, False)
                continue
        merged.append((ind, stripped, is_compound))

    out = []
    i = 0
    while i < len(merged):
        ind, st, comp = merged[i]
        if (
            comp
            and not re.match(r"^(def|class)\b", st)
            and i + 1 < len(merged)
            and merged[i + 1][0] == ind + 1
            and not merged[i + 1][2]
            and (i + 2 >= len(merged) or merged[i + 2][0] <= ind)
        ):
            out.append(" " * ind + st + merged[i + 1][1])
            i += 2
        else:
            out.append(" " * ind + st)
            i += 1
    return "\n".join(out)


def pack_source(src: str) -> str:
    tree = ast.parse(src)
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        tree.body.pop(0)

    reserved = set(dir(builtins)) | set(keyword.kwlist) | set(getattr(keyword, "softkwlist", ()))
    keep = reserved | {"os", "json", "urllib", "request", "__name__", "__main__", "choose"}
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg:
            keep.add(node.arg)

    global_names = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name not in keep:
            global_names.add(stmt.name)
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name) and n.id not in keep:
                        global_names.add(n.id)
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for al in stmt.names:
                if al.asname and al.asname not in keep:
                    global_names.add(al.asname)

    g_freq = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in global_names:
            g_freq[node.id] += 1
        elif isinstance(node, ast.FunctionDef) and node.name in global_names:
            g_freq[node.name] += 1
        elif isinstance(node, ast.Global):
            for nm in node.names:
                if nm in global_names:
                    g_freq[nm] += 1
        elif isinstance(node, ast.alias) and node.asname in global_names:
            g_freq[node.asname] += 1

    g_pool = [c for c in string.ascii_uppercase + string.ascii_lowercase if c not in keep]
    abs_alias = g_pool.pop(0)
    g_map = {name: g_pool.pop(0) for name, _ in g_freq.most_common()}
    used_globals = set(g_map.values()) | {abs_alias}

    local_pool_base = [c for c in string.ascii_lowercase + string.ascii_uppercase if c not in keep and c not in used_globals]
    local_pool_base += [a + b for a in string.ascii_lowercase for b in string.digits if a + b not in keep]

    def rename_block(node, scope_map):
        if isinstance(node, ast.FunctionDef):
            if node.name in scope_map:
                node.name = scope_map[node.name]
            declared_globals = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Global):
                    declared_globals.update(sub.names)
            loc_vars = set()
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                if arg.arg not in keep:
                    loc_vars.add(arg.arg)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    if sub.id not in keep and sub.id not in declared_globals and sub.id not in global_names:
                        loc_vars.add(sub.id)
                elif isinstance(sub, ast.Lambda):
                    for a in sub.args.args:
                        if a.arg not in keep:
                            loc_vars.add(a.arg)
            loc_freq = Counter()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id in loc_vars:
                    loc_freq[sub.id] += 1
                elif isinstance(sub, ast.arg) and sub.arg in loc_vars:
                    loc_freq[sub.arg] += 1
            pool = list(local_pool_base)
            new_map = dict(scope_map)
            for nm, _ in loc_freq.most_common():
                new_map[nm] = pool.pop(0)
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                if arg.arg in new_map:
                    arg.arg = new_map[arg.arg]
            for child in node.body:
                rename_block(child, new_map)
            for d in node.args.defaults:
                rename_block(d, scope_map)
            return
        if isinstance(node, ast.Lambda):
            for a in node.args.args:
                if a.arg in scope_map:
                    a.arg = scope_map[a.arg]
            rename_block(node.body, scope_map)
            return
        if isinstance(node, ast.Name):
            if node.id in scope_map:
                node.id = scope_map[node.id]
            return
        if isinstance(node, ast.Global):
            node.names = [scope_map.get(nm, nm) for nm in node.names]
            return
        if isinstance(node, ast.alias):
            if node.asname in scope_map:
                node.asname = scope_map[node.asname]
            return
        for child in ast.iter_child_nodes(node):
            rename_block(child, scope_map)

    for stmt in tree.body:
        rename_block(stmt, g_map)

    class AbsAlias(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == "abs" and isinstance(node.ctx, ast.Load):
                node.id = abs_alias
            return node

    tree = AbsAlias().visit(tree)
    tree.body.insert(1, ast.parse(f"{abs_alias}=abs").body[0])
    ast.fix_missing_locations(tree)

    minified = fold_lines(strip_spaces(ast.unparse(tree)))
    ast.parse(minified)

    co = zlib.compressobj(level=9, wbits=-15, memLevel=9)
    raw = co.compress(minified.encode("utf-8")) + co.flush()
    b85 = base64.b85encode(raw).decode("ascii")
    assert "'" not in b85 and "\\" not in b85
    return f"import zlib,base64\nexec(zlib.decompress(base64.b85decode('{b85}'),-15))\n"


if __name__ == "__main__":
    src_path = sys.argv[1] if len(sys.argv) > 1 else "engine_v3.py"
    dst_path = sys.argv[2] if len(sys.argv) > 2 else "main_v3.py"
    with open(src_path, "r", encoding="utf-8") as f:
        packed = pack_source(f.read())
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(packed)
    size = len(packed.encode("utf-8"))
    print(f"Packed {src_path} -> {dst_path}: {size} bytes ({4096 - size} bytes under 4,096 limit)")
