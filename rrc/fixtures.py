"""Authored benign finite probes. None is an imported/public Java benchmark."""
from __future__ import annotations
from typing import Any
from .schema import validate

class Builder:
    def __init__(self, external: int = 0, choices: int = 0):
        self.p: dict[str, Any] = {"external": [f"h{i}" for i in range(external)],
            "choices": [f"r{i}" for i in range(choices)], "nodes": [],
            "feasible": 0, "table": [], "sites": []}
        self.inputs = [self.node("input", index=i) for i in range(external + choices)]
        self.true = self.lit(True)
        self.p["feasible"] = self.true
        self.loader = self.lit("L")
        self.a, self.b, self.m, self.sig = self.lit("A"), self.lit("B"), self.lit("f"), self.lit("()")
    def node(self, op: str, *args: int, **fields: Any) -> int:
        j = len(self.p["nodes"])
        self.p["nodes"].append({"op": op, **fields} if fields else {"op": op, "args": list(args)})
        return j
    def lit(self, value: str | bool) -> int:
        return self.node("lit", value=value)
    def probe(self, class_ref: int | None = None, method: int | None = None,
              loader: int | None = None, signature: int | None = None, guard: int | None = None) -> None:
        self.p["sites"].append({"guard": self.true if guard is None else guard,
            "loader": self.loader if loader is None else loader,
            "class": self.a if class_ref is None else class_ref,
            "method": self.m if method is None else method,
            "signature": self.sig if signature is None else signature})
    def table(self, entries: list[list[str]] | None = None) -> None:
        self.p["table"] = entries if entries is not None else [["L", "A", "f", "()"], ["L", "B", "f", "()"]]
    def finish(self) -> dict[str, Any]:
        return validate(self.p)


def all_fixtures() -> list[tuple[str, str, dict[str, Any]]]:
    out = []
    def add(label: str, b: Builder):
        out.append((f"F{len(out)+1:02d}", label, b.finish()))
    b = Builder(); b.probe(); b.table(); add("constant lookup", b)
    b = Builder(); b.probe(method=b.node("cat", b.lit("rea"), b.lit("d"))); b.table([["L","A","read","()"]]); add("concatenated method", b)
    b = Builder(1); c = b.node("ite", b.inputs[0], b.a, b.b); b.probe(b.node("alias", c)); b.table(); add("branch through alias", b)
    b = Builder(1); h=b.inputs[0]; c=b.node("ite",h,b.a,b.b); m=b.node("ite",h,b.m,b.lit("g")); b.probe(c,method=m)
    b.table([["L",c,m,"()"] for c in ["A","B"] for m in ["f","g"]]); add("joint class-method correlation", b)
    b = Builder(1); q=b.node("eq",b.inputs[0],b.lit(False)); b.probe(b.node("ite",q,b.a,b.b)); b.table(); add("typed equality", b)
    b = Builder(2); b.p["feasible"]=b.node("eq",*b.inputs); b.probe(b.node("ite",b.inputs[0],b.b,b.a)); b.table(); add("incomparable sufficient observations", b)
    b = Builder(3); x,y,z=b.inputs; yz=b.node("and",y,z); none=b.node("and",b.node("not",y),b.node("not",z)); b.p["feasible"]=b.node("or",none,b.node("and",x,yz)); b.probe(b.node("ite",x,b.b,b.a)); b.table(); add("one-deletion minimality trap", b)
    b = Builder(1,1); q=b.node("eq",*b.inputs); b.probe(b.node("ite",q,b.b,b.a)); b.table(); add("choice permutation preserves target sets", b)
    b = Builder(0,1); b.probe(b.node("ite",b.inputs[0],b.a,b.b)); b.table(); add("internal nondeterminism only", b)
    b = Builder(1); l=b.node("ite",b.inputs[0],b.loader,b.lit("M")); b.probe(loader=l); b.table([["L","A","f","()"],["M","A","f","()"]]); add("loader identity", b)
    b = Builder(1); s=b.node("ite",b.inputs[0],b.sig,b.lit("(I)")); b.probe(signature=s); b.table([["L","A","f","()"],["L","A","f","(I)"]]); add("signature identity", b)
    b = Builder(1); b.probe(b.node("ite",b.inputs[0],b.a,b.b)); b.table([["L","A","f","()"]]); add("lookup error is not a target", b)
    b = Builder(1); b.probe(guard=b.inputs[0]); b.table(); add("guarded skipped site", b)
    b = Builder(1); b.p["feasible"]=b.inputs[0]; b.probe(b.node("ite",b.inputs[0],b.a,b.b)); b.table(); add("infeasible world excluded", b)
    b = Builder(); b.p["feasible"]=b.lit(False); b.probe(); b.table(); add("empty feasible world family", b)
    b = Builder(1); b.probe(b.node("ite",b.inputs[0],b.a,b.a)); b.table(); add("syntactic but not semantic dependency", b)
    b = Builder(); s=b.node("cat",b.lit("a"*24),b.lit("b"*24)); b.probe(s); b.table([["L","a"*24+"b"*24,"f","()"]]); add("48-byte boundary", b)
    b = Builder(); s=b.node("cat",b.lit("ab"),b.lit("c")); b.probe(s); b.table([["L","abc","f","()"]]); add("noncommutative concatenation", b)
    b = Builder(1); b.probe(b.node("ite",b.inputs[0],b.a,b.b)); b.probe(b.node("ite",b.inputs[0],b.b,b.a)); b.table(); add("two site-indexed outcomes", b)
    b = Builder(1); s=b.node("ite",b.inputs[0],b.a,b.b); b.probe(b.node("cat",s,s)); b.table([["L",c,"f","()"] for c in ["AA","AB","BA","BB"]]); add("repeated variable correlation", b)
    b = Builder(1); m=b.node("alias",b.node("ite",b.inputs[0],b.m,b.lit("g"))); b.probe(method=m); b.table([["L","A",m,"()"] for m in ["f","g"]]); add("method alias", b)
    b = Builder(1); h=b.inputs[0]; c=b.node("ite",h,b.a,b.b); b.probe(c,guard=h); b.table(); add("guard-name correlation", b)
    b = Builder(1,1); h,r=b.inputs; c=b.node("ite",b.node("or",h,r),b.a,b.b); b.probe(c); b.table(); add("robust versus conditional target", b)
    b = Builder(8,4); q=b.inputs[0]
    for h in b.inputs[1:]: q=b.node("not",b.node("eq",q,h))
    c=b.node("ite",q,b.a,b.b)
    while len(b.p["nodes"]) < 64: c=b.node("alias",c)
    for _ in range(8): b.probe(c)
    b.table([["L","A","f","()"],["L","B","f","()"]]+[["L",f"C{i}","f","()"] for i in range(254)])
    add("bounded largest pilot probe", b)
    return out
